"""
Wiring the intelligence pipeline into a LangGraph.

The flow is: check relevance, and stop early if the content is not relevant;
otherwise recall related past intelligence, analyse the content, and stop if
there is nothing new; otherwise write the brief and store it back so future
runs can use it as context.

The models, the vector store and the checkpointer are all injected. Production
passes real Ollama models, the pgvector store and a Postgres checkpointer; tests
pass fakes, the in memory backend and an in memory checkpointer.

The store arrives unscoped and neither node can search it. Both start by calling
`for_customer(state["customer_id"])`, so retrieval and storage are pinned to the
customer the API authenticated, and a run with no customer id raises instead of
reading everybody's data.
"""
import functools
import logging
from datetime import datetime, timezone

from langgraph.graph import StateGraph, START, END
from langchain_core.documents import Document

from src.monitor.state import IntelligenceState
from src.monitor.nodes import make_nodes

logger = logging.getLogger(__name__)


def _retrieve_context(state: dict, vector_store) -> dict:
    """
    Recall this customer's related past intelligence so analysis can spot what is
    truly new. The scope is taken before the query, so the search cannot be run
    without it.
    """
    scope = vector_store.for_customer(state.get("customer_id"))
    query = f"{state.get('topic', '')} {state.get('content_title', '')}"
    results = scope.similarity_search(query, k=3)
    past = [
        f"[{doc.metadata.get('scraped_at', 'unknown date')}] {doc.page_content[:300]}"
        for doc in results
        if doc.metadata.get("monitor_id") != state.get("monitor_id")
    ]
    return {"related_past_intel": past, "current_step": "retrieve_context"}


def _store_brief(state: dict, vector_store) -> dict:
    """Store the finished brief so later runs by this customer can recall it."""
    brief = state.get("intelligence_brief", "")
    if not brief:
        return {"current_step": "store_brief"}
    scope = vector_store.for_customer(state.get("customer_id"))
    doc = Document(
        page_content=brief,
        metadata={
            "monitor_id": state.get("monitor_id", ""),
            "topic": state.get("topic", ""),
            "source": state.get("content_url", ""),
            "scraped_at": datetime.now(timezone.utc).isoformat(),
            "urgency": state.get("urgency", "low"),
            "type": "intelligence_brief",
        },
    )
    try:
        scope.add_documents([doc])
    except Exception as exc:
        return {"errors": [*state.get("errors", []), f"Brief storage failed: {exc}"],
                "current_step": "store_brief"}
    return {"current_step": "store_brief"}


def build_intelligence_graph(vector_store, fast_model=None, quality_model=None,
                             checkpointer=None):
    if fast_model is None or quality_model is None:
        from langchain_ollama import ChatOllama
        from src.config import settings
        fast_model = fast_model or ChatOllama(model=settings.fast_model, temperature=0.0)
        quality_model = quality_model or ChatOllama(model=settings.quality_model, temperature=0.2)

    if checkpointer is None:
        from langgraph.checkpoint.memory import MemorySaver
        checkpointer = MemorySaver()

    check_relevance, analyze_content, generate_brief = make_nodes(fast_model, quality_model)
    retrieve_fn = functools.partial(_retrieve_context, vector_store=vector_store)
    store_fn = functools.partial(_store_brief, vector_store=vector_store)

    def route_after_relevance(state: dict) -> str:
        return "retrieve_context" if state.get("is_relevant") else "end"

    def route_after_analysis(state: dict) -> str:
        return "generate_brief" if state.get("key_developments") else "end"

    graph = StateGraph(IntelligenceState)
    graph.add_node("check_relevance", check_relevance)
    graph.add_node("retrieve_context", retrieve_fn)
    graph.add_node("analyze_content", analyze_content)
    graph.add_node("generate_brief", generate_brief)
    graph.add_node("store_brief", store_fn)

    graph.add_edge(START, "check_relevance")
    graph.add_conditional_edges("check_relevance", route_after_relevance,
                                {"retrieve_context": "retrieve_context", "end": END})
    graph.add_edge("retrieve_context", "analyze_content")
    graph.add_conditional_edges("analyze_content", route_after_analysis,
                                {"generate_brief": "generate_brief", "end": END})
    graph.add_edge("generate_brief", "store_brief")
    graph.add_edge("store_brief", END)

    return graph.compile(checkpointer=checkpointer)
