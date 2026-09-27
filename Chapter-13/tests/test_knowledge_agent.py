"""The grounded knowledge agent: answers, cites, declines (§4.4)."""
from src.knowledge.agent import (HANDOFF_MESSAGE, KnowledgeService, answer,
                                 best_score)
from src.vectorstores.faiss_store import RetrievedPassage
from tests.conftest import FakeModel


def _passage(text, relevance, source="faq.json"):
    return RetrievedPassage(text=text, metadata={"source": source},
                            relevance=relevance)


def test_the_decline_threshold_comes_from_config_when_not_given(monkeypatch):
    """MIN_RELEVANCE in .env used to be dead: the agent read a module constant
    instead. A reader who raises it should see the agent decline sooner."""
    from src.config import settings
    from src.knowledge.agent import DEFAULT_MIN_RELEVANCE, answer
    from src.vectorstores.faiss_store import RetrievedPassage

    passage = RetrievedPassage("the late fee is 500", {"source": "fees.csv"},
                               relevance=0.30)
    assert passage.relevance > DEFAULT_MIN_RELEVANCE      # answerable by default

    monkeypatch.setattr(settings, "min_relevance", 0.50)
    assert answer("what is the late fee", [passage]).handed_off

    monkeypatch.setattr(settings, "min_relevance", 0.10)
    assert answer("what is the late fee", [passage],
                  model=FakeModel(reply="It is 500.")).handed_off is False


def test_an_explicit_threshold_wins_over_config(monkeypatch):
    from src.config import settings
    from src.knowledge.agent import answer
    from src.vectorstores.faiss_store import RetrievedPassage

    monkeypatch.setattr(settings, "min_relevance", 0.10)
    passage = RetrievedPassage("thin match", {"source": "x"}, relevance=0.20)
    assert answer("q", [passage], min_relevance=0.90).handed_off


def test_declines_when_nothing_was_retrieved():
    result = answer("What is the moon made of?", [], model=FakeModel())
    assert result.handed_off is True
    assert result.text == HANDOFF_MESSAGE


def test_declines_when_retrieval_is_weak():
    weak = [_passage("Something barely related.", relevance=0.05)]
    model = FakeModel()
    result = answer("What is the late fee?", weak, model=model)
    assert result.handed_off is True
    assert model.prompts == []        # declining means no model call at all


def test_answers_from_context_and_cites_sources():
    retrieved = [
        _passage("The late payment fee is 25.00.", 0.9, source="fee-schedule.csv"),
        _passage("Fees change with 30 days notice.", 0.5, source="card-terms.md"),
    ]
    model = FakeModel(reply="The late payment fee is 25.00 [fee-schedule.csv].")
    result = answer("What is the late fee?", retrieved, model=model)

    assert result.handed_off is False
    assert result.sources == ["fee-schedule.csv", "card-terms.md"]
    prompt = model.prompts[0]
    assert "The late payment fee is 25.00.  [fee-schedule.csv]" in prompt
    assert "What is the late fee?" in prompt
    assert "only" in prompt           # the grounding instruction is present


def test_best_score_handles_empty():
    assert best_score([]) == 0.0


def test_service_wires_search_to_answer():
    class FakeIndex:
        def search(self, query, k):
            return [_passage("The cheque book fee is 3.00.", 0.8)]

    service = KnowledgeService(FakeIndex(), model=FakeModel(reply="It is 3.00."))
    result = service.ask("cheque book fee?")
    assert result.text == "It is 3.00."
    assert result.handed_off is False


# ── A non-answer is a decline (§8.16) ────────────────────────────────

def test_i_dont_know_becomes_a_handoff_so_it_is_never_cached():
    from src.knowledge.agent import answer
    from tests.conftest import FakeModel
    from src.vectorstores.faiss_store import RetrievedPassage
    passage = RetrievedPassage(text="Interest applies after the due date.",
                               metadata={"source": "card-terms.md"}, relevance=0.9)
    reply = answer("what is the interest free period?", [passage],
                   model=FakeModel(reply="I don't know. The passage only says..."),
                   min_relevance=0.25)
    assert reply.handed_off is True
    assert reply.sources == []


def test_is_non_answer_reads_only_the_start():
    from src.knowledge.agent import is_non_answer
    assert is_non_answer("I don’t know.")
    assert is_non_answer("  I do not know that.")
    assert not is_non_answer("Up to 45 days. I don't know about other cards.")
