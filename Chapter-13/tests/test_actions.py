"""Write tools: validation, idempotency, confirmation (§6.3, §6.5, §6.6)."""
import json

import pytest

from src.tools.action_agent import ActionAgent, parse_tool_choice
from src.tools.idempotency import IdempotencyStore, derive_key
from src.tools.read_tools import READ_TOOLS
from src.tools.selector import build_tool_index
from src.tools.service_desk import ServiceDesk
from src.tools.write_tools import WRITE_TOOLS, execute_write
from tests.conftest import FakeModel


def _spec(name):
    return next(s for s in READ_TOOLS + WRITE_TOOLS if s.name == name)


@pytest.fixture
def desk():
    return ServiceDesk()


@pytest.fixture
def idem(fake_redis):
    return IdempotencyStore(fake_redis)


# ── The write gate ───────────────────────────────────────────────────

def test_missing_fields_ask_instead_of_guessing(desk, idem):
    result = execute_write(_spec("order_cheque_book"),
                           {"customer_id": "c1"}, desk, idem)
    assert result.status == "needs_info"
    assert set(result.missing_fields) == {"account", "delivery_address"}
    assert desk.record_count == 0


def test_a_write_returns_a_reference_the_customer_keeps(desk, idem):
    result = execute_write(_spec("raise_complaint"),
                           {"customer_id": "c1", "topic": "wrong late fee"},
                           desk, idem)
    assert result.status == "done"
    assert result.reference.startswith("CMP-")
    assert desk.status(result.reference)["status"] == "open"


def test_the_same_request_twice_creates_one_record(desk, idem):
    """Failure 3: the retry gets the ORIGINAL ticket, not a second one."""
    fields = {"customer_id": "c1", "topic": "wrong late fee"}
    first = execute_write(_spec("raise_complaint"), fields, desk, idem)
    second = execute_write(_spec("raise_complaint"), dict(fields), desk, idem)

    assert second.duplicate is True
    assert second.reference == first.reference
    assert desk.record_count == 1


def test_a_different_request_is_not_a_duplicate(desk, idem):
    first = execute_write(_spec("raise_complaint"),
                          {"customer_id": "c1", "topic": "wrong late fee"}, desk, idem)
    other = execute_write(_spec("raise_complaint"),
                          {"customer_id": "c1", "topic": "card never arrived"}, desk, idem)
    assert other.duplicate is False
    assert other.reference != first.reference
    assert desk.record_count == 2


def test_derive_key_ignores_field_order():
    a = derive_key("raise_complaint", {"topic": "x", "customer_id": "c1"})
    b = derive_key("raise_complaint", {"customer_id": "c1", "topic": "x"})
    assert a == b
    assert a != derive_key("request_callback", {"customer_id": "c1", "topic": "x"})


# ── The action agent: confirmation and restraint (§6.6) ─────────────

def _agent(embeddings, desk, idem, reply):
    index = build_tool_index(READ_TOOLS + WRITE_TOOLS, embeddings)
    return ActionAgent(index, desk, idem, model=FakeModel(reply=reply), top_k=4)


def test_high_impact_action_asks_before_acting(embeddings, desk, idem):
    choice = json.dumps({"tool": "block_card",
                         "args": {"card_id": "card-2", "reason": "lost"}})
    agent = _agent(embeddings, desk, idem, reply=choice)

    result = agent.handle("block my premium travel card", [], "c1")
    assert result.status == "needs_confirmation"
    assert desk.record_count == 0            # nothing happened yet

    confirmed = agent.handle("block my premium travel card", [], "c1",
                             confirmed=True)
    assert confirmed.status == "done"
    assert confirmed.reference.startswith("BLK-")
    assert desk.record_count == 1


def test_cheque_book_order_flows_straight_through(embeddings, desk, idem):
    choice = json.dumps({"tool": "order_cheque_book",
                         "args": {"account": "SAV-01",
                                  "delivery_address": "12 Hill Road"}})
    agent = _agent(embeddings, desk, idem, reply=choice)
    result = agent.handle("please send me a new cheque book for my savings account",
                          [], "c1")
    assert result.status == "done"
    assert result.reference.startswith("CHQ-")


def test_read_tool_answers_without_any_write_machinery(embeddings, desk, idem):
    ref = desk.create("complaint", {"customer_id": "c1", "topic": "fee"})
    choice = json.dumps({"tool": "request_status", "args": {"reference": ref}})
    agent = _agent(embeddings, desk, idem, reply=choice)
    result = agent.handle(f"what happened to my complaint {ref}", [], "c1")
    assert result.status == "done"
    assert "open" in result.message


def test_model_declining_declines(embeddings, desk, idem):
    agent = _agent(embeddings, desk, idem, reply=json.dumps({"tool": "none"}))
    result = agent.handle("please rewrite my mortgage contract", [], "c1")
    assert result.status == "unknown_tool"
    assert desk.record_count == 0


def test_model_cannot_pick_a_tool_it_was_not_offered(embeddings, desk, idem):
    # k=1 on a cheque book request: block_card is not among the candidates,
    # so a model that names it anyway is refused.
    index = build_tool_index(READ_TOOLS + WRITE_TOOLS, embeddings)
    choice = json.dumps({"tool": "block_card", "args": {"card_id": "card-1"}})
    agent = ActionAgent(index, desk, idem, model=FakeModel(reply=choice), top_k=1)
    result = agent.handle("please send me a new cheque book", [], "c1")
    assert result.status == "unknown_tool"
    assert desk.record_count == 0


def test_tool_choice_parsing_fails_soft():
    assert parse_tool_choice('{"tool": "block_card", "args": {}}')["tool"] == "block_card"
    assert parse_tool_choice("Sure! {\"tool\": \"none\"} hope that helps")["tool"] == "none"
    assert parse_tool_choice("no json here")["tool"] == "none"
    assert parse_tool_choice('{"broken": true}')["tool"] == "none"


def test_the_model_is_told_which_arguments_each_tool_needs(embeddings, desk, idem):
    """The model can only fill fields it has been told about. customer_id is
    not offered, because it comes from the session and not from the model."""
    agent = _agent(embeddings, desk, idem, reply='{"tool": "none"}')
    agent.handle("I lost my card, please block it", [], "c1")
    prompt = agent._model.prompts[-1]
    assert "block_card:" in prompt
    assert "Arguments: card_id, reason (one of: lost, stolen, fraud, customer_initiated)." in prompt
    assert "customer_id" not in prompt.split("Tools:")[1].split("Customer id:")[0]


def test_the_model_cannot_choose_whose_account_it_acts_on(embeddings, desk, idem):
    """A customer id written by the model is overwritten by the session's."""
    reply = json.dumps({"tool": "raise_complaint",
                        "args": {"customer_id": "someone-else", "topic": "late fee"}})
    agent = _agent(embeddings, desk, idem, reply=reply)
    result = agent.handle("I want to complain about a late fee", [], "c1")
    assert result.status == "done"
    assert desk.status(result.reference)["customer_id"] == "c1"


# ── Why a card was blocked ───────────────────────────────────────────

def test_a_block_records_its_reason(desk, idem):
    result = execute_write(_spec("block_card"),
                           {"customer_id": "c1", "card_id": "card-2",
                            "reason": "fraud"}, desk, idem)
    assert result.status == "done"
    assert desk.status(result.reference)["reason"] == "fraud"


def test_a_block_with_no_reason_asks_and_lists_the_choices(desk, idem):
    result = execute_write(_spec("block_card"),
                           {"customer_id": "c1", "card_id": "card-2"}, desk, idem)
    assert result.status == "needs_info"
    assert result.missing_fields == ["reason"]
    assert "lost, stolen, fraud, customer_initiated" in result.message
    assert desk.record_count == 0


@pytest.mark.parametrize("reason", ["bank_initiated", "because I said so"])
def test_a_reason_outside_the_customer_list_is_refused(desk, idem, reason):
    """bank_initiated is a real reason, but only the bank's own systems may
    record it. A customer's request, or a model, cannot choose it."""
    result = execute_write(_spec("block_card"),
                           {"customer_id": "c1", "card_id": "card-2",
                            "reason": reason}, desk, idem)
    assert result.status == "needs_info"
    assert desk.record_count == 0


def test_blocking_the_same_card_again_with_another_reason_is_one_block(desk, idem):
    first = execute_write(_spec("block_card"),
                          {"customer_id": "c1", "card_id": "card-2",
                           "reason": "lost"}, desk, idem)
    again = execute_write(_spec("block_card"),
                          {"customer_id": "c1", "card_id": "card-2",
                           "reason": "stolen"}, desk, idem)
    assert again.duplicate is True
    assert again.reference == first.reference
    assert desk.record_count == 1


def test_missing_fields_are_asked_for_before_confirmation(embeddings, desk, idem):
    """Found by measuring (§8.16): a block with no reason used to ask the
    customer to confirm, then ask for the reason, so the yes was wasted."""
    choice = json.dumps({"tool": "block_card", "args": {"card_id": "card-2"}})
    agent = _agent(embeddings, desk, idem, reply=choice)
    result = agent.handle("block my travel card", [], "c1")
    assert result.status == "needs_info"
    assert result.missing_fields == ["reason"]
    assert desk.record_count == 0


# ── Saying yes runs the held action (§8.16) ─────────────────────────

def test_yes_runs_the_held_action_without_a_second_model_call(embeddings, desk, idem):
    choice = json.dumps({"tool": "block_card",
                         "args": {"card_id": "card-2", "reason": "lost"}})
    agent = _agent(embeddings, desk, idem, reply=choice)
    agent.handle("I lost my card, please block it", [], "c1")
    calls_before = len(agent._model.prompts)

    done = agent.handle("I lost my card, please block it", [], "c1",
                        confirmed=True)
    assert done.status == "done" and done.reference.startswith("BLK-")
    assert len(agent._model.prompts) == calls_before
    assert desk.status(done.reference)["card_id"] == "card-2"


def test_yes_runs_what_was_approved_even_if_the_model_would_now_choose_differently(
        embeddings, desk, idem):
    replies = [json.dumps({"tool": "block_card",
                           "args": {"card_id": "card-2", "reason": "lost"}}),
               json.dumps({"tool": "block_card",
                           "args": {"card_id": "card-1", "reason": "lost"}})]
    agent = _agent(embeddings, desk, idem, reply=replies)
    agent.handle("block my card", [], "c1")
    done = agent.handle("block my card", [], "c1", confirmed=True)
    assert desk.status(done.reference)["card_id"] == "card-2"


def test_a_yes_with_nothing_waiting_asks_again(embeddings, desk, idem):
    """A confirmed flag alone is not consent: there must be an action the
    customer was actually shown."""
    choice = json.dumps({"tool": "block_card",
                         "args": {"card_id": "card-2", "reason": "lost"}})
    agent = _agent(embeddings, desk, idem, reply=choice)
    result = agent.handle("block my card", [], "c1", confirmed=True)
    assert result.status == "needs_confirmation"
    assert desk.record_count == 0


def test_one_customers_yes_cannot_run_another_customers_action(embeddings, desk, idem):
    choice = json.dumps({"tool": "block_card",
                         "args": {"card_id": "card-2", "reason": "lost"}})
    agent = _agent(embeddings, desk, idem, reply=choice)
    agent.handle("block my card", [], "c1")
    other = agent.handle("block my card", [], "c2", confirmed=True)
    assert other.status == "needs_confirmation"
    assert desk.record_count == 0


def test_held_actions_live_in_redis_and_are_taken_once(fake_redis):
    from src.tools.pending import PendingActions
    pending = PendingActions(fake_redis)
    pending.hold("c1", "block_card", {"card_id": "card-2", "reason": "lost"})
    assert pending.take("c1") == ("block_card", {"card_id": "card-2", "reason": "lost"})
    assert pending.take("c1") is None


def test_a_held_action_expires():
    from src.tools.pending import PendingActions
    pending = PendingActions(ttl_seconds=-1)
    pending.hold("c1", "block_card", {"card_id": "card-2"})
    assert pending.take("c1") is None
