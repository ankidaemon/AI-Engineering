import json
import time
import hashlib
import asyncio
import logging
import redis.asyncio as aioredis
from src.config import settings

logger = logging.getLogger(__name__)


class RedisCache:
    """
    Async Redis client managing three distinct concerns:

    Role 1 — Query Result Cache
        Keys:   qcache:{sha256(normalized_query)}
        TTL:    REDIS_CACHE_TTL (default: 3600s)
        Purpose: Avoid re-running full RAG pipeline for repeated queries.
                 Delivers significant cost and latency savings since
                 Llama 3.1 70B inference at ~5 tokens/sec is expensive.

    Role 2 — Conversation Session Store
        Keys:   session:{session_id}
        TTL:    REDIS_SESSION_TTL (default: 86400s)
        Purpose: Multi-turn conversation support. Stores the last N
                 conversation turns per user session.

    Role 3 — Rate Limiter
        Keys:   ratelimit:{ip}:{unix_minute_bucket}
        TTL:    120s (2 minutes, covering the sliding window)
        Purpose: Per-IP request rate limiting to prevent inference budget
                 exhaustion from a single client.

    All operations are designed to fail open: if Redis is unavailable,
    the main RAG pipeline continues without caching. This prevents a
    Redis outage from taking down the entire service.
    """

    def __init__(self):
        self._pool = aioredis.ConnectionPool.from_url(
            settings.redis_url,
            max_connections=25,
            decode_responses=True,
            socket_connect_timeout=2.0,
            socket_timeout=2.0
        )
        self._r = aioredis.Redis(connection_pool=self._pool)

    # ── Role 1: Query Cache ───────────────────────────────────────

    def _cache_key(self, query: str) -> str:
        normalized = query.strip().lower()
        return "qcache:" + hashlib.sha256(normalized.encode()).hexdigest()

    async def get_cached(self, query: str) -> dict | None:
        try:
            raw = await self._r.get(self._cache_key(query))
            if raw:
                logger.debug("Cache HIT")
                return json.loads(raw)
        except Exception as exc:
            logger.warning(f"Cache read error (failing open): {exc}")
        return None

    async def set_cached(
        self,
        query: str,
        payload: dict,
        ttl: int | None = None
    ):
        try:
            await self._r.setex(
                self._cache_key(query),
                ttl or settings.redis_cache_ttl,
                json.dumps(payload, default=str)
            )
        except Exception as exc:
            logger.warning(f"Cache write error (failing open): {exc}")

    async def invalidate_all_query_cache(self) -> int:
        try:
            keys = await self._r.keys("qcache:*")
            return await self._r.delete(*keys) if keys else 0
        except Exception:
            return 0

    # ── Role 2: Session Store ─────────────────────────────────────

    async def get_session(self, session_id: str) -> dict:
        try:
            raw = await self._r.get(f"session:{session_id}")
            if raw:
                return json.loads(raw)
        except Exception as exc:
            logger.warning(f"Session read error: {exc}")
        return {"turns": [], "created_at": time.time()}

    async def append_turn(
        self,
        session_id: str,
        role: str,        # "user" or "assistant"
        content: str,
        max_turns: int = 20
    ):
        try:
            session = await self.get_session(session_id)
            session["turns"].append({
                "role":      role,
                "content":   content,
                "timestamp": time.time()
            })
            # Keep only the most recent turns to bound memory usage
            session["turns"] = session["turns"][-max_turns:]
            await self._r.setex(
                f"session:{session_id}",
                settings.redis_session_ttl,
                json.dumps(session)
            )
        except Exception as exc:
            logger.warning(f"Session write error: {exc}")

    def format_history_for_prompt(
        self,
        session: dict,
        max_turns: int = 6
    ) -> str:
        """
        Formats the most recent conversation turns as a readable block
        for injection into the generation prompt. We cap at max_turns
        to avoid history dominating the context window.
        """
        turns = session.get("turns", [])[-max_turns:]
        lines = []
        for turn in turns:
            role = "User" if turn["role"] == "user" else "Assistant"
            # Truncate long turns to prevent history from consuming
            # too much of the 128K context window
            lines.append(f"{role}: {turn['content'][:600]}")
        return "\n".join(lines)

    # ── Role 3: Rate Limiter ──────────────────────────────────────

    async def check_rate_limit(
        self,
        identifier: str,
        limit: int | None = None
    ) -> tuple[bool, int]:
        """
        Sliding window rate limit using 1-minute buckets.
        Returns (is_allowed, requests_remaining).
        Fails open: returns (True, limit) if Redis is unreachable.
        """
        rpm = limit or settings.redis_rate_limit_rpm
        bucket = int(time.time() // 60)
        key = f"ratelimit:{identifier}:{bucket}"

        try:
            count = await self._r.incr(key)
            if count == 1:
                # Set expiry on first increment; covers the current minute
                # plus one more to handle clock skew
                await self._r.expire(key, 120)
            remaining = max(0, rpm - int(count))
            return int(count) <= rpm, remaining
        except Exception as exc:
            logger.warning(f"Rate limit check failed (failing open): {exc}")
            return True, rpm

    # ── Health / Lifecycle ────────────────────────────────────────

    async def ping(self) -> bool:
        try:
            return await self._r.ping()
        except Exception:
            return False

    async def close(self):
        await self._r.aclose()
