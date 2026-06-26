"""
FAISS wrapper — local, high-performance vector search (Section 4.1).

FAISS is a *library*, not a database: persistence, metadata, and concurrency are
your responsibility. This wrapper supplies the database-like conveniences —
loading a saved index on startup, adding documents incrementally, saving after
each change, and an over-fetch-then-filter search.

The embeddings object is injectable so the store can be tested offline with a
deterministic fake (see tests/test_faiss.py); by default it uses Ollama.
"""
import logging
import shutil
from pathlib import Path
from typing import Callable, Optional

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

from src.config import settings
from src.models import get_embeddings

logger = logging.getLogger(__name__)


class FAISSVectorStore:
    def __init__(
        self,
        persist_dir: str | None = None,
        embeddings=None,
    ):
        self._persist_dir = Path(persist_dir or settings.faiss_persist_dir)
        self._persist_dir.mkdir(parents=True, exist_ok=True)
        self._index_path = self._persist_dir / "index"
        self._embeddings = embeddings or get_embeddings()
        self._store: Optional[FAISS] = None
        self._load_or_init()

    def _load_or_init(self) -> None:
        if self._index_path.exists():
            try:
                self._store = FAISS.load_local(
                    str(self._index_path),
                    self._embeddings,
                    allow_dangerous_deserialization=True,
                )
                logger.info("FAISS: loaded %d vectors from %s",
                            self._store.index.ntotal, self._index_path)
            except Exception as exc:
                logger.warning("Could not load FAISS index (%s); starting fresh.", exc)
                self._store = None

    def add_documents(self, documents: list[Document]) -> int:
        """Add documents to the index. Builds on first call, extends afterwards."""
        if not documents:
            return 0
        if self._store is None:
            self._store = FAISS.from_documents(documents, self._embeddings)
        else:
            self._store.add_documents(documents)
        self._save()
        return len(documents)

    def similarity_search(
        self,
        query: str,
        k: int = 5,
        filter_fn: Optional[Callable[[Document], bool]] = None,
    ) -> list[Document]:
        """Search the index. When filtering, over-fetch so we still return k."""
        if self._store is None:
            return []
        fetch_k = k * 4 if filter_fn else k
        docs = self._store.similarity_search(query, k=fetch_k)
        if filter_fn:
            docs = [d for d in docs if filter_fn(d)]
        return docs[:k]

    def similarity_search_with_score(self, query: str, k: int = 5):
        """Return (document, similarity) pairs. FAISS gives L2 distance; we
        convert to a 0..1 similarity so higher means more similar."""
        if self._store is None:
            return []
        results = self._store.similarity_search_with_score(query, k=k)
        return [(doc, 1.0 / (1.0 + dist)) for doc, dist in results]

    def as_retriever(self, k: int = 5):
        if self._store is None:
            raise RuntimeError("FAISS index is empty. Add documents first.")
        return self._store.as_retriever(search_kwargs={"k": k})

    def get_vector_count(self) -> int:
        return self._store.index.ntotal if self._store else 0

    def _save(self) -> None:
        if self._store:
            self._store.save_local(str(self._index_path))

    def reset(self) -> None:
        """Wipe the index. Destructive — use with care in production."""
        self._store = None
        if self._index_path.exists():
            shutil.rmtree(self._index_path)
        logger.warning("FAISS index reset — all vectors deleted")
