"""
The FAISS-backed knowledge index (§4.3, §4.5).

FAISS is a similarity search library, not a database, so this wrapper adds
what the knowledge base needs on top: embedding chunks on the way in, saving
the index to disk, converting raw distances into a 0..1 relevance the agent
can threshold on, and — the piece freshness depends on — `replace(doc_id, ...)`,
which swaps a changed document's old chunks for new ones without rebuilding
the whole index (Failure 1 in the chapter).

Embeddings are injected so tests run offline with a deterministic fake.
"""
import json
import logging
import os
import uuid
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class RetrievedPassage:
    """One search hit: the text, its metadata, and a 0..1 relevance score."""
    text: str
    metadata: dict = field(default_factory=dict)
    relevance: float = 0.0

    @property
    def source(self) -> str:
        return self.metadata.get("source", "unknown")


class KnowledgeIndex:
    def __init__(self, persist_dir: str = "./data/faiss", embeddings=None):
        self._persist_dir = persist_dir
        if embeddings is None:
            from langchain_ollama import OllamaEmbeddings
            from src.config import settings
            embeddings = OllamaEmbeddings(model=settings.embedding_model)
        self._embeddings = embeddings
        self._store = None
        # doc_id -> list of chunk ids currently in the index. This is what
        # makes replace() possible: we know exactly which chunks belong to
        # which document, so a changed document swaps only its own chunks.
        self._chunk_ids: dict = {}
        self._load_if_persisted()

    # ── Writing ──────────────────────────────────────────────────────

    def replace(self, doc_id: str, chunks: list) -> int:
        """Swap a document's old chunks for new ones. Safe on first insert."""
        old_ids = self._chunk_ids.pop(doc_id, [])
        if old_ids and self._store is not None:
            self._store.delete(old_ids)
        if not chunks:
            self._persist()
            return 0
        new_ids = [f"{doc_id}:{uuid.uuid4().hex}" for _ in chunks]
        from langchain_community.vectorstores import FAISS
        if self._store is None:
            self._store = FAISS.from_documents(chunks, self._embeddings, ids=new_ids)
        else:
            self._store.add_documents(chunks, ids=new_ids)
        self._chunk_ids[doc_id] = new_ids
        self._persist()
        return len(chunks)

    # ── Reading ──────────────────────────────────────────────────────

    def search(self, query: str, k: int = 6, filter_dict: dict = None) -> list:
        """Returns RetrievedPassage objects, best first, relevance in 0..1."""
        if self._store is None:
            return []
        hits = self._store.similarity_search_with_score(query, k=k, filter=filter_dict)
        results = []
        for doc, distance in hits:
            # FAISS returns an L2 distance where smaller is better; convert
            # to a 0..1 relevance where bigger is better, so the knowledge
            # agent can apply one threshold (MIN_RELEVANCE) regardless of
            # embedding scale.
            relevance = 1.0 / (1.0 + float(distance))
            results.append(RetrievedPassage(doc.page_content, doc.metadata, relevance))
        return results

    @property
    def document_count(self) -> int:
        return len(self._chunk_ids)

    # ── Persistence ──────────────────────────────────────────────────

    def _persist(self):
        if self._store is None:
            return
        os.makedirs(self._persist_dir, exist_ok=True)
        self._store.save_local(self._persist_dir)
        with open(os.path.join(self._persist_dir, "chunk_ids.json"), "w") as f:
            json.dump(self._chunk_ids, f)

    def _load_if_persisted(self):
        index_file = os.path.join(self._persist_dir, "index.faiss")
        ids_file = os.path.join(self._persist_dir, "chunk_ids.json")
        if not os.path.exists(index_file):
            return
        from langchain_community.vectorstores import FAISS
        self._store = FAISS.load_local(
            self._persist_dir, self._embeddings,
            allow_dangerous_deserialization=True,
        )
        if os.path.exists(ids_file):
            with open(ids_file) as f:
                self._chunk_ids = json.load(f)
