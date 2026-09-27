"""The semantic cache and its boundary (§7.4)."""
from src.cache.semantic_cache import MemoryBackend, RedisBackend, SemanticCache


def _cache(embeddings, **kwargs):
    kwargs.setdefault("threshold", 0.95)
    return SemanticCache(embeddings, **kwargs)


def test_same_meaning_wording_hits(embeddings):
    cache = _cache(embeddings)
    assert cache.put("what is the interest free period",
                     "Up to 45 days.") is True
    # same words, different order — same meaning to the embedder
    assert cache.get("the interest free period is what") == "Up to 45 days."


def test_a_different_question_misses(embeddings):
    cache = _cache(embeddings)
    cache.put("what is the interest free period", "Up to 45 days.")
    assert cache.get("how do I order a cheque book for my account") is None


def test_expired_entries_are_not_served(embeddings):
    now = [1000.0]
    cache = _cache(embeddings, ttl_seconds=60, clock=lambda: now[0])
    cache.put("what is the late fee", "25.00")
    assert cache.get("what is the late fee") == "25.00"
    now[0] += 61
    assert cache.get("what is the late fee") is None


def test_customer_specific_answers_are_refused(embeddings):
    """The boundary lives in the cache, not in callers' good intentions."""
    cache = _cache(embeddings)
    assert cache.put("what is my balance", "Your balance is 4,210.55",
                     customer_id="c1") is False
    assert cache.get("what is my balance") is None


def test_write_results_are_refused(embeddings):
    cache = _cache(embeddings)
    assert cache.put("block my card", "Done, reference BLK-000001",
                     kind="action") is False
    assert cache.get("block my card") is None


def test_redis_backend_shares_entries(embeddings, fake_redis):
    writer = _cache(embeddings, backend=RedisBackend(fake_redis))
    writer.put("what is the late fee", "25.00")
    # a second instance sharing the same Redis sees the entry
    reader = _cache(embeddings, backend=RedisBackend(fake_redis))
    assert reader.get("what is the late fee") == "25.00"


def test_memory_backend_roundtrip():
    backend = MemoryBackend()
    backend.append({"a": 1})
    assert backend.all() == [{"a": 1}]
