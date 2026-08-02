"""Circuit breaker state transitions and fallback behaviour."""
import time
from src.resilience.circuit_breaker import CircuitBreaker, CircuitState


def _boom():
    raise RuntimeError("service down")


def test_passes_through_when_closed():
    cb = CircuitBreaker(name="t", failure_threshold=3)
    assert cb.call(lambda: 42) == 42
    assert cb.state == CircuitState.CLOSED


def test_opens_after_threshold_failures():
    cb = CircuitBreaker(name="t", failure_threshold=3)
    for _ in range(3):
        try:
            cb.call(_boom)
        except RuntimeError:
            pass
    assert cb.state == CircuitState.OPEN
    assert not cb.is_available


def test_open_circuit_uses_fallback():
    cb = CircuitBreaker(name="t", failure_threshold=1)
    try:
        cb.call(_boom)
    except RuntimeError:
        pass
    assert cb.state == CircuitState.OPEN
    assert cb.call(_boom, fallback=lambda: "cached") == "cached"


def test_recovers_through_half_open():
    cb = CircuitBreaker(name="t", failure_threshold=1, recovery_timeout=0.05, success_threshold=1)
    try:
        cb.call(_boom)
    except RuntimeError:
        pass
    assert cb.state == CircuitState.OPEN
    time.sleep(0.06)                      # wait out the recovery timeout
    assert cb.call(lambda: "ok") == "ok"  # HALF_OPEN test call succeeds
    assert cb.state == CircuitState.CLOSED
