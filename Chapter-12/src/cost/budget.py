"""
A hard spend cap over a rolling time window.

Alerting tells a human that spend is high. A budget guard refuses to spend more
without asking anyone. In production you want the guard, because alerts fire at
three in the morning and a runaway loop does not wait for someone to read Slack.

The counter is kept in memory here, which is right for a single process and for
tests. In a multi process or multi pod deployment, store it in Redis so the cap
holds across the whole fleet, exactly as Chapter 11 did for FAISS.
"""
import time
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


class BudgetExceeded(Exception):
    """Raised when a request would push spend over the configured cap."""


@dataclass
class BudgetGuard:
    """
    Enforces a spend cap per key over a rolling window.

    Call `check_and_reserve` before the LLM call with the estimated cost. If the
    reservation would breach the cap it raises, and the call never happens. Call
    `settle` after the call with the true cost to correct the reservation.

    A per key budget (per user or per tenant) stops one caller from consuming
    everyone else's headroom.
    """
    hourly_cap_usd: float = 10.00
    window_seconds: int = 3600
    _spend: dict = field(default_factory=dict, init=False)  # key -> [(ts, usd)]

    def _current(self, key: str) -> float:
        cutoff = time.time() - self.window_seconds
        entries = [(ts, usd) for ts, usd in self._spend.get(key, []) if ts >= cutoff]
        self._spend[key] = entries  # prune as we read
        return sum(usd for _, usd in entries)

    def current_spend(self, key: str = "global") -> float:
        return round(self._current(key), 6)

    def check_and_reserve(self, estimated_usd: float, key: str = "global") -> None:
        spent = self._current(key)
        if spent + estimated_usd > self.hourly_cap_usd:
            logger.error(
                "Budget cap hit for '%s': $%.4f spent + $%.4f requested > $%.2f cap",
                key, spent, estimated_usd, self.hourly_cap_usd,
            )
            raise BudgetExceeded(
                f"Hourly budget ${self.hourly_cap_usd:.2f} would be exceeded for '{key}'"
            )
        self._spend.setdefault(key, []).append((time.time(), estimated_usd))

    def settle(self, estimated_usd: float, actual_usd: float, key: str = "global") -> None:
        """Record the difference between the reservation and the true cost."""
        self._spend.setdefault(key, []).append((time.time(), actual_usd - estimated_usd))
