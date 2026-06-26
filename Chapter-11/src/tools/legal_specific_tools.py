"""
Legal-specialist tools (Section 6.3).

These are model-backed: each wraps a focused prompt around the quality model. The
parsing helpers are factored out as pure functions so they can be unit-tested
without a model (see tests/test_tools.py), and every tool fails soft — a tool
that raises would take the whole agent down with it.
"""
import json
import re

from langchain_core.messages import HumanMessage
from langchain_core.tools import tool

from src.models import get_quality_model


# ── pure parsing helpers (unit-tested directly) ───────────────────────────

def _extract_json_obligations(content: str) -> dict:
    """Pull an obligations object out of a model reply, falling back to raw text."""
    match = re.search(r"\{.*\}", content, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return {"obligations": [{"raw": content}]}


def _parse_bullets(content: str) -> list[str]:
    """Turn a bulleted/numbered model reply into a clean list of strings."""
    lines = [
        line.strip().lstrip("•-*0123456789. ").strip()
        for line in content.split("\n")
        if line.strip() and any(c in line for c in "•-*0123456789")
    ]
    return lines if lines else [content.strip()]


# ── tools ─────────────────────────────────────────────────────────────────

@tool
def extract_obligations_tool(clause_text: str) -> dict:
    """
    Extracts obligations from a contract clause: who must do what, by when.
    Use this on any clause containing 'shall', 'must', 'agrees to', or 'will'.
    """
    prompt = (
        f"From this contract text, extract every obligation. For each, give the "
        f"party, the required action, and any deadline or condition.\n\n"
        f"Text:\n{clause_text}\n\n"
        f'Return JSON: {{"obligations": [{{"party": str, "action": str, '
        f'"deadline": str, "condition": str}}]}}'
    )
    response = get_quality_model(temperature=0).invoke([HumanMessage(content=prompt)])
    return _extract_json_obligations(response.content)


@tool
def flag_unusual_clauses_tool(contract_text: str) -> list[str]:
    """
    Identifies non-standard, aggressive, or unusual clauses a lawyer should review.
    Returns a list of flagged items, each with a short reason.
    Use this to find provisions that deviate from market standard.
    """
    prompt = (
        f"Review this contract text and identify any unusual, aggressive, or "
        f"non-standard clauses that a lawyer should flag. For each, briefly say "
        f"why it is unusual.\n\nContract text:\n{contract_text[:3000]}\n\n"
        f"List the flagged items as bullet points."
    )
    response = get_quality_model(temperature=0).invoke([HumanMessage(content=prompt)])
    return _parse_bullets(response.content)


@tool
def compute_liability_exposure_tool(liability_section: str) -> dict:
    """
    Analyzes a liability/indemnification section and summarizes the exposure.
    Returns the cap, excluded damages, carve-outs, and indemnification duties.
    Use this for any section about limitation of liability or indemnification.
    """
    prompt = (
        f"Analyze this liability section and extract: (1) the liability cap if "
        f"any, (2) excluded damage types, (3) carve-outs from the cap, "
        f"(4) indemnification obligations.\n\nText:\n{liability_section}\n\n"
        f"Respond with a structured analysis."
    )
    response = get_quality_model(temperature=0).invoke([HumanMessage(content=prompt)])
    return {"analysis": response.content,
            "section_length": len(liability_section.split())}
