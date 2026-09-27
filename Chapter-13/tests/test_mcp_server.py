"""The MCP server, exercised in-process: no transport, no Redis (§1.5, §8.9).

The point under test is that the protocol door and the chat door share one
gate: the same field checks, the same idempotency, the same confirmation
rule, because they are the same lines of code.
"""
import asyncio

from src.mcp_server import build_server
from src.products.advisor import Customer
from src.tools.idempotency import IdempotencyStore
from src.tools.service_desk import ServiceDesk


def _server(fake_redis, get_customer=None):
    return build_server(desk=ServiceDesk(),
                        idem_store=IdempotencyStore(fake_redis),
                        get_customer=get_customer)


def _call(server, name, args):
    result = asyncio.run(server.call_tool(name, args))
    blocks = result[0] if isinstance(result, tuple) else result
    return "".join(getattr(block, "text", "") for block in blocks)


def test_every_banking_tool_is_listed_with_its_description(fake_redis):
    tools = asyncio.run(_server(fake_redis).list_tools())
    by_name = {t.name: t for t in tools}
    assert {"list_customer_products", "request_status", "raise_complaint",
            "request_callback", "order_cheque_book", "block_card"} <= set(by_name)
    # descriptions travel with the tools: they are what a remote model reads
    assert "cheque book" in by_name["order_cheque_book"].description
    assert "confirmed" in by_name["block_card"].description


def test_a_write_through_mcp_returns_the_customer_reference(fake_redis):
    text = _call(_server(fake_redis), "raise_complaint",
                 {"customer_id": "c1", "topic": "wrong fee charged"})
    assert "CMP-" in text


def test_the_idempotency_gate_guards_the_protocol_door_too(fake_redis):
    """Failure 3 cannot re-enter through MCP: a repeat returns the original
    reference instead of raising a second complaint."""
    server = _server(fake_redis)
    first = _call(server, "raise_complaint",
                  {"customer_id": "c1", "topic": "wrong fee charged"})
    second = _call(server, "raise_complaint",
                   {"customer_id": "c1", "topic": "wrong fee charged"})
    reference = first.split()[-1].rstrip(".")
    assert "already exists" in second and reference in second


def test_block_card_refuses_until_explicitly_confirmed(fake_redis):
    server = _server(fake_redis)
    refusal = _call(server, "block_card",
                    {"customer_id": "c1", "card_id": "card-2", "reason": "lost"})
    assert "onfirm" in refusal and "BLK-" not in refusal
    done = _call(server, "block_card",
                 {"customer_id": "c1", "card_id": "card-2", "reason": "lost",
                  "confirmed": True})
    assert "BLK-" in done


def test_read_tool_answers_from_the_customer_record(fake_redis):
    demo = Customer("c1", holdings=["everyday-savings", "travel-card"])
    server = _server(fake_redis, get_customer=lambda cid: demo)
    text = _call(server, "list_customer_products", {"customer_id": "c1"})
    assert "everyday-savings" in text and "travel-card" in text
