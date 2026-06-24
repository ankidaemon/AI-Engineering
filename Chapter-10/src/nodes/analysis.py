"""
Analysis nodes — one per document type, plus a shared runner.

Each node builds its chain from src.chains.analysis_chains and delegates to
`_run_analysis`, which times the call, normalizes the output into the common
state fields (summary / action_items / analysis_result), and records errors
without raising. The general path produces markdown and is flagged accordingly.
"""
import time
import logging
from langchain_core.messages import AIMessage
from src.state import WorkflowState
from src.chains.analysis_chains import (
    build_legal_analysis_chain,
    build_technical_analysis_chain,
    build_financial_analysis_chain,
    build_general_summary_chain,
)

logger = logging.getLogger(__name__)


def analyze_legal_document(state: WorkflowState) -> dict:
    return _run_analysis(state, build_legal_analysis_chain(), "legal_analysis")


def analyze_technical_document(state: WorkflowState) -> dict:
    return _run_analysis(state, build_technical_analysis_chain(), "technical_analysis")


def analyze_financial_document(state: WorkflowState) -> dict:
    return _run_analysis(state, build_financial_analysis_chain(), "financial_analysis")


def summarize_general_document(state: WorkflowState) -> dict:
    return _run_analysis(state, build_general_summary_chain(), "general_summary", is_markdown=True)


def _run_analysis(state: WorkflowState, chain, step_name: str, is_markdown: bool = False) -> dict:
    # If classification failed, skip analysis and let routing send us to finalize.
    if any("Classification error" in e for e in state.get("errors", [])):
        return {"current_step": step_name}

    start = time.time()
    try:
        result = chain.invoke({"document": state["document_text"]})
        elapsed = int((time.time() - start) * 1000)

        if is_markdown:
            analysis     = {"raw": result}
            summary      = result
            action_items = []
            key_points   = []
        else:
            analysis     = result if isinstance(result, dict) else result.dict()
            summary      = analysis.get("summary", "")
            action_items = analysis.get("action_items", [])
            key_points   = analysis.get("key_obligations") or analysis.get("technologies") or []

        return {
            "analysis_result":    analysis,
            "summary":            summary,
            "action_items":       action_items,
            "key_points":         key_points,
            "current_step":       step_name,
            "processing_time_ms": {**state.get("processing_time_ms", {}), step_name: elapsed},
            "messages": [AIMessage(content=f"Analysis complete ({step_name}): "
                                           f"{len(str(result))} characters")],
        }
    except Exception as exc:
        logger.error("Analysis failed in %s: %s", step_name, exc)
        return {
            "errors":       [*state.get("errors", []), f"{step_name} error: {exc}"],
            "current_step": step_name,
        }
