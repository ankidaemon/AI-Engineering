"""
Chain tests. Building a chain constructs a ChatOllama object but makes no
network call, so we can assert structure offline. The self-eval loop is tested
with mocked generation and evaluation chains.
"""
from unittest.mock import MagicMock

from src.chains.classification_chain import DocumentClassification, build_classification_chain
from src.chains.risk_chain import RiskAssessmentResult
from src.chains.analysis_chains import (
    LegalDoc,
    build_legal_analysis_chain,
    build_general_summary_chain,
)
from src.chains.self_eval_chain import SelfEvaluatingChain


# ── schemas ───────────────────────────────────────────────────────────

def test_classification_schema_round_trips():
    obj = DocumentClassification(
        document_type="legal", document_language="English",
        estimated_complexity="high", requires_human_review=True,
        classification_notes="contract",
    )
    assert obj.document_type == "legal"


def test_risk_schema_accepts_decision_options():
    obj = RiskAssessmentResult(
        risk_flags=["x"], risk_level="high", requires_human_review=True,
        recommendations=["y"], decision_options=[{"option": "a", "pros": [], "cons": []}],
    )
    assert obj.risk_level == "high"


def test_legal_schema_fields():
    assert "parties" in LegalDoc.model_fields


# ── builders return runnables ─────────────────────────────────────────

def test_builders_return_invokable_chains():
    for build in (build_classification_chain, build_legal_analysis_chain,
                  build_general_summary_chain):
        chain = build()
        assert hasattr(chain, "invoke")


# ── self-evaluation loop ──────────────────────────────────────────────

def _self_eval_with_mocks(gen_outputs, eval_outputs):
    gen = MagicMock()
    gen.invoke.side_effect = gen_outputs
    sec = SelfEvaluatingChain(generation_chain=gen, max_retries=2, min_score=7)
    ev = MagicMock()
    ev.invoke.side_effect = eval_outputs
    sec._eval_chain = ev          # bypass the real evaluator
    return sec, gen


def test_self_eval_accepts_on_first_pass():
    sec, gen = _self_eval_with_mocks(
        gen_outputs=["good output"],
        eval_outputs=[{"is_acceptable": True, "score": 9}],
    )
    out = sec.invoke({"task": "summarize"})
    assert out["attempts"] == 1
    assert gen.invoke.call_count == 1   # no retry


def test_self_eval_retries_then_stops_at_budget():
    sec, gen = _self_eval_with_mocks(
        gen_outputs=["v1", "v2"],
        eval_outputs=[
            {"is_acceptable": False, "score": 4, "revision_guidance": "more detail"},
            {"is_acceptable": False, "score": 5, "revision_guidance": "still weak"},
        ],
    )
    out = sec.invoke({"task": "summarize"})
    assert out["attempts"] == 2
    assert gen.invoke.call_count == 2   # initial + one retry, then budget exhausted
