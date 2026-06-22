from unittest.mock import MagicMock
from src.retrieval.reranker import CrossEncoderReranker


def _make_reranker(scores):
    """Build a reranker without loading a real cross-encoder model."""
    reranker = CrossEncoderReranker.__new__(CrossEncoderReranker)
    reranker._model = MagicMock()
    reranker._model.predict.return_value = scores
    return reranker


def test_rerank_orders_by_relevance_and_truncates():
    reranker = _make_reranker([0.1, 0.9, 0.5])
    candidates = [
        {"chunk_id": "a", "content": "loosely related passage"},
        {"chunk_id": "b", "content": "the passage that answers the query"},
        {"chunk_id": "c", "content": "somewhat related passage"},
    ]

    out = reranker.rerank("the query", candidates, top_k=2)

    # Highest cross-encoder score first, lowest dropped by top_k
    assert [c["chunk_id"] for c in out] == ["b", "c"]
    assert out[0]["rerank_score"] == 0.9
    assert len(out) == 2


def test_rerank_scores_query_passage_pairs():
    reranker = _make_reranker([0.4, 0.6])
    candidates = [
        {"chunk_id": "a", "content": "first"},
        {"chunk_id": "b", "content": "second"},
    ]

    reranker.rerank("q", candidates)

    pairs = reranker._model.predict.call_args[0][0]
    assert pairs == [("q", "first"), ("q", "second")]


def test_rerank_empty_candidates_returns_empty():
    reranker = _make_reranker([])
    assert reranker.rerank("q", []) == []
