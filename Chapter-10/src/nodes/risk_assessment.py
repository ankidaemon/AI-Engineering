"""
Risk assessment node.

Reads the analysis outputs from state, runs the risk chain, and merges its
human-review verdict with any flag already set during classification (logical
OR — once flagged, always flagged). On failure it defaults to medium risk and
*forces* human review, failing safe rather than waving a document through.
"""
import time
import logging
from langchain_core.messages import AIMessage
from src.state import WorkflowState
from src.chains.risk_chain import build_risk_chain

logger = logging.getLogger(__name__)


def assess_risks(state: WorkflowState) -> dict:
    start = time.time()
    already_flagged = state.get("requires_human_review", False)

    try:
        chain = build_risk_chain()
        result = chain.invoke({
            "document_type": state.get("document_type", "general"),
            "summary":       state.get("summary", "No summary available"),
            "key_points":    "\n".join(f"- {p}" for p in state.get("key_points", [])),
            "action_items":  "\n".join(f"- {a}" for a in state.get("action_items", [])),
        })

        elapsed = int((time.time() - start) * 1000)
        risk_level = result.get("risk_level", "low")
        human_required = already_flagged or bool(result.get("requires_human_review", False))

        return {
            "risk_flags":            result.get("risk_flags", []),
            "risk_level":            risk_level,
            "requires_human_review": human_required,
            "recommendations":       result.get("recommendations", []),
            "decision_options":      result.get("decision_options", []),
            "current_step":          "risk_assessment",
            "processing_time_ms":    {**state.get("processing_time_ms", {}), "risk_assessment": elapsed},
            "messages": [AIMessage(content=(
                f"Risk assessment: {str(risk_level).upper()} | "
                f"{len(result.get('risk_flags', []))} flags | "
                f"Human review: {human_required}"
            ))],
        }
    except Exception as exc:
        logger.error("Risk assessment failed: %s", exc)
        return {
            "risk_level":            "medium",
            "requires_human_review": True,   # fail safe — escalate to a human
            "errors":                [*state.get("errors", []), f"Risk assessment error: {exc}"],
            "current_step":          "risk_assessment",
        }
