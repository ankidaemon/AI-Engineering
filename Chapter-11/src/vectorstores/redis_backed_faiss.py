"""
Redis-backed FAISS — FAISS for vectors, Redis for the three things FAISS leaves
to you: persistence, metadata, and concurrency (Section 4.3).

The plain FAISS wrapper (`faiss_store.py`) persists the index to the **local
filesystem** and serializes writes with an **in-process** `threading.Lock`. Both
assumptions break the moment you run in containers:

* A pod's filesystem is ephemeral — when the pod restarts or reschedules, the
  on-disk index is gone. A volume helps on one node, but several pods cannot share
  one writable index file safely.
* An in-process lock only coordinates threads inside *one* process. Two pods (or
  two `uvicorn` workers) writing at once is exactly the race from Failure 2, and a
  local lock does nothing to stop it.

Redis fixes all three with one networked dependency that scales from a single
local container to managed/enterprise Redis behind many pods:

* **Persistence** — the serialized FAISS index lives in a Redis key, so any pod
  can load the latest index on startup regardless of which pod wrote it.
* **Metadata** — document metadata is stored in Redis as an inverted index
  (a set of document ids per ``field=value``), so filtering is a set intersection
  computed by Redis rather than a scan of over-fetched candidates.
* **Concurrency** — writes are serialized with a **distributed** Redis lock that
  coordinates across processes *and* hosts, not just threads.

The correctness pattern for writes is *lock → reload → add → persist*: inside the
lock we pull the freshest index from Redis before extending it, so two writers on
different pods never clobber each other's documents (the lost-update bug from
Failure 2, now solved across the whole cluster, not just one process).

Both the embeddings object and the Redis client are injectable, so the store runs
offline in tests with deterministic fake embeddings and an in-memory `fakeredis`
client — no model server and no Redis server required.
"""
import logging
import uuid
from typing import Any, Optional

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

from src.config import settings
from src.models import get_embeddings

logger = logging.getLogger(__name__)

# The stable id we stamp onto every document's metadata. FAISS returns Documents,
# not ids, from a search, so this is how a search hit is matched back to the
# metadata Redis indexed for it.
_RID = "_rid"


class RedisBackedFAISSStore:
    def __init__(
        self,
        embeddings=None,
        redis_client: Any = None,
        redis_url: str | None = None,
        index_key: str | None = None,
        metadata_prefix: str | None = None,
        lock_key: str | None = None,
        lock_timeout: int | None = None,
    ):
        self._embeddings = embeddings or get_embeddings()
        self._index_key = index_key or settings.redis_index_key
        self._meta_prefix = metadata_prefix or settings.redis_metadata_prefix
        self._lock_key = lock_key or settings.redis_lock_key
        self._lock_timeout = lock_timeout or settings.redis_lock_timeout
        self._client = redis_client or self._connect(redis_url or settings.redis_url)
        self._store: Optional[FAISS] = None
        self._reload()

    # ── connection / persistence ──────────────────────────────────────
    def _connect(self, url: str):
        """Lazily import redis so importing this module never needs the package."""
        import redis
        return redis.Redis.from_url(url)

    def _reload(self) -> None:
        """Load the freshest serialized index from Redis (no-op if none yet)."""
        blob = self._client.get(self._index_key)
        if not blob:
            self._store = None
            return
        try:
            self._store = FAISS.deserialize_from_bytes(
                embeddings=self._embeddings,
                serialized=blob,
                allow_dangerous_deserialization=True,
            )
            logger.info("Redis/FAISS: loaded %d vectors from key '%s'",
                        self._store.index.ntotal, self._index_key)
        except Exception as exc:                       # corrupt/incompatible blob
            logger.warning("Could not load index from Redis (%s); starting fresh.", exc)
            self._store = None

    def _persist(self) -> None:
        if self._store is not None:
            self._client.set(self._index_key, self._store.serialize_to_bytes())

    def refresh(self) -> None:
        """Pull the latest index written by *any* pod. Reads serve an in-memory
        snapshot; call this when a reader must see another writer's newest data."""
        self._reload()

    # ── concurrency ───────────────────────────────────────────────────
    def _lock(self):
        """A distributed lock: coordinates writers across processes and hosts,
        unlike the in-process threading.Lock of ThreadSafeFAISSStore."""
        return self._client.lock(
            self._lock_key, timeout=self._lock_timeout, blocking_timeout=self._lock_timeout
        )

    # ── writes ────────────────────────────────────────────────────────
    def add_documents(self, documents: list[Document]) -> int:
        """Add documents safely. The lock → reload → add → persist sequence makes
        concurrent writes from different pods lose-update-free (Failure 2)."""
        if not documents:
            return 0
        for doc in documents:                          # stamp a stable id on each
            doc.metadata.setdefault(_RID, uuid.uuid4().hex)
        with self._lock():
            self._reload()                             # start from the freshest index
            if self._store is None:
                self._store = FAISS.from_documents(documents, self._embeddings)
            else:
                self._store.add_documents(documents)
            self._index_metadata(documents)
            self._persist()
        return len(documents)

    def _index_metadata(self, documents: list[Document]) -> None:
        """Write each document's metadata as an inverted index in Redis so that
        filtering becomes a set intersection (see _allowed_rids)."""
        pipe = self._client.pipeline()
        for doc in documents:
            rid = doc.metadata[_RID]
            for key, value in doc.metadata.items():
                if key == _RID or not isinstance(value, (str, int, float, bool)):
                    continue
                pipe.sadd(f"{self._meta_prefix}:idx:{key}={value}", rid)
        pipe.execute()

    # ── reads ─────────────────────────────────────────────────────────
    def _allowed_rids(self, filter_dict: dict) -> set:
        """Intersect the inverted-index sets — Redis computes which documents match
        every field=value in the filter."""
        keys = [f"{self._meta_prefix}:idx:{k}={v}" for k, v in filter_dict.items()]
        members = self._client.sinter(keys) if keys else set()
        return {m.decode() if isinstance(m, bytes) else m for m in members}

    def similarity_search(
        self, query: str, k: int = 5, filter_dict: Optional[dict] = None
    ) -> list[Document]:
        if self._store is None:
            return []
        if not filter_dict:
            return self._store.similarity_search(query, k=k)
        allowed = self._allowed_rids(filter_dict)      # Redis decides the candidates
        docs = self._store.similarity_search(query, k=k * 4)   # over-fetch, then keep
        docs = [d for d in docs if d.metadata.get(_RID) in allowed]
        return docs[:k]

    def as_retriever(self, k: int = 5):
        if self._store is None:
            raise RuntimeError("Index is empty. Add documents first.")
        return self._store.as_retriever(search_kwargs={"k": k})

    def get_vector_count(self) -> int:
        return self._store.index.ntotal if self._store else 0

    def reset(self) -> None:
        """Wipe the index and all metadata from Redis. Destructive."""
        with self._lock():
            self._store = None
            self._client.delete(self._index_key)
            for key in self._client.scan_iter(f"{self._meta_prefix}:idx:*"):
                self._client.delete(key)
        logger.warning("Redis/FAISS: index and metadata cleared")
