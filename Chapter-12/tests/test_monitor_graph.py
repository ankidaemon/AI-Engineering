"""
End to end test of the intelligence pipeline with fake models and a fake store.

No Ollama, no database, no network. The fake chat models return canned JSON and
text, so we can drive the whole graph and assert on its routing and output.
"""
import pytest
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langgraph.checkpoint.memory import MemorySaver

from src.monitor.graph import build_intelligence_graph
from src.vectorstores.pgvector_store import make_vector_store


def make_store():
    """The real store with the in memory backend. The graph is handed the
    unscoped object and has to scope it itself, which is the behaviour under
    test in `test_tenancy.py`."""
    return make_vector_store("memory")


RELEVANT = '{"relevance_score": 0.9, "content_type": "news", "is_relevant": true, "skip_reason": ""}'
NOT_RELEVANT = '{"relevance_score": 0.1, "content_type": "blog", "is_relevant": false, "skip_reason": "off topic"}'
ANALYSIS = ('{"key_developments": ["a new regulation was proposed"], '
            '"impact_assessment": "significant for compliance teams", '
            '"entities": ["European Parliament"], "sentiment": "neutral", '
            '"urgency": "high", "action_items": ["brief the legal team"]}')
BRIEF = "HIGH PRIORITY: a new regulation was proposed that affects compliance."


def _state():
    return {
        "content_url": "http://example.com/reg",
        "content_text": "A long article about a proposed AI regulation and its impact.",
        "content_title": "New AI regulation proposed",
        "topic": "AI regulation",
        "monitor_id": "sess-1",
        "customer_id": "acme",
        "errors": [],
        "messages": [],
    }


def test_relevant_content_produces_and_stores_brief():
    store = make_store()
    graph = build_intelligence_graph(
        store,
        fast_model=FakeListChatModel(responses=[RELEVANT]),
        quality_model=FakeListChatModel(responses=[ANALYSIS, BRIEF]),
        checkpointer=MemorySaver(),
    )
    final = graph.invoke(_state(), {"configurable": {"thread_id": "sess-1"}})

    assert final["is_relevant"] is True
    assert final["intelligence_brief"] == BRIEF
    assert final["urgency"] == "high"
    stored = store.for_customer("acme").similarity_search("regulation", k=5)
    assert stored, "the brief should be stored back into the vector store"


def test_brief_survives_model_output_containing_braces():
    """A real model can return developments or actions with curly braces (it
    once leaked JSON schema text like {'description': ...}). The brief prompt
    must treat that as literal content, not as template variables, and not crash."""
    store = make_store()
    analysis_with_braces = (
        '{"key_developments": ["a rule {description} was proposed"], '
        '"impact_assessment": "affects {compliance} teams", '
        '"entities": ["EU"], "sentiment": "neutral", '
        '"urgency": "high", "action_items": ["review {policy} docs"]}'
    )
    graph = build_intelligence_graph(
        store,
        fast_model=FakeListChatModel(responses=[RELEVANT]),
        quality_model=FakeListChatModel(responses=[analysis_with_braces, BRIEF]),
        checkpointer=MemorySaver(),
    )
    final = graph.invoke(_state(), {"configurable": {"thread_id": "sess-braces"}})
    assert final["intelligence_brief"] == BRIEF
    assert store.for_customer("acme").similarity_search("regulation", k=5)


def test_irrelevant_content_stops_early():
    store = make_store()
    graph = build_intelligence_graph(
        store,
        fast_model=FakeListChatModel(responses=[NOT_RELEVANT]),
        quality_model=FakeListChatModel(responses=[ANALYSIS, BRIEF]),
        checkpointer=MemorySaver(),
    )
    final = graph.invoke(_state(), {"configurable": {"thread_id": "sess-2"}})

    assert final["is_relevant"] is False
    assert not final.get("intelligence_brief")
    assert store.total_vector_count() == 0
