"""Cost control: estimation, budget caps, throttling, and resilient calls."""
import asyncio
import pytest

from src.cost.estimator import count_tokens, estimate_request_cost, project_monthly_cost
from src.cost.budget import BudgetGuard, BudgetExceeded
from src.cost.throttle import TokenBucket, Throttle, default_burst
from src.cost.resilient_call import with_backoff, generate_with_fallback


# ── Estimation ───────────────────────────────────────────────────────

def test_count_tokens_is_positive():
    assert count_tokens("hello world, this is a prompt") > 0


def test_self_hosted_model_is_free():
    est = estimate_request_cost("a" * 1000, model="llama3.1:8b")
    assert est.cost_usd == 0.0
    assert est.input_tokens > 0


def test_hosted_cost_scales_with_output():
    cheap = estimate_request_cost("word " * 100, model="gpt-4o-mini", projected_output_tokens=100)
    dear = estimate_request_cost("word " * 100, model="gpt-4o", projected_output_tokens=100)
    assert dear.cost_usd > cheap.cost_usd > 0


def test_monthly_projection_multiplies_out():
    monthly = project_monthly_cost(1000, "some average prompt", model="gpt-4o-mini")
    per = estimate_request_cost("some average prompt", model="gpt-4o-mini").cost_usd
    assert monthly == pytest.approx(per * 1000 * 30, rel=1e-6)


# ── Budget ───────────────────────────────────────────────────────────

def test_budget_allows_within_cap():
    guard = BudgetGuard(hourly_cap_usd=1.00)
    guard.check_and_reserve(0.40, key="user-1")
    guard.check_and_reserve(0.40, key="user-1")
    assert guard.current_spend("user-1") == pytest.approx(0.80)


def test_budget_rejects_over_cap():
    guard = BudgetGuard(hourly_cap_usd=1.00)
    guard.check_and_reserve(0.80, key="user-1")
    with pytest.raises(BudgetExceeded):
        guard.check_and_reserve(0.50, key="user-1")


def test_budget_is_per_key():
    guard = BudgetGuard(hourly_cap_usd=1.00)
    guard.check_and_reserve(0.90, key="heavy")
    guard.check_and_reserve(0.90, key="light")  # different key has its own headroom
    assert guard.current_spend("light") == pytest.approx(0.90)


def test_settle_corrects_reservation():
    guard = BudgetGuard(hourly_cap_usd=10.0)
    guard.check_and_reserve(1.00, key="u")
    guard.settle(1.00, 0.25, key="u")           # real cost was lower
    assert guard.current_spend("u") == pytest.approx(0.25)


# ── Throttle ─────────────────────────────────────────────────────────

async def _noop():
    return None


async def test_token_bucket_limits_rate():
    bucket = TokenBucket(rate_per_minute=60, burst=2)  # 1/sec, burst of 2
    start = asyncio.get_event_loop().time()
    for _ in range(4):
        await bucket.acquire()
    elapsed = asyncio.get_event_loop().time() - start
    # 2 free from the burst, then ~1s each for the next two.
    assert elapsed >= 1.5


@pytest.mark.parametrize("rate,expected", [
    (60, 6), (600, 60), (10, 1), (5, 1), (1, 1),
])
def test_default_burst_is_a_tenth_of_the_minute(rate, expected):
    """Never zero, or the bucket would start empty and stall the first call."""
    assert default_burst(rate) == expected


def test_default_burst_keeps_the_first_window_near_the_nominal_rate():
    """
    The worst case is `burst + rate_per_minute` calls in the first rolling
    window. `burst == rate_per_minute` makes that 2x the limit, which is a 429
    on the first request after an idle period.
    """
    rate = 600
    assert default_burst(rate) + rate <= rate * 1.1
    naive_burst = rate                      # what the bare TokenBucket defaults to
    assert naive_burst + rate == rate * 2


async def test_throttle_uses_the_conservative_burst_by_default():
    throttle = Throttle(rate_per_minute=60, max_concurrent=10)
    assert throttle._bucket._capacity == default_burst(60)


async def test_throttle_burst_can_be_raised_for_providers_that_tolerate_spikes():
    throttle = Throttle(rate_per_minute=60, max_concurrent=10, burst=30)
    start = asyncio.get_event_loop().time()
    await asyncio.gather(*[throttle.run(_noop) for _ in range(30)])
    # all 30 come out of the burst, so none of them waits on the refill
    assert asyncio.get_event_loop().time() - start < 0.5


async def test_a_burst_of_one_spaces_calls_evenly():
    throttle = Throttle(rate_per_minute=600, max_concurrent=10, burst=1)
    start = asyncio.get_event_loop().time()
    await asyncio.gather(*[throttle.run(_noop) for _ in range(4)])
    # 1 free, then 3 at 0.1s each
    assert asyncio.get_event_loop().time() - start >= 0.25


async def test_throttle_bounds_concurrency():
    throttle = Throttle(rate_per_minute=6000, max_concurrent=2)
    active = 0
    peak = 0

    async def job():
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        await asyncio.sleep(0.05)
        active -= 1

    await asyncio.gather(*[throttle.run(job) for _ in range(6)])
    assert peak <= 2


# ── Resilient calls ──────────────────────────────────────────────────

async def test_backoff_retries_then_succeeds():
    calls = {"n": 0}

    async def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise ConnectionError("boom")
        return "ok"

    assert await with_backoff(flaky, base=0.001) == "ok"
    assert calls["n"] == 3


async def test_backoff_does_not_retry_non_retryable():
    async def bad():
        raise ValueError("permanent")

    with pytest.raises(ValueError):
        await with_backoff(bad, base=0.001)


async def test_fallback_chain_uses_next_backend():
    async def primary():
        raise ConnectionError("down")

    async def secondary():
        return "from-secondary"

    result = await generate_with_fallback([primary, secondary])
    assert result == "from-secondary"
