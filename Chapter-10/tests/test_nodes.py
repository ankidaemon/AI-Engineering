"""
Node unit tests. Nodes are pure functions of state, so each is testable in
isolation. LLM-backed nodes are tested by patching their chain builder, so no
model server is required.
"""
from unittest.mock import patch, MagicMock

from src.nodes.ingestion      import ingest_document
from src.nodes.classification import classify_document
from src.nodes.finalization   import generate_final_report


def make_state(**overrides):
    defaults = {
        "document_text": (
            "This Software License Agreement is entered into between Alpha Corp "
            "and Beta Inc. The licensor grants a non-exclusive license to use the "
            "software. Indemnification clauses apply."
        ),
        "document_id":        "TEST-001",
        "errors":             [],
        "messages":           [],
        "processing_time_ms": {},
    }
    return {**defaults, **overrides}


# ── ingestion ─────────────────────────────────────────────────────────

def test_ingest_rejects_empty_document():
    result = ingest_document(make_state(document_text="   "))
    assert any("empty" in e.lower() for e in result["errors"])


def test_ingest_normalizes_and_counts():
    result = ingest_document(make_state(document_text="word  word\n\n\n\nword"))
    assert "\n\n\n" not in result["document_text"]
    assert result["errors"] == []
    assert result["current_step"] == "ingest_document"


# ── classification (chain builder patched) ────────────────────────────

@patch("src.nodes.classification.build_classification_chain")
def test_classification_validates_unknown_type(mock_builder):
    chain = MagicMock()
    chain.invoke.return_value = {"document_type": "poetry", "estimated_complexity": "low"}
    mock_builder.return_value = chain

    result = classify_document(make_state())
    # Unknown type must fall back to "general".
    assert result["document_type"] == "general"


@patch("src.nodes.classification.build_classification_chain")
def test_classification_defaults_on_exception(mock_builder):
    chain = MagicMock()
    chain.invoke.side_effect = ValueError("boom")
    mock_builder.return_value = chain

    result = classify_document(make_state())
    assert result["document_type"] == "general"
    assert any("Classification error" in e for e in result["errors"])


def test_classification_skips_when_prior_errors():
    result = classify_document(make_state(errors=["Document text is empty"]))
    assert result == {"current_step": "classify_document"}


# ── finalization (pure, no LLM) ───────────────────────────────────────

def test_finalization_produces_markdown():
    state = make_state(
        document_type="legal",
        summary="A software license agreement between two parties.",
        key_points=["Non-exclusive license", "Indemnification applies"],
        risk_flags=["No termination clause found"],
        recommendations=["Add termination clause"],
        decision_options=[{"option": "Sign as-is", "pros": ["Fast"], "cons": ["Risky"]}],
        risk_level="medium",
        revision_count=0,
        human_decision="approved",
        human_feedback="",
    )
    result = generate_final_report(state)

    assert "final_report" in result
    assert "## Executive Summary" in result["report_markdown"]
    assert "## Risk Flags" in result["report_markdown"]
    assert "MEDIUM" in result["report_markdown"]


def test_finalization_handles_empty_lists():
    state = make_state(
        document_type="general", summary="A document.",
        key_points=[], risk_flags=[], recommendations=[],
        decision_options=[], risk_level="low",
    )
    result = generate_final_report(state)
    assert result["final_report"]["risk_level"] == "low"
    assert isinstance(result["report_markdown"], str)
