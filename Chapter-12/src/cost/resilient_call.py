"""
Staying up when the model provider does not.

Three layers, applied in order:
  1. retry the transient failures, carefully, with backoff and jitter;
  2. fall back to another model when the primary is down;
  3. degrade to a cached or canned answer so the user never sees a 500.
"""
import asyncio
import random
import logging

logger = logging.getLogger(__name__)

# Extend with your client's timeout / rate limit exception types.
RETRYABLE = (TimeoutError, ConnectionError)


async def with_backoff(coro_factory, *, max_attempts: int = 3, base: float = 0.5):
    """
    Retry transient failures with exponential backoff and full jitter. Only
    retryable errors are retried; a bad request or a budget rejection is raised
    immediately so you do not pay to repeat a call that can never succeed.
    """
    for attempt in range(1, max_attempts + 1):
        try:
            return await coro_factory()
        except RETRYABLE as exc:
            if attempt == max_attempts:
                logger.error("Giving up after %d attempts: %s", attempt, exc)
                raise
            delay = base * (2 ** (attempt - 1)) + random.uniform(0, base)
            logger.warning("Attempt %d failed (%s), retrying in %.2fs", attempt, exc, delay)
            await asyncio.sleep(delay)


async def generate_with_fallback(backends):
    """
    Try each backend in order until one succeeds. `backends` is a list of zero
    argument callables that return coroutines, ordered by preference. The last
    one should always succeed (a cached or canned response), so a provider
    outage still returns something useful instead of an error.
    """
    last_exc = None
    for backend in backends:
        try:
            return await with_backoff(backend)
        except Exception as exc:
            last_exc = exc
            logger.warning("Backend failed, falling through: %s", exc)
    raise RuntimeError(f"All backends failed; last error: {last_exc}")
