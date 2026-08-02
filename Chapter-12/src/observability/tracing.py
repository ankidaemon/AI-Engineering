"""
Observability helpers built on LangSmith.

`traced` marks any plain function so its inputs, outputs and errors show up in
LangSmith next to your LangChain calls. `CostTracker` turns the token counts a
trace reports into a running cost. `log_user_feedback` attaches a thumbs up or
down to a specific run so you can measure real quality over time.

The LangSmith client is injected, so tests pass a fake and nothing phones home.
"""
import functools
import logging
import time
from typing import Callable, Optional

logger = logging.getLogger(__name__)


def traced(name: Optional[str] = None, tags: Optional[list] = None) -> Callable:
    """
    Decorator that traces a function through LangSmith when tracing is enabled.
    If the `langsmith` package or the `traceable` wrapper is unavailable, the
    function runs unchanged, so this is always safe to leave in the code.
    """
    def decorator(fn: Callable) -> Callable:
        try:
            from langsmith import traceable
            return traceable(name=name or fn.__name__, tags=tags or [])(fn)
        except Exception:
            @functools.wraps(fn)
            def passthrough(*args, **kwargs):
                return fn(*args, **kwargs)
            return passthrough

    return decorator


class CostTracker:
    """
    Turns token counts into a running cost. LangSmith captures token counts
    automatically; this class multiplies them by a price table and keeps a
    session total you can log or expose on a metrics route.
    """

    # Prices per one million tokens. Self-hosted models are free per token.
    PRICING = {
        "llama3.1:8b": {"input": 0.00, "output": 0.00},
        "llama3.1:70b": {"input": 0.00, "output": 0.00},
        "gpt-4o": {"input": 5.00, "output": 15.00},
        "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    }

    def __init__(self):
        self._session_cost = 0.0
        self._session_tokens = {"input": 0, "output": 0}

    def estimate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        pricing = self.PRICING.get(model, {"input": 0.0, "output": 0.0})
        cost = (
            (input_tokens / 1_000_000) * pricing["input"]
            + (output_tokens / 1_000_000) * pricing["output"]
        )
        self._session_cost += cost
        self._session_tokens["input"] += input_tokens
        self._session_tokens["output"] += output_tokens
        return cost

    def session_summary(self) -> dict:
        return {
            "total_cost_usd": round(self._session_cost, 6),
            "total_input_tokens": self._session_tokens["input"],
            "total_output_tokens": self._session_tokens["output"],
        }

    def reset(self) -> None:
        self._session_cost = 0.0
        self._session_tokens = {"input": 0, "output": 0}


def log_user_feedback(run_id: str, score: float, comment: str = "", client=None) -> bool:
    """
    Record a user's rating of a run in LangSmith. Pass a client in tests; in
    production it builds a real `langsmith.Client`. Returns True on success and
    never raises, because losing a feedback event must not break a request.
    """
    try:
        if client is None:
            from langsmith import Client
            client = Client()
        client.create_feedback(
            run_id=run_id,
            key="user_score",
            score=score,
            comment=comment,
        )
        return True
    except Exception as exc:
        logger.warning("Failed to log feedback for run %s: %s", run_id, exc)
        return False


def timed(fn: Callable) -> Callable:
    """Small helper: log how long a function took, in milliseconds."""
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        start = time.time()
        try:
            return fn(*args, **kwargs)
        finally:
            logger.info("%s took %d ms", fn.__name__, int((time.time() - start) * 1000))

    return wrapper
