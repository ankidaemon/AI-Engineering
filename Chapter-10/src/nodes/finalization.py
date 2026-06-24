"""
Finalization node — deterministic report assembly (no LLM).

Collects everything accumulated in state into a structured report dict and a
human-readable markdown rendering. Kept LLM-free on purpose: it is fast,
deterministic, and unit-testable without a model (see tests/test_nodes.py).
For a polished prose narrative, call chains.synthesis_chain separately.
"""
from datetime import datetime, timezone
from langchain_core.messages import AIMessage
from src.state import WorkflowState


def generate_final_report(state: WorkflowState) -> dict:
    report = {
        "document_id":      state.get("document_id", "unknown"),
        "document_type":    state.get("document_type", "general"),
        "risk_level":       state.get("risk_level", "unknown"),
        "generated_at":     datetime.now(timezone.utc).isoformat(),
        "summary":          state.get("summary", ""),
        "key_points":       state.get("key_points", []),
        "action_items":     state.get("action_items", []),
        "risk_flags":       state.get("risk_flags", []),
        "recommendations":  state.get("recommendations", []),
        "decision_options": state.get("decision_options", []),
        "human_decision":   state.get("human_decision", "not_required"),
        "human_feedback":   state.get("human_feedback", ""),
        "revision_count":   state.get("revision_count", 0),
        "processing_time":  state.get("processing_time_ms", {}),
        "errors":           state.get("errors", []),
    }

    md = [
        "# Document Analysis Report",
        f"**Document ID:** {report['document_id']}",
        f"**Type:** {str(report['document_type']).title()}",
        f"**Risk Level:** {str(report['risk_level']).upper()}",
        f"**Generated:** {report['generated_at']}",
        "",
        "## Executive Summary",
        report["summary"] or "_No summary generated._",
        "",
        "## Key Points",
    ]
    md += [f"- {p}" for p in report["key_points"]]

    md += ["", "## Risk Flags"]
    md += [f"- ⚠️ {flag}" for flag in report["risk_flags"]]

    md += ["", "## Recommendations"]
    md += [f"- {rec}" for rec in report["recommendations"]]

    md += ["", "## Decision Options"]
    for i, opt in enumerate(report["decision_options"], 1):
        md.append(f"### Option {i}: {opt.get('option', '')}")
        md.append("**Pros:**")
        md += [f"  - {pro}" for pro in opt.get("pros", [])]
        md.append("**Cons:**")
        md += [f"  - {con}" for con in opt.get("cons", [])]
        md.append("")

    if report["errors"]:
        md += ["## Processing Notes"]
        md += [f"- ℹ️ {err}" for err in report["errors"]]

    return {
        "final_report":    report,
        "report_markdown": "\n".join(md),
        "current_step":    "finalize",
        "messages":        [AIMessage(content="Final report generated successfully.")],
    }
