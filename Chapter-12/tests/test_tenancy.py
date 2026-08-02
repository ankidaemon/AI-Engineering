"""
Customer isolation.

Three separate boundaries, so three sets of tests: who the caller is, which
conversation they may resume, and which vectors they may read. The last of these
is the one that matters most, because a leak there does not raise, it quietly
puts another customer's text into a prompt and returns it in a brief.
"""
import pytest
from langchain_core.documents import Document
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langgraph.checkpoint.memory import MemorySaver

from src.tenancy.auth import ApiKeyAuthenticator, Unauthenticated, parse_api_keys
from src.tenancy.conversations import InMemoryConversations, ConversationAccessDenied
from src.vectorstores.pgvector_store import (
    IntelligenceVectorStore, InMemoryBackend, make_vector_store, sqlalchemy_url,
)
from src.monitor.graph import build_intelligence_graph


# ── Authentication ───────────────────────────────────────────────────

def test_a_valid_key_resolves_to_its_customer():
    auth = ApiKeyAuthenticator("k-acme:acme,k-globex:globex")
    assert auth.customer_for("k-acme") == "acme"
    assert auth.customer_for("k-globex") == "globex"


@pytest.mark.parametrize("key", [None, "", "k-unknown", "k-acme "])
def test_anything_but_an_exact_key_is_rejected(key):
    auth = ApiKeyAuthenticator("k-acme:acme")
    with pytest.raises(Unauthenticated):
        auth.customer_for(key)


def test_no_configured_keys_means_nobody_gets_in():
    """There is no anonymous customer, so an unconfigured deployment is closed."""
    auth = ApiKeyAuthenticator("")
    with pytest.raises(Unauthenticated):
        auth.customer_for("anything")


def test_plaintext_keys_are_not_retained():
    parsed = parse_api_keys("k-acme:acme")
    assert "k-acme" not in parsed
    assert list(parsed.values()) == ["acme"]


# ── Conversation ownership ───────────────────────────────────────────

def test_a_new_conversation_gets_a_server_minted_id():
    convs = InMemoryConversations()
    first = convs.start("acme")
    second = convs.start("acme")
    assert first != second
    assert len(first) == 36            # a uuid, not anything the client chose


def test_the_owner_can_resume_their_own_conversation():
    convs = InMemoryConversations()
    conversation_id = convs.start("acme")
    assert convs.resolve("acme", conversation_id) == conversation_id


def test_another_customer_cannot_resume_it():
    """The whole reason thread ids may not come from the request body."""
    convs = InMemoryConversations()
    stolen = convs.start("acme")
    with pytest.raises(ConversationAccessDenied):
        convs.resolve("globex", stolen)


def test_an_invented_conversation_id_is_refused():
    convs = InMemoryConversations()
    with pytest.raises(ConversationAccessDenied):
        convs.resolve("acme", "00000000-0000-0000-0000-000000000000")


def test_omitting_the_id_starts_a_conversation_rather_than_failing():
    convs = InMemoryConversations()
    conversation_id = convs.resolve("acme", None)
    assert convs.owner_of(conversation_id) == "acme"


# ── Vector scoping ───────────────────────────────────────────────────

def test_the_unscoped_store_cannot_search():
    """Not a filter someone can forget: there is no unscoped call to make."""
    store = make_vector_store("memory")
    assert not hasattr(store, "similarity_search")
    assert not hasattr(store, "add_documents")


@pytest.mark.parametrize("given,expected", [
    ("postgresql://intel:intel@localhost:5432/intel",
     "postgresql+psycopg://intel:intel@localhost:5432/intel"),
    ("postgres://intel:intel@localhost:5432/intel",
     "postgresql+psycopg://intel:intel@localhost:5432/intel"),
    ("postgresql+psycopg://intel:intel@localhost:5432/intel",
     "postgresql+psycopg://intel:intel@localhost:5432/intel"),
])
def test_the_same_setting_serves_sqlalchemy_and_psycopg(given, expected):
    """One POSTGRES_URL, two clients. SQLAlchemy picks a driver from the scheme
    and defaults to psycopg2, which is not installed, so a plain URL would fail
    at startup."""
    assert sqlalchemy_url(given) == expected


@pytest.mark.parametrize("bad", ["", "   ", None])
def test_a_scope_without_a_customer_is_refused(bad):
    store = make_vector_store("memory")
    with pytest.raises(ValueError):
        store.for_customer(bad)


def test_a_search_never_returns_another_customers_documents():
    store = make_vector_store("memory")
    store.for_customer("acme").add_documents(
        [Document(page_content="acme merger talks with a rival", metadata={})]
    )
    store.for_customer("globex").add_documents(
        [Document(page_content="globex merger talks with a rival", metadata={})]
    )

    hits = store.for_customer("acme").similarity_search("merger talks", k=10)

    assert len(hits) == 1
    assert "acme" in hits[0].page_content
    assert hits[0].metadata["customer_id"] == "acme"


def test_a_crowded_neighbour_does_not_starve_a_small_customer():
    """
    The filter is applied to the query, not to the results. A flat FAISS index
    post-filters a global top `fetch_k`, so this is the case where a big
    customer's documents crowd out a small one and the small one gets nothing.
    """
    store = make_vector_store("memory")
    big = store.for_customer("globex")
    big.add_documents([
        Document(page_content=f"merger talks round {i}", metadata={})
        for i in range(500)
    ])
    store.for_customer("acme").add_documents(
        [Document(page_content="merger talks at acme", metadata={})]
    )

    hits = store.for_customer("acme").similarity_search("merger talks", k=3)

    assert len(hits) == 1
    assert hits[0].metadata["customer_id"] == "acme"


def test_document_metadata_cannot_forge_a_customer_id():
    """The id is stamped from the scope, so setting it on the way in does nothing."""
    store = make_vector_store("memory")
    store.for_customer("acme").add_documents(
        [Document(page_content="planted", metadata={"customer_id": "globex"})]
    )
    assert store.for_customer("globex").similarity_search("planted", k=10) == []
    assert len(store.for_customer("acme").similarity_search("planted", k=10)) == 1


def test_a_caller_supplied_filter_cannot_widen_the_scope():
    store = make_vector_store("memory")
    store.for_customer("globex").add_documents(
        [Document(page_content="globex internals", metadata={})]
    )
    hits = store.for_customer("acme").similarity_search(
        "globex internals", k=10, filter_dict={"customer_id": "globex"}
    )
    assert hits == []


# ── The pipeline end to end ──────────────────────────────────────────

RELEVANT = ('{"relevance_score": 0.9, "content_type": "news", '
            '"is_relevant": true, "skip_reason": ""}')
ANALYSIS = ('{"key_developments": ["a new regulation was proposed"], '
            '"impact_assessment": "significant for compliance teams", '
            '"entities": ["European Parliament"], "sentiment": "neutral", '
            '"urgency": "high", "action_items": ["brief the legal team"]}')


def _graph(store):
    return build_intelligence_graph(
        store,
        fast_model=FakeListChatModel(responses=[RELEVANT, RELEVANT]),
        quality_model=FakeListChatModel(
            responses=[ANALYSIS, "ACME CONFIDENTIAL BRIEF", ANALYSIS, "globex brief"]
        ),
        checkpointer=MemorySaver(),
    )


def _state(customer_id, conversation_id):
    return {
        "content_url": "http://example.com/reg",
        "content_text": "A long article about a proposed AI regulation.",
        "content_title": "New AI regulation proposed",
        "topic": "AI regulation",
        "monitor_id": conversation_id,
        "customer_id": customer_id,
        "errors": [],
        "messages": [],
    }


def test_one_customers_brief_never_reaches_another_customers_run():
    """
    The regression test for the leak this design exists to close. Retrieval feeds
    `related_past_intel` straight into the analysis and brief prompts, so a
    document crossing here ends up in another customer's output.
    """
    store = make_vector_store("memory")
    graph = _graph(store)

    graph.invoke(_state("acme", "conv-acme"),
                 {"configurable": {"thread_id": "conv-acme"}})
    assert store.for_customer("acme").similarity_search("regulation", k=5)

    second = graph.invoke(_state("globex", "conv-globex"),
                          {"configurable": {"thread_id": "conv-globex"}})

    assert second["related_past_intel"] == []
    assert "ACME" not in " ".join(second["related_past_intel"])


def test_a_run_without_a_customer_fails_instead_of_reading_everything():
    store = make_vector_store("memory")
    store.for_customer("acme").add_documents(
        [Document(page_content="acme brief", metadata={})]
    )
    graph = _graph(store)

    state = _state("acme", "conv-1")
    del state["customer_id"]

    with pytest.raises(ValueError):
        graph.invoke(state, {"configurable": {"thread_id": "conv-1"}})
