"""
LangGraph assembly — wires the nodes into a stateful, cyclical workflow.

Flow:

    START -> ingest -> classify
                          │
            ┌─────────────┼───────────────┬───────────────┐
            ▼             ▼               ▼               ▼
      legal_analysis  technical_…   financial_…    general_summary
            └─────────────┴───────────────┴───────────────┘
                          ▼
                  risk_assessment
                          │
              requires_human_review?
                    │            │
                   yes           no
                    ▼            ▼
            human_review_gate  finalize -> END
                    │
        approved ───┴── needs_revision ──► re_classify ──► classify (loop)
            │                                  (capped at MAX_REVISIONS)
            ▼
         finalize -> END

The graph is compiled with `interrupt_before=["human_review_gate"]`, so it
pauses for a human decision and resumes via update_state(). A checkpointer
persists state across the pause (and across process restarts with SQLite).
"""
import logging
from pathlib import Path

from langgraph.graph import StateGraph, END, START

from src.config import settings
from src.state import WorkflowState
from src.nodes.ingestion       import ingest_document
from src.nodes.classification  import classify_document
from src.nodes.analysis        import (
    analyze_legal_document,
    analyze_technical_document,
    analyze_financial_document,
    summarize_general_document,
)
from src.nodes.risk_assessment import assess_risks
from src.nodes.human_review    import human_review_gate
from src.nodes.re_analysis     import re_classify
from src.nodes.finalization    import generate_final_report

logger = logging.getLogger(__name__)


# ── Edge functions (routing logic) ────────────────────────────────────

def route_after_classification(state: WorkflowState) -> str:
    if state.get("errors"):
        return "finalize"
    routing = {
        "legal":     "legal_analysis",
        "technical": "technical_analysis",
        "financial": "financial_analysis",
    }
    return routing.get(state.get("document_type", ""), "general_summary")


def route_after_risk_assessment(state: WorkflowState) -> str:
    return "human_review_gate" if state.get("requires_human_review", False) else "finalize"


def route_after_human_review(state: WorkflowState) -> str:
    if state.get("human_decision", "approved") == "approved":
        return "finalize"
    # Hard cap on revisions — terminate the cycle regardless of model/human output.
    if state.get("revision_count", 0) >= settings.max_revisions:
        logger.warning("Revision cap reached for %s — finalizing.", state.get("document_id"))
        return "finalize"
    return "re_classify"


# ── Checkpointer ──────────────────────────────────────────────────────

def _make_checkpointer(db_path: str):
    """
    Persistent SQLite checkpointer, with an in-memory fallback.

    Note: langgraph's `SqliteSaver.from_conn_string` is a context manager in
    recent releases — using its return value directly as a checkpointer is a
    common bug. We instead pass an explicit sqlite3 connection, which yields a
    real saver instance that persists across process restarts.
    """
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    try:
        import sqlite3
        from langgraph.checkpoint.sqlite import SqliteSaver
        conn = sqlite3.connect(db_path, check_same_thread=False)
        return SqliteSaver(conn)
    except Exception as exc:  # package missing, read-only FS, etc.
        from langgraph.checkpoint.memory import MemorySaver
        logger.warning("SqliteSaver unavailable (%s); using in-memory checkpointer.", exc)
        return MemorySaver()


# ── Graph builder ─────────────────────────────────────────────────────

def build_graph(db_path: str | None = None, checkpointer=None):
    graph = StateGraph(WorkflowState)

    graph.add_node("ingest",             ingest_document)
    graph.add_node("classify",           classify_document)
    graph.add_node("legal_analysis",     analyze_legal_document)
    graph.add_node("technical_analysis", analyze_technical_document)
    graph.add_node("financial_analysis", analyze_financial_document)
    graph.add_node("general_summary",    summarize_general_document)
    graph.add_node("risk_assessment",    assess_risks)
    graph.add_node("human_review_gate",  human_review_gate)
    graph.add_node("re_classify",        re_classify)
    graph.add_node("finalize",           generate_final_report)

    graph.add_edge(START, "ingest")
    graph.add_edge("ingest", "classify")

    graph.add_conditional_edges(
        "classify",
        route_after_classification,
        {
            "legal_analysis":     "legal_analysis",
            "technical_analysis": "technical_analysis",
            "financial_analysis": "financial_analysis",
            "general_summary":    "general_summary",
            "finalize":           "finalize",
        },
    )

    for node in ["legal_analysis", "technical_analysis",
                 "financial_analysis", "general_summary"]:
        graph.add_edge(node, "risk_assessment")

    graph.add_conditional_edges(
        "risk_assessment",
        route_after_risk_assessment,
        {"human_review_gate": "human_review_gate", "finalize": "finalize"},
    )

    graph.add_conditional_edges(
        "human_review_gate",
        route_after_human_review,
        {"finalize": "finalize", "re_classify": "re_classify"},
    )

    graph.add_edge("re_classify", "classify")
    graph.add_edge("finalize", END)

    checkpointer = checkpointer or _make_checkpointer(db_path or settings.checkpoint_db_path)
    return graph.compile(
        checkpointer=checkpointer,
        interrupt_before=["human_review_gate"],
    )


# Module-level singleton used by the conversation/API layers.
workflow_app = build_graph()
