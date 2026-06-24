"""
Classification node.

Runs the classification chain on a cheap excerpt and writes the routing
metadata (type, language, complexity, human-review flag) into state. Defends
against bad model output two ways: an unknown document_type falls back to
"general", and any exception is caught, recorded in `errors`, and defaulted —
nodes must never raise (Chapter 10, Failure 3).
"""
import time
import logging
from langchain_core.messages import AIMessage
from src.state import WorkflowState
from src.chains.classification_chain import build_classification_chain

logger = logging.getLogger(__name__)

VALID_TYPES = {"legal", "technical", "financial", "general"}


def classify_document(state: WorkflowState) -> dict:
    # Short-circuit if ingestion already flagged a fatal problem.
    if state.get("errors"):
        return {"current_step": "classify_document"}

    start = time.time()
    excerpt = " ".join(state["document_text"].split()[:600])

    chain = build_classification_chain()
    try:
        result = chain.invoke({"excerpt": excerpt})
        doc_type = str(result.get("document_type", "general")).strip().lower()
        if doc_type not in VALID_TYPES:
            doc_type = "general"

        elapsed = int((time.time() - start) * 1000)
        return {
            "document_type":         doc_type,
            "document_language":     result.get("document_language", "English"),
            "estimated_complexity":  result.get("estimated_complexity", "medium"),
            "requires_human_review": bool(result.get("requires_human_review", False)),
            "current_step":          "classify_document",
            "processing_time_ms":    {**state.get("processing_time_ms", {}), "classify": elapsed},
            "messages": [AIMessage(content=(
                f"Classified as {doc_type} | "
                f"Complexity: {result.get('estimated_complexity', 'medium')} | "
                f"Human review: {result.get('requires_human_review', False)}"
            ))],
        }
    except Exception as exc:
        logger.error("Classification failed: %s", exc)
        return {
            "document_type": "general",
            "errors":        [*state.get("errors", []), f"Classification error: {exc}"],
            "current_step":  "classify_document",
        }
