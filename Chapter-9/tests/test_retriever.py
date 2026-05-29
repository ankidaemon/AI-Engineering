import pytest
from unittest.mock import MagicMock, patch
from src.retrieval.hybrid_retriever import HybridRetriever
from src.retrieval.bm25_index import BM25Index
from src.ingestion.chunker import Chunk


@pytest.fixture
def sample_chunks():
    return [
        Chunk(
            content="Transformer attention mechanisms use query key value projections.",
            metadata={"title": "Attention Is All You Need", "section": "Methods"},
            chunk_id="vaswani_chunk_0",
            doc_id="vaswani",
            chunk_index=0
        ),
        Chunk(
            content="BERT uses bidirectional transformer encoders for language modeling.",
            metadata={"title": "BERT", "section": "Introduction"},
            chunk_id="devlin_chunk_0",
            doc_id="devlin",
            chunk_index=0
        ),
        Chunk(
            content="GPT uses autoregressive transformer decoders for text generation.",
            metadata={"title": "GPT", "section": "Methods"},
            chunk_id="gpt_chunk_0",
            doc_id="gpt",
            chunk_index=0
        ),
    ]


def test_bm25_index_and_query(tmp_path, sample_chunks):
    with patch.object(BM25Index, "PERSIST_PATH", tmp_path / "bm25.pkl"):
        index = BM25Index()
        index.index_chunks(sample_chunks)

        results = index.query("transformer attention", top_k=3)
        assert len(results) > 0
        assert all("chunk_id" in r for r in results)
        assert all("score" in r for r in results)


def test_bm25_returns_relevant_result(tmp_path, sample_chunks):
    with patch.object(BM25Index, "PERSIST_PATH", tmp_path / "bm25.pkl"):
        index = BM25Index()
        index.index_chunks(sample_chunks)

        results = index.query("BERT bidirectional encoder", top_k=3)
        top_result = results[0]
        assert "devlin" in top_result["chunk_id"]


def test_bm25_empty_query_returns_empty(tmp_path, sample_chunks):
    with patch.object(BM25Index, "PERSIST_PATH", tmp_path / "bm25.pkl"):
        index = BM25Index()
        index.index_chunks(sample_chunks)

        results = index.query("", top_k=3)
        assert results == []


def test_bm25_empty_index_returns_empty(tmp_path):
    with patch.object(BM25Index, "PERSIST_PATH", tmp_path / "bm25.pkl"):
        index = BM25Index()
        results = index.query("transformer", top_k=3)
        assert results == []


def test_rrf_merge_boosts_overlap():
    retriever = HybridRetriever.__new__(HybridRetriever)
    retriever._alpha = 0.7
    retriever.RRF_K  = 60

    dense = [
        {"chunk_id": "doc_A", "content": "A", "score": 0.9, "metadata": {}},
        {"chunk_id": "doc_B", "content": "B", "score": 0.8, "metadata": {}},
    ]
    sparse = [
        {"chunk_id": "doc_A", "content": "A", "score": 5.0, "metadata": {}},
        {"chunk_id": "doc_C", "content": "C", "score": 4.0, "metadata": {}},
    ]

    merged = retriever._rrf_merge(dense, sparse)

    # doc_A appears in both lists — should rank first
    assert merged[0]["chunk_id"] == "doc_A"
    assert merged[0]["rrf_score"] > merged[1]["rrf_score"]
