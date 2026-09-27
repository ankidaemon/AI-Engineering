"""The assistant end to end, on fakes (§8), and the health summary (§8.11)."""
from src.api import summarize_health
from src.assistant import Assistant
from src.cache.semantic_cache import SemanticCache
from src.knowledge.agent import Answer
from src.products.advisor import Customer, Recommendation
from src.products.catalog import DEFAULT_CATALOG
from src.tools.base import ActionResult
from tests.conftest import FakeEmbeddings


class FakeRouter:
    def __init__(self, kind):
        self._kind = kind

    def route(self, message):
        return self._kind


class FakeKnowledge:
    def __init__(self):
        self.asked = []

    def ask(self, question):
        self.asked.append(question)
        return Answer(text="Up to 45 days.", sources=["card-faq.json"])


class FakeAdvisor:
    def recommend(self, need, customer, memories=()):
        self.seen = (need, customer, list(memories))
        return Recommendation(product=DEFAULT_CATALOG[3],   # travel-card
                              explanation="It fits your travel.")


class FakeActions:
    def handle(self, message, history, customer_id, confirmed=False):
        self.seen = (message, customer_id, confirmed)
        if not confirmed:
            return ActionResult(status="needs_confirmation",
                                message="Shall I go ahead?")
        return ActionResult(status="done", reference="BLK-000001",
                            message="Done. Your reference is BLK-000001.")


class FakeMemory:
    def __init__(self, facts=("travels abroad monthly",)):
        self.facts = list(facts)
        self.recalled = []
        self.remembered = []

    def recall(self, customer_id, query):
        self.recalled.append((customer_id, query))
        return self.facts

    def remember(self, customer_id, message, reply):
        self.remembered.append((customer_id, message, reply))


def _assistant(kind, cache=None, get_customer=None, memory=None, remember=None):
    return Assistant(FakeKnowledge(), FakeAdvisor(), FakeActions(),
                     router=FakeRouter(kind),
                     cache=cache, get_customer=get_customer,
                     memory=memory, remember=remember)


def test_question_routes_to_knowledge_with_sources():
    assistant = _assistant("question")
    reply = assistant.handle("c1", "what is the interest free period")
    assert reply.kind == "question"
    assert reply.text == "Up to 45 days."
    assert reply.sources == ["card-faq.json"]


def test_second_identical_question_comes_from_cache():
    cache = SemanticCache(FakeEmbeddings(), threshold=0.99)
    assistant = _assistant("question", cache=cache)
    first = assistant.handle("c1", "what is the interest free period")
    second = assistant.handle("c2", "what is the interest free period")
    assert first.from_cache is False
    assert second.from_cache is True
    assert second.text == first.text
    assert len(assistant._knowledge.asked) == 1     # retrieval ran once


def test_advice_routes_to_the_advisor_with_the_profile():
    customer = Customer("c1", income=60000, profile_notes="travels often")
    assistant = _assistant("advice", get_customer=lambda cid: customer)
    reply = assistant.handle("c1", "which card is best for me?")
    assert reply.kind == "advice"
    assert reply.reference == "travel-card"
    assert assistant._advisor.seen[1] is customer


def test_advice_recalls_this_customers_memories_for_the_advisor():
    """§8.8: recall happens on the request path (a vector search), scoped
    to the customer, and lands in the advisor's query."""
    memory = FakeMemory(facts=["travels abroad monthly"])
    assistant = _assistant("advice", memory=memory,
                           get_customer=lambda cid: Customer("c7"))
    assistant.handle("c7", "which card should I get?")
    assert memory.recalled == [("c7", "which card should I get?")]
    assert assistant._advisor.seen[2] == ["travels abroad monthly"]


def test_every_reply_leaves_through_the_remember_seam():
    """§8.8: production wires `remember` to a Celery task, so the seam is a
    callable — the assistant hands it the finished exchange."""
    queued = []
    assistant = _assistant("question",
                           remember=lambda cid, msg, text: queued.append((cid, msg, text)))
    assistant.handle("c1", "what is the interest free period")
    assert queued == [("c1", "what is the interest free period", "Up to 45 days.")]


def test_a_cache_hit_is_not_remembered_again():
    memory = FakeMemory()
    cache = SemanticCache(FakeEmbeddings(), threshold=0.99)
    assistant = _assistant("question", cache=cache, memory=memory)
    assistant.handle("c1", "what is the interest free period")
    assistant.handle("c2", "what is the interest free period")   # cache hit
    assert len(memory.remembered) == 1


def test_action_routes_and_carries_confirmation():
    assistant = _assistant("action")
    first = assistant.handle("c1", "block my card")
    assert first.needs_confirmation is True
    done = assistant.handle("c1", "block my card", confirmed=True)
    assert done.reference == "BLK-000001"
    assert done.needs_confirmation is False


def test_health_summary_never_lies():
    assert summarize_health({"model_server": True, "redis": True,
                             "workers": True}) == "healthy"
    assert summarize_health({"model_server": True, "redis": False,
                             "workers": True}) == "degraded"


def test_action_turns_are_not_handed_to_memory():
    """Mem0 reads a long prompt per exchange (§8.16); "block my card" and
    "Done. Your reference is BLK-000001." tell it nothing about the customer."""
    queued = []
    assistant = _assistant("action",
                           remember=lambda cid, msg, text: queued.append(msg))
    assistant.handle("c1", "block my card")
    assistant.handle("c1", "block my card", confirmed=True)
    assert queued == []
