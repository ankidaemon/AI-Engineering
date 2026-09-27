"""The retrieval router: nearest exemplar, fail toward the harmless path
(§3.3, §8.7). No model anywhere in these tests — routing is vector search."""
from src.router import ROUTE_EXEMPLARS, ROUTES, Router


def test_default_exemplars_cover_every_route():
    assert set(ROUTE_EXEMPLARS) == set(ROUTES)
    assert all(len(utts) >= 3 for utts in ROUTE_EXEMPLARS.values())


def test_clear_messages_route_correctly(embeddings):
    router = Router(embeddings)
    assert router.route("what is the late fee on my card") == "question"
    assert router.route("which card is best for someone who travels") == "advice"
    assert router.route("please block my card right now") == "action"
    assert router.route("order me a new cheque book for my account") == "action"


def test_gibberish_falls_back_to_question(embeddings):
    """A message resembling no exemplar must never reach the action agent."""
    router = Router(embeddings)
    assert router.route("qwerty zzz flurble") == "question"


def test_a_close_call_between_routes_falls_back_to_question(embeddings):
    # Custom exemplars engineered to tie: the message overlaps both routes
    # equally, so the margin rule demotes to the harmless path.
    router = Router(embeddings, exemplars={
        "question": ["what are the branch opening hours"],
        "advice": ["good credit card"],
        "action": ["block credit card"],
    })
    assert router.route("credit card") == "question"


def test_a_clear_margin_is_respected(embeddings):
    router = Router(embeddings, exemplars={
        "question": ["what are the branch opening hours"],
        "advice": ["which savings account should I choose"],
        "action": ["freeze my debit card immediately"],
    })
    assert router.route("freeze my debit card") == "action"


def test_thresholds_are_tunable(embeddings):
    # A paraphrase that clears the default floor fails a strict one: the
    # same message routes differently as the threshold moves.
    relaxed = Router(embeddings, min_score=0.2)
    strict = Router(embeddings, min_score=0.99)
    assert relaxed.route("stop my card") == "action"
    assert strict.route("stop my card") == "question"
