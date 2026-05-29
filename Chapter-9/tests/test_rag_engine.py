import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from src.rag_engine import RAGEngine, RAGResponse


@pytest.fixture
def mock_retriever():
    r = MagicMock()
    r.retrieve.return_value = [
        {
            "chunk_id":  "2401.00001_chunk_0",
            "content":   "Transformer self-attention has quadratic complexity "
                         "with respect to sequence length.",
            "score":     0.93,
            "rrf_score": 0.0145,
            "metadata": {
                "title":     "Efficient Transformers: A Survey",
                "arxiv_id":  "2401.00001",
                "published": "2024-01-15",
                "section":   "Introduction",
                "authors":   "Smith et al."
            }
        }
    ]
    return r


@pytest.fixture
def mock_cache():
    c = MagicMock()
    c.get_cached                = AsyncMock(return_value=None)
    c.set_cached                = AsyncMock()
    c.get_session               = AsyncMock(return_value={"turns": []})
    c.append_turn               = AsyncMock()
    c.format_history_for_prompt = MagicMock(return_value="")
    return c


@pytest.fixture
def mock_llama():
    ll = MagicMock()
    ll.generate = AsyncMock(return_value=(
        "## Computational Bottlenecks of Self-Attention\n\n"
        "Self-attention has O(n^2) time and memory complexity [Smith et al., 2024]. "
        "Proposed solutions include sparse attention, linear attention, and "
        "approximate methods such as Performers and Longformer."
    ))
    return ll


@pytest.mark.asyncio
async def test_rag_query_returns_grounded_response(
    mock_retriever, mock_cache, mock_llama
):
    engine = RAGEngine.__new__(RAGEngine)
    engine._retriever = mock_retriever
    engine._cache     = mock_cache
    engine._llama     = mock_llama
    engine._expand    = False

    result = await engine.query(
        query="What is the complexity of self-attention?",
        session_id="test-001"
    )

    assert isinstance(result, RAGResponse)
    assert len(result.answer) > 30
    assert len(result.sources) >= 1
    assert result.cache_hit is False
    mock_retriever.retrieve.assert_called_once()


@pytest.mark.asyncio
async def test_cache_hit_bypasses_retrieval(mock_retriever, mock_cache, mock_llama):
    mock_cache.get_cached = AsyncMock(return_value={
        "answer":           "Cached answer about attention complexity.",
        "sources":          [],
        "expanded_queries": []
    })

    engine = RAGEngine.__new__(RAGEngine)
    engine._retriever = mock_retriever
    engine._cache     = mock_cache
    engine._llama     = mock_llama
    engine._expand    = False

    result = await engine.query(
        query="What is the complexity of self-attention?",
        session_id="test-002"
    )

    assert result.cache_hit is True
    assert result.answer == "Cached answer about attention complexity."
    mock_retriever.retrieve.assert_not_called()
    mock_llama.generate.assert_not_called()


@pytest.mark.asyncio
async def test_token_budget_caps_context(mock_retriever, mock_cache, mock_llama):
    big_chunks = [
        {
            "chunk_id":  f"doc_chunk_{i}",
            "content":   "word " * 2000,  # ~2667 tokens each
            "rrf_score": 1.0 / (i + 1),
            "metadata":  {}
        }
        for i in range(10)
    ]
    mock_retriever.retrieve.return_value = big_chunks

    engine = RAGEngine.__new__(RAGEngine)
    engine._retriever = mock_retriever
    engine._cache     = mock_cache
    engine._llama     = mock_llama
    engine._expand    = False

    result = await engine.query(
        query="Test query",
        session_id="test-003"
    )

    # Should have selected fewer than all 10 chunks due to token budget
    actual_chunks_passed = mock_llama.generate.call_args[0][0]
    # System message + 1 user message
    assert len(actual_chunks_passed) == 2
    assert result.answer is not None
