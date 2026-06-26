"""
FAISS wrapper tests. The store accepts an injectable embeddings object, so we use
a deterministic fake here — no Ollama, no network. Requires `faiss-cpu`.
"""
import hashlib

import pytest
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

from src.vectorstores.faiss_store import FAISSVectorStore


class FakeEmbeddings(Embeddings):
    """Deterministic embeddings: a fixed-length vector derived from text bytes.

    Subclasses Embeddings so FAISS treats it as an embeddings object (not a bare
    callable). No model server or network required.
    """
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
def store(tmp_path):
    return FAISSVectorStore(persist_dir=str(tmp_path / "faiss"),
                            embeddings=FakeEmbeddings())


def test_add_and_count(store):
    docs = [
        Document(page_content="Termination requires 30 days notice.",
                 metadata={"doc_type": "legal", "page": 1}),
        Document(page_content="Payment terms are net 30 from invoice date.",
                 metadata={"doc_type": "legal", "page": 2}),
        Document(page_content="System must support 10,000 concurrent users.",
                 metadata={"doc_type": "technical", "page": 1}),
    ]
    assert store.add_documents(docs) == 3
    assert store.get_vector_count() == 3


def test_search_returns_results(store):
    store.add_documents([
        Document(page_content="alpha", metadata={"doc_type": "legal"}),
        Document(page_content="beta", metadata={"doc_type": "technical"}),
    ])
    results = store.similarity_search("alpha", k=1)
    assert len(results) == 1


def test_metadata_filter(store):
    store.add_documents([
        Document(page_content="legal clause about liability", metadata={"doc_type": "legal"}),
        Document(page_content="api rate limits and SLAs", metadata={"doc_type": "technical"}),
    ])
    legal_only = store.similarity_search(
        "clause", k=5, filter_fn=lambda d: d.metadata.get("doc_type") == "legal")
    assert all(d.metadata.get("doc_type") == "legal" for d in legal_only)


def test_empty_store_returns_nothing(store):
    assert store.similarity_search("anything") == []
    assert store.get_vector_count() == 0
