"""
Pinecone wrapper — managed cloud vector search at scale (Section 4.2).

Pinecone is optional: its packages (langchain-pinecone, pinecone-client) are
imported lazily inside __init__, so this module imports fine without them. The
one Pinecone-specific concept worth knowing is the *namespace* — a partition
inside an index used to keep tenants or projects isolated while sharing one index.
"""
import logging
from typing import Optional

from langchain_core.documents import Document

from src.config import settings
from src.models import get_embeddings

logger = logging.getLogger(__name__)


class ProductionPineconeStore:
    def __init__(
        self,
        api_key: str | None = None,
        index_name: str | None = None,
        dimension: int = 768,
    ):
        try:
            from pinecone import Pinecone, ServerlessSpec
        except ImportError as exc:
            raise RuntimeError(
                "Pinecone support requires: pip install langchain-pinecone pinecone-client"
            ) from exc

        self._ServerlessSpec = ServerlessSpec
        self._pc = Pinecone(api_key=api_key or settings.pinecone_api_key)
        self._index_name = index_name or settings.pinecone_index
        self._dimension = dimension
        self._embeddings = get_embeddings()
        self._index = self._get_or_create_index()

    def _get_or_create_index(self):
        existing = [i.name for i in self._pc.list_indexes()]
        if self._index_name not in existing:
            self._pc.create_index(
                name=self._index_name,
                dimension=self._dimension,
                metric="cosine",
                spec=self._ServerlessSpec(cloud="aws", region="us-east-1"),
            )
        return self._pc.Index(self._index_name)

    def get_store(self, namespace: str = "default"):
        from langchain_pinecone import PineconeVectorStore
        return PineconeVectorStore(
            index=self._index, embedding=self._embeddings, namespace=namespace
        )

    def add_documents_batch(
        self, documents: list[Document], namespace: str = "default", batch_size: int = 100
    ) -> int:
        store = self.get_store(namespace)
        total = 0
        for i in range(0, len(documents), batch_size):
            batch = documents[i : i + batch_size]
            store.add_documents(batch)
            total += len(batch)
            logger.info("Pinecone: upserted %d/%d to '%s'", total, len(documents), namespace)
        return total

    def as_retriever(self, namespace: str = "default", k: int = 5,
                     filter_dict: Optional[dict] = None):
        store = self.get_store(namespace)
        kwargs = {"k": k}
        if filter_dict:
            kwargs["filter"] = filter_dict
        return store.as_retriever(search_kwargs=kwargs)

    def delete_namespace(self, namespace: str) -> None:
        """Remove all vectors in a namespace — e.g. when a tenant leaves."""
        self._index.delete(delete_all=True, namespace=namespace)
        logger.info("Pinecone: deleted namespace '%s'", namespace)
