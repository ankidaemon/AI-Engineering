"""
Traffic shaping for LLM calls.

A budget caps money. Throttling caps rate. You want both, because they stop two
different problems: a runaway loop that spends fast, and a provider rate limit
that returns 429 errors when you send too many requests per minute.

`TokenBucket` smooths bursts to a steady rate. `Throttle` adds a hard ceiling on
how many calls can be in flight at once.

One warning about the name, because this is a book about language models. The
tokens in this module are **permits to make a request**. They have nothing to do
with the tokens `src/cost/estimator.py` counts, which are units of model text.
`TokenBucket` is the standard name for this algorithm so it stays, but every
argument and counter below says `permits`, and one permit buys one API call
regardless of how many model tokens that call goes on to spend.
"""
import asyncio
import time
import logging

logger = logging.getLogger(__name__)


class TokenBucket:
    """
    An async token bucket. The bucket refills at a steady rate and every call
    spends one permit. When the bucket is empty, callers wait until it refills,
    which keeps you under a provider's requests per minute ceiling.

    Two dials, and they do different jobs. `rate_per_minute` is the long run
    average. `burst` is how many permits may pile up while nobody is spending,
    which is how many calls may go out back to back after an idle period.

    Burst is not free. A bucket that starts full admits `burst` calls instantly
    and then `rate_per_minute` more over the following minute, so the first
    window can carry `burst + rate_per_minute` calls. Against a provider
    enforcing a rolling window, that is the moment you get a 429. This class
    keeps the textbook default of `burst == rate_per_minute` because it is the
    primitive; `Throttle` is the one you point at a real provider, and it picks
    a conservative burst instead.
    """

    def __init__(self, rate_per_minute: int = 60, burst: int | None = None):
        self._rate = rate_per_minute / 60.0          # permits per second
        self._capacity = burst or rate_per_minute    # largest allowed burst
        self._permits = float(self._capacity)
        self._updated = time.monotonic()
        self._lock = asyncio.Lock()

    def _refill(self) -> None:
        now = time.monotonic()
        self._permits = min(self._capacity, self._permits + (now - self._updated) * self._rate)
        self._updated = now

    async def acquire(self, permits: int = 1) -> None:
        async with self._lock:
            while True:
                self._refill()
                if self._permits >= permits:
                    self._permits -= permits
                    return
                wait = (permits - self._permits) / self._rate
                logger.debug("Rate limit reached, waiting %.2fs", wait)
                await asyncio.sleep(wait)


def default_burst(rate_per_minute: int) -> int:
    """
    A tenth of the minute's allowance, at least one.

    The worst case for any burst `b` is `b + rate_per_minute` calls in the first
    rolling window, so a tenth keeps the overshoot near 10% instead of the 100%
    you get from `burst == rate_per_minute`. Raise it if your provider measures
    in fixed windows or you know it tolerates spikes; lower it to 1 for perfectly
    even spacing and no overshoot at all.
    """
    return max(1, rate_per_minute // 10)


class Throttle:
    """
    Combines a request rate limit with a hard concurrency ceiling.

    The two limits are not redundant, because the bucket controls how often
    calls *start* and the semaphore controls how many are *running*. In flight
    work is roughly rate times duration, so the same 60 per minute sits at two
    concurrent calls when the provider answers in two seconds and at sixty when
    it slows to a minute. The bucket cannot see that; only the ceiling can.
    """

    def __init__(self, rate_per_minute: int = 60, max_concurrent: int = 10,
                 burst: int | None = None):
        self._bucket = TokenBucket(
            rate_per_minute, burst if burst is not None else default_burst(rate_per_minute)
        )
        self._sem = asyncio.Semaphore(max_concurrent)

    async def run(self, coro_factory):
        """`coro_factory` is a zero argument callable that returns a coroutine."""
        # Rate gate first. Reversed, a caller would hold a concurrency slot
        # while sleeping out its bucket wait, and the ceiling would throttle
        # admission instead of execution.
        await self._bucket.acquire()   # shape the rate
        async with self._sem:          # bound the in flight calls
            return await coro_factory()
