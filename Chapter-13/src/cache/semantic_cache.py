"""
The semantic cache, with its boundary enforced in code (§7.4).

Many customers ask the same handful of questions. The cache is keyed by the
MEANING of the question, not its exact wording, so "what is the interest
free period" and "how long before interest kicks in" can share one cached
answer: store the embedding with the answer, and a lookup is a similarity
check against stored entries.

The boundary is the serious part in banking, so it lives HERE, not in the
callers' good intentions: only general knowledge answers, tied to no
customer, are accepted. Anything customer-specific must never be cached and
served to someone else, and the result of a write action must never be
cached at all — the next customer's request is a different request even if
it reads the same. `put` refuses both, quietly returning False.

Storage is a small injected backend: in-memory for tests and single-node
runs, Redis-backed so instances share the cache in production.
"""
import json
import time

from src.vectorstores.cosine_index import cosine


class MemoryBackend:
    def __init__(self):
        self._entries = []

    def append(self, entry: dict):
        self._entries.append(entry)

    def all(self) -> list:
        return list(self._entries)


class RedisBackend:
    """Entries as JSON in one Redis list, shared by every instance."""

    KEY = "semantic_cache:entries"

    def __init__(self, redis_client):
        self._redis = redis_client

    def append(self, entry: dict):
        self._redis.rpush(self.KEY, json.dumps(entry))

    def all(self) -> list:
        raw = self._redis.lrange(self.KEY, 0, -1)
        return [json.loads(item) for item in raw]


class SemanticCache:
    def __init__(self, embeddings, backend=None, threshold: float = 0.92,
                 ttl_seconds: int = 3600, clock=time.time):
        self._embeddings = embeddings
        self._backend = backend or MemoryBackend()
        self._threshold = threshold
        self._ttl = ttl_seconds
        self._clock = clock

    def put(self, question: str, answer: str, kind: str = "knowledge",
            customer_id: str = None) -> bool:
        """Accepts only general knowledge answers. Refuses anything
        customer-specific and anything that came from a write action."""
        if kind != "knowledge" or customer_id is not None:
            return False
        self._backend.append({
            "vector": self._embeddings.embed_query(question),
            "question": question,
            "answer": answer,
            "expires": self._clock() + self._ttl,
        })
        return True

    def get(self, question: str):
        """The stored answer whose question means the same thing, or None."""
        entries = self._backend.all()
        if not entries:
            return None
        now = self._clock()
        query_vec = self._embeddings.embed_query(question)
        best, best_score = None, 0.0
        for entry in entries:
            if entry["expires"] < now:
                continue
            score = cosine(query_vec, entry["vector"])
            if score > best_score:
                best, best_score = entry, score
        if best is not None and best_score >= self._threshold:
            return best["answer"]
        return None
