"""Cost tracking, feedback logging, monitoring thresholds, and evaluators."""
from datetime import datetime, timedelta

from src.observability.tracing import CostTracker, log_user_feedback, traced
from src.observability.monitoring import (
    MetricThresholds, ProductionMetrics, check_thresholds,
)
from src.observability.evaluation import exact_match, contains_reference, keyword_recall


# ── Cost tracker ─────────────────────────────────────────────────────

def test_cost_tracker_accumulates():
    ct = CostTracker()
    ct.estimate_cost("gpt-4o-mini", 1_000_000, 1_000_000)
    summary = ct.session_summary()
    assert summary["total_cost_usd"] == 0.75          # 0.15 input + 0.60 output
    assert summary["total_input_tokens"] == 1_000_000


def test_self_hosted_is_free_in_tracker():
    ct = CostTracker()
    assert ct.estimate_cost("llama3.1:70b", 5000, 5000) == 0.0


def test_traced_runs_function_even_without_langsmith():
    @traced(name="double")
    def double(x):
        return x * 2

    assert double(21) == 42


# ── Feedback logging with an injected fake client ────────────────────

class FakeLangSmith:
    def __init__(self):
        self.feedback = []

    def create_feedback(self, run_id, key, score, comment):
        self.feedback.append((run_id, key, score, comment))


def test_feedback_uses_injected_client():
    fake = FakeLangSmith()
    assert log_user_feedback("run-123", 1.0, "great", client=fake) is True
    assert fake.feedback == [("run-123", "user_score", 1.0, "great")]


def test_feedback_never_raises_on_error():
    class Broken:
        def create_feedback(self, **kwargs):
            raise RuntimeError("network down")

    assert log_user_feedback("run-1", 0.0, client=Broken()) is False


# ── Monitoring thresholds (pure function) ────────────────────────────

def _metrics(**kwargs) -> ProductionMetrics:
    now = datetime.utcnow()
    base = dict(period_start=now - timedelta(hours=1), period_end=now)
    base.update(kwargs)
    return ProductionMetrics(**base)


def test_no_alerts_when_healthy():
    m = _metrics(run_count=100, error_count=1, p95_latency_ms=3000, estimated_cost_usd=1.0)
    assert check_thresholds(m, MetricThresholds()) == []


def test_latency_alert():
    m = _metrics(run_count=100, p95_latency_ms=9000)
    alerts = check_thresholds(m, MetricThresholds(max_p95_latency_ms=8000))
    assert any(a["metric"] == "p95_latency" for a in alerts)


def test_error_rate_alert_is_critical():
    m = _metrics(run_count=100, error_count=20)
    alerts = check_thresholds(m, MetricThresholds())
    err = [a for a in alerts if a["metric"] == "error_rate"]
    assert err and err[0]["severity"] == "CRITICAL"


def test_cost_alert():
    m = _metrics(run_count=100, estimated_cost_usd=25.0)
    alerts = check_thresholds(m, MetricThresholds(max_hourly_cost_usd=10.0))
    assert any(a["metric"] == "hourly_cost" for a in alerts)


# ── Evaluators ───────────────────────────────────────────────────────

def test_exact_match():
    assert exact_match("Yes", "yes") == 1.0
    assert exact_match("no", "yes") == 0.0


def test_contains_reference():
    assert contains_reference("The answer is 42 clearly", "42") == 1.0
    assert contains_reference("nothing here", "42") == 0.0


def test_keyword_recall():
    assert keyword_recall("alpha and gamma", ["alpha", "beta", "gamma", "delta"]) == 0.5
    assert keyword_recall("anything", []) == 1.0
