"""
WorkflowState — the single source of truth that flows through every node.

A LangGraph node receives this dict and returns a *partial* update (only the
fields it changed). By default an update replaces a field; the `messages` field
is the exception — its `operator.add` reducer means node updates are *appended*
to the running message history rather than overwriting it.

`total=False` makes every field optional, so an initial state can supply only
what it has and let nodes fill in the rest.
"""
from typing import TypedDict, Annotated, Sequence
from langchain_core.messages import BaseMessage
import operator

# Bump this whenever the shape of WorkflowState changes. The ingest node
# compares it against the version stored in a resumed checkpoint and restarts
# from scratch on a mismatch (see Chapter 10, Failure 5 — stale checkpoints).
STATE_SCHEMA_VERSION = 1


class WorkflowState(TypedDict, total=False):
    # ── Input ─────────────────────────────────────────────────────────
    document_text:     str
    document_id:       str
    document_filename: str
    requester_id:      str

    # ── Classification ────────────────────────────────────────────────
    document_type:        str   # legal | technical | financial | general
    document_language:    str
    estimated_complexity: str   # low | medium | high

    # ── Analysis outputs ──────────────────────────────────────────────
    analysis_result: dict       # shape varies by document_type
    summary:         str
    key_points:      list[str]
    action_items:    list[str]

    # ── Risk assessment ───────────────────────────────────────────────
    risk_flags:            list[str]
    risk_level:            str   # low | medium | high | critical
    requires_human_review: bool

    # ── Decision support ──────────────────────────────────────────────
    recommendations:  list[str]
    decision_options: list[dict]   # [{"option": str, "pros": [...], "cons": [...]}]

    # ── Human review ──────────────────────────────────────────────────
    human_reviewer: str
    human_decision: str   # approved | needs_revision
    human_feedback: str
    revision_count: int

    # ── Output ────────────────────────────────────────────────────────
    final_report:    dict
    report_markdown: str

    # ── Conversation (appended, not replaced) ─────────────────────────
    messages: Annotated[Sequence[BaseMessage], operator.add]

    # ── Metadata ──────────────────────────────────────────────────────
    state_schema_version: int
    errors:               list[str]
    current_step:         str
    processing_time_ms:   dict   # step_name -> milliseconds
