"""
Never doing the same thing twice (§6.5, Failure 3).

Customers double tap, networks retry, and conversations circle back. Any of
these can turn one intended complaint into two. The defense is idempotency:
each write carries a key derived from what the customer actually asked for,
and the system remembers the keys it has already acted on. A repeat returns
the ORIGINAL reference instead of acting again — the customer gets the same
ticket number they got the first time, which is exactly right, because there
was only ever one request.

The store is backed by Redis (already present as broker and cache, §7.2) via
an injected client, so tests run on fakeredis and production shares state
across instances.
"""
import hashlib
import json


def derive_key(action: str, fields: dict) -> str:
    """Stable key from the action and its meaningful fields. Same request,
    same key — regardless of field order or retry."""
    canonical = json.dumps({"action": action, "fields": fields},
                           sort_keys=True, separators=(",", ":"))
    return "idem:" + hashlib.sha256(canonical.encode()).hexdigest()


class IdempotencyStore:
    def __init__(self, redis_client, ttl_seconds: int = 24 * 3600):
        self._redis = redis_client
        self._ttl = ttl_seconds

    def recall(self, key: str):
        """The original result if this key was already acted on, else None."""
        value = self._redis.get(key)
        if value is None:
            return None
        return value.decode() if isinstance(value, bytes) else value

    def remember(self, key: str, reference: str):
        self._redis.set(key, reference, ex=self._ttl)
