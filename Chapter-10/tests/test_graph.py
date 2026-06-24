"""
Graph wiring tests. Routing functions are pure and tested directly; the graph
build is smoke-tested with an in-memory checkpointer (no SQLite file, no model).
"""
from langgraph.checkpoint.memory import MemorySaver

from src.graph import (
    build_graph,
    route_after_classification,
    route_after_risk_assessment,
    route_after_human_review,
)
from src.config import settings


# ── routing ───────────────────────────────────────────────────────────

def test_route_classification_by_type():
    assert route_after_classification({"document_type": "legal"})     == "legal_analysis"
    assert route_after_classification({"document_type": "financial"}) == "financial_analysis"
    assert route_after_classification({"document_type": "mystery"})   == "general_summary"


def test_route_classification_short_circuits_on_error():
    assert route_after_classification({"errors": ["bad"], "document_type": "legal"}) == "finalize"


def test_route_risk_to_human_when_flagged():
    assert route_after_risk_assessment({"requires_human_review": True}) == "human_review_gate"
    assert route_after_risk_assessment({"requires_human_review": False}) == "finalize"


def test_route_human_review_paths():
    assert route_after_human_review({"human_decision": "approved"}) == "finalize"
    assert route_after_human_review(
        {"human_decision": "needs_revision", "revision_count": 0}
    ) == "re_classify"


def test_route_human_review_respects_revision_cap():
    # At the hard cap, terminate regardless of the decision (Failure 1).
    assert route_after_human_review({
        "human_decision": "needs_revision",
        "revision_count": settings.max_revisions,
    }) == "finalize"


# ── build ─────────────────────────────────────────────────────────────

def test_graph_builds_with_expected_nodes():
    app = build_graph(checkpointer=MemorySaver())
    node_names = set(app.get_graph().nodes)
    for expected in ["ingest", "classify", "risk_assessment",
                     "human_review_gate", "finalize"]:
        assert expected in node_names
