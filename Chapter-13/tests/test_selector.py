"""Retrieval-based tool selection and follow-up contextualization (§6.4)."""
from src.tools.read_tools import READ_TOOLS
from src.tools.selector import build_tool_index, contextualize, select_tools
from src.tools.write_tools import WRITE_TOOLS
from tests.conftest import FakeModel

ALL_TOOLS = READ_TOOLS + WRITE_TOOLS


def test_clear_request_retrieves_the_right_tool(embeddings):
    index = build_tool_index(ALL_TOOLS, embeddings)
    top = [spec.name for spec, _ in index.top_k(
        "I lost my card this morning, please stop it before someone uses it", k=2)]
    assert "block_card" in top


def test_cheque_book_request_retrieves_its_tool(embeddings):
    index = build_tool_index(ALL_TOOLS, embeddings)
    top = [spec.name for spec, _ in index.top_k(
        "please send me a new cheque book for my savings account", k=2)]
    assert "order_cheque_book" in top


def test_standalone_message_skips_the_rewrite():
    """No history means no model call at all — the message is already
    standalone, and model=None proves nothing was invoked."""
    assert contextualize("block my travel card", [], model=None) == \
        "block my travel card"


def test_follow_up_is_rewritten_with_history():
    model = FakeModel(reply="block the customer's premium travel card")
    history = ["Customer: which cards do I have?",
               "Assistant: 1. Cashback Card  2. Premium Travel Card"]
    rewritten = contextualize("block the second one", history, model=model)
    assert rewritten == "block the customer's premium travel card"
    assert "block the second one" in model.prompts[0]
    assert "Premium Travel Card" in model.prompts[0]   # history reached the model


def test_follow_up_only_resolves_with_history(embeddings):
    """Failure 5 end to end: the contextualized request retrieves block_card."""
    index = build_tool_index(ALL_TOOLS, embeddings)
    history = ["Customer: which cards do I have?",
               "Assistant: 1. Cashback Card  2. Premium Travel Card"]
    model = FakeModel(reply="block the customer's premium travel card")

    standalone, specs = select_tools("block the second one", history,
                                     index, k=2, model=model)
    assert standalone == "block the customer's premium travel card"
    assert "block_card" in [s.name for s in specs]


def test_empty_rewrite_falls_back_to_the_original():
    model = FakeModel(reply="   ")
    assert contextualize("order cheques", ["turn"], model=model) == "order cheques"


def test_only_the_last_few_turns_are_sent_to_the_rewrite():
    """The rewrite prompt must not grow with the length of the conversation."""
    from tests.conftest import FakeModel
    history = [f"Customer: message {i}" for i in range(40)]
    model = FakeModel(reply="block the travel card")
    contextualize("block the second one", history, model=model, max_turns=6)
    prompt = model.prompts[-1]
    assert "message 39" in prompt and "message 34" in prompt
    assert "message 33" not in prompt
