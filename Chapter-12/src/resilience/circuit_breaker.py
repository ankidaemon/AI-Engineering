"""
A circuit breaker for calls to external services (the LLM, the vector store,
FireCrawl). When a service starts failing, the breaker trips and rejects calls
for a while instead of letting every request pile up behind slow timeouts. That
stops one failing dependency from dragging down the whole application.
"""
import time
import logging
from enum import Enum
from dataclasses import dataclass, field
from typing import Callable, Optional, TypeVar

logger = logging.getLogger(__name__)
T = TypeVar("T")


class CircuitState(Enum):
    CLOSED = "closed"        # normal, calls pass through
    OPEN = "open"            # tripped, calls are rejected immediately
    HALF_OPEN = "half_open"  # testing recovery, a few calls allowed through


@dataclass
class CircuitBreaker:
    """
    States:
      CLOSED    normal operation, failures are counted.
      OPEN      too many failures, calls fail fast until the recovery timeout.
      HALF_OPEN one test call is allowed; success closes the circuit, failure
                opens it again.
    """
    name: str
    failure_threshold: int = 5
    recovery_timeout: float = 60.0
    success_threshold: int = 2

    _state: CircuitState = field(default=CircuitState.CLOSED, init=False)
    _failure_count: int = field(default=0, init=False)
    _success_count: int = field(default=0, init=False)
    _last_failure: float = field(default=0.0, init=False)

    @property
    def state(self) -> CircuitState:
        return self._state

    @property
    def is_available(self) -> bool:
        return self._state != CircuitState.OPEN

    def call(self, fn: Callable[[], T], fallback: Optional[Callable[[], T]] = None) -> T:
        if self._state == CircuitState.OPEN:
            if time.time() - self._last_failure > self.recovery_timeout:
                logger.info("Circuit '%s': OPEN to HALF_OPEN (testing recovery)", self.name)
                self._state = CircuitState.HALF_OPEN
                self._success_count = 0
            elif fallback is not None:
                logger.warning("Circuit '%s' is OPEN, using fallback", self.name)
                return fallback()
            else:
                raise RuntimeError(f"Circuit '{self.name}' is OPEN, service unavailable")

        try:
            result = fn()
            self._on_success()
            return result
        except Exception as exc:
            self._on_failure()
            if fallback is not None:
                logger.warning("Circuit '%s' failure, using fallback: %s", self.name, exc)
                return fallback()
            raise

    def _on_success(self) -> None:
        self._failure_count = 0
        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self.success_threshold:
                logger.info("Circuit '%s': HALF_OPEN to CLOSED", self.name)
                self._state = CircuitState.CLOSED

    def _on_failure(self) -> None:
        self._last_failure = time.time()
        self._failure_count += 1
        if self._state == CircuitState.HALF_OPEN:
            logger.warning("Circuit '%s': HALF_OPEN to OPEN (test failed)", self.name)
            self._state = CircuitState.OPEN
        elif self._failure_count >= self.failure_threshold:
            logger.error(
                "Circuit '%s': CLOSED to OPEN (%d consecutive failures)",
                self.name, self._failure_count,
            )
            self._state = CircuitState.OPEN
