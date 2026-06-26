"""
ChromaDB wrapper — a local, persistent vector database (Section 4.2).

Where FAISS is a bare library (you supply persistence, metadata, and concurrency
yourself), Chroma is a *database*: it persists to disk on its own, filters on
metadata, and isolates document sets into **collections** — all in-process, with
no separate service to run and no cloud account.

Collections are Chroma's multi-tenancy primitive: write to a collection, search
within it, and drop the whole collection when a tenant or document set expires.

The maintained `langchain_chroma` package is imported lazily inside `get_store`,
so importing this module never requires `chromadb` to be installed; the embeddings
object is injectable so the store can be tested offline with a deterministic fake.
"""
import logging
from typing import Optional

from langchain_core.documents import Document

from src.config import settings
from src.models import get_embeddings

logger = logging.getLogger(__name__)


class ChromaDocumentStore:
    def __init__(
        self,
        persist_dir: str | None = None,
        collection: str | None = None,
        embeddings=None,
    ):
        self._persist_dir = persist_dir or settings.chroma_persist_dir
        self._default_collection = collection or settings.chroma_collection
        self._embeddings = embeddings or get_embeddings()

    def get_store(self, collection: str | None = None):
        """Return a LangChain Chroma store bound to a (persisted) collection."""
        from langchain_chroma import Chroma
        return Chroma(
            collection_name=collection or self._default_collection,
            embedding_function=self._embeddings,
            persist_directory=self._persist_dir,
        )

    def add_documents(self, documents: list[Document], collection: str | None = None) -> int:
        if not documents:
            return 0
        self.get_store(collection).add_documents(documents)
        return len(documents)

    def add_documents_batch(
        self, documents: list[Document], collection: str | None = None, batch_size: int = 100
    ) -> int:
        store = self.get_store(collection)
        name = collection or self._default_collection
        total = 0
        for i in range(0, len(documents), batch_size):
            batch = documents[i : i + batch_size]
            store.add_documents(batch)
            total += len(batch)
            logger.info("Chroma: added %d/%d to collection '%s'", total, len(documents), name)
        return total

    def similarity_search(
        self, query: str, collection: str | None = None, k: int = 5,
        filter_dict: Optional[dict] = None,
    ) -> list[Document]:
        return self.get_store(collection).similarity_search(query, k=k, filter=filter_dict)

    def as_retriever(
        self, collection: str | None = None, k: int = 5, filter_dict: Optional[dict] = None
    ):
        kwargs = {"k": k}
        if filter_dict:
            kwargs["filter"] = filter_dict
        return self.get_store(collection).as_retriever(search_kwargs=kwargs)

    def delete_collection(self, collection: str | None = None) -> None:
        """Remove an entire collection — e.g. when a tenant leaves or a set expires."""
        self.get_store(collection).delete_collection()
        logger.info("Chroma: deleted collection '%s'", collection or self._default_collection)
