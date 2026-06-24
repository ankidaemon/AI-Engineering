"""
Re-analysis node.

Reached when a human reviewer requests revisions. It increments the revision
counter (the hard safety bound that prevents an infinite review loop — see
graph.route_after_human_review and Chapter 10, Failure 1) and routes back into
classification so the document is re-analyzed with the reviewer's feedback in
state.
"""
from src.state import WorkflowState


def re_classify(state: WorkflowState) -> dict:
    return {
        "revision_count": state.get("revision_count", 0) + 1,
        "current_step":   "re_classify",
    }
