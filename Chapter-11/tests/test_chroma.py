"""
ChromaDB wrapper tests. The store accepts an injectable embeddings object, so we
use a deterministic fake here — no Ollama, no network. Requires `chromadb`.

These exercise the two things Chroma adds over the raw FAISS library: built-in
metadata filtering and collection-based isolation (multi-tenancy).
"""
import hashlib

import pytest
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

from src.vectorstores.chroma_store import ChromaDocumentStore


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
def store(tmp_path):
    return ChromaDocumentStore(
        persist_dir=str(tmp_path / "chroma"),
        collection="test",
        embeddings=FakeEmbeddings(),
    )


def test_add_and_search(store):
    store.add_documents([
        Document(page_content="Termination requires 30 days notice.",
                 metadata={"doc_type": "legal"}),
        Document(page_content="System must support 10,000 concurrent users.",
                 metadata={"doc_type": "technical"}),
    ])
    results = store.similarity_search("termination", k=1)
    assert len(results) == 1


def test_metadata_filter(store):
    store.add_documents([
        Document(page_content="legal clause about liability", metadata={"doc_type": "legal"}),
        Document(page_content="api rate limits and SLAs", metadata={"doc_type": "technical"}),
    ])
    legal = store.similarity_search("clause", k=5, filter_dict={"doc_type": "legal"})
    assert legal and all(d.metadata.get("doc_type") == "legal" for d in legal)


def test_collections_are_isolated(store):
    store.add_documents([Document(page_content="alpha", metadata={})], collection="tenant_a")
    store.add_documents([Document(page_content="beta", metadata={})], collection="tenant_b")
    a = store.similarity_search("alpha", collection="tenant_a", k=5)
    b = store.similarity_search("alpha", collection="tenant_b", k=5)
    assert any("alpha" in d.page_content for d in a)
    assert all("alpha" not in d.page_content for d in b)
