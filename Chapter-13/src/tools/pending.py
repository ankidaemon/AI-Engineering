"""
Actions waiting for the customer's yes (§6.6, §8.16).

When a high-impact action needs confirmation, the tool and the arguments the
model chose are held here, one per customer. When the customer says yes, the
action agent runs exactly what is held, with no second model call. That saves
a call on every confirmed action, and it makes certain the customer approved
the same action that then runs, not a fresh decision that might differ.

Held actions expire, so a yes that arrives much later is treated as a new
request and asked about again. Backed by Redis in production, so any API
instance can pick up a yes; an in-process dict when no client is given.
"""
import json
import time


class PendingActions:
    def __init__(self, redis_client=None, ttl_seconds: int = 300):
        self._redis = redis_client
        self._ttl = ttl_seconds
        self._local: dict = {}

    def hold(self, customer_id: str, tool: str, fields: dict) -> None:
        value = json.dumps({"tool": tool, "fields": fields})
        if self._redis is not None:
            self._redis.set(self._key(customer_id), value, ex=self._ttl)
        else:
            self._local[customer_id] = (time.time() + self._ttl, value)

    def take(self, customer_id: str):
        """(tool, fields) and forget it, or None if nothing is waiting.
        Taking removes it, so one yes runs one action."""
        if self._redis is not None:
            key = self._key(customer_id)
            pipe = self._redis.pipeline()
            pipe.get(key)
            pipe.delete(key)
            value, _ = pipe.execute()
        else:
            expires, value = self._local.pop(customer_id, (0, None))
            if time.time() > expires:
                value = None
        if value is None:
            return None
        held = json.loads(value)
        return held["tool"], held["fields"]

    @staticmethod
    def _key(customer_id: str) -> str:
        return f"pending:{customer_id}"
