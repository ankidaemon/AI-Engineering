"""
Redis-backed FAISS tests. FAISS does the vectors; Redis supplies persistence,
metadata, and concurrency. Both dependencies are injected with offline fakes —
deterministic fake embeddings and an in-memory `fakeredis` client — so these run
with no model server and no Redis server. Requires `faiss-cpu` and `fakeredis`.

The four tests map to the four claims the module makes:
  - add + search works at all;
  - metadata filtering is computed by Redis (inverted-index intersection);
  - the index lives in Redis, so a brand-new instance loads it (the container /
    ephemeral-filesystem story);
  - concurrent writers don't lose each other's documents (Failure 2, cluster-wide).
"""
import hashlib
import threading

import fakeredis
import pytest
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

from src.vectorstores.redis_backed_faiss import RedisBackedFAISSStore


class FakeEmbeddings(Embeddings):
    """Deterministic embeddings derived from text bytes — no model server."""
    def __init__(self, dim: int = 16):
        self.dim = dim

    def _vec(self, text: str):
        digest = hashlib.md5(text.encode("utf-8")).digest()
        return [b / 255.0 for b in digest[: self.dim]]

    def embed_documents(self, texts):
        return [self._vec(t) for t in texts]

    def embed_query(self, text):
        return self._vec(text)


@pytest.fixture
def client():
    # One shared in-memory Redis the whole test can point multiple stores at.
    return fakeredis.FakeStrictRedis()


@pytest.fixture
def store(client):
    return RedisBackedFAISSStore(embeddings=FakeEmbeddings(), redis_client=client)


def test_add_and_search(store):
    assert store.add_documents([
        Document(page_content="Termination requires 30 days notice.",
                 metadata={"doc_type": "legal"}),
        Document(page_content="System must support 10,000 concurrent users.",
                 metadata={"doc_type": "technical"}),
    ]) == 2
    assert store.get_vector_count() == 2
    assert len(store.similarity_search("termination", k=1)) == 1


def test_metadata_filter_uses_redis(store):
    store.add_documents([
        Document(page_content="legal clause about liability", metadata={"doc_type": "legal"}),
        Document(page_content="api rate limits and SLAs", metadata={"doc_type": "technical"}),
    ])
    legal = store.similarity_search("clause", k=5, filter_dict={"doc_type": "legal"})
    assert legal and all(d.metadata.get("doc_type") == "legal" for d in legal)


def test_index_persists_in_redis_across_instances(client):
    # Write with one instance...
    writer = RedisBackedFAISSStore(embeddings=FakeEmbeddings(), redis_client=client)
    writer.add_documents([Document(page_content="alpha", metadata={"doc_type": "legal"})])

    # ...then a brand-new instance (think: a freshly scheduled pod with an empty
    # filesystem) loads the index straight from Redis — nothing on local disk.
    fresh_pod = RedisBackedFAISSStore(embeddings=FakeEmbeddings(), redis_client=client)
    assert fresh_pod.get_vector_count() == 1
    assert any("alpha" in d.page_content for d in fresh_pod.similarity_search("alpha", k=1))


def test_concurrent_writes_do_not_lose_documents(store):
    # Several writers add at once. Without the distributed lock + reload-before-add,
    # the last persist would clobber the others (Failure 2). With it, every
    # document survives.
    def writer(i):
        store.add_documents([Document(page_content=f"doc-{i}", metadata={"doc_type": "legal"})])

    threads = [threading.Thread(target=writer, args=(i,)) for i in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    store.refresh()
    assert store.get_vector_count() == 8
