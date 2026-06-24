"""
Human-review gate node.

This node exists to be *interrupted before* it runs. The graph is compiled with
`interrupt_before=["human_review_gate"]`, so execution pauses here and returns
control to the caller. External code (the conversation/API layer) injects the
reviewer's decision via `app.update_state(..., as_node="human_review_gate")`
and then resumes. The body is intentionally trivial.
"""
from src.state import WorkflowState


def human_review_gate(state: WorkflowState) -> dict:
    return {"current_step": "human_review_gate"}
