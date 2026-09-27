"""
Read tools: safe to call freely (§6.2).

Calling any of these twice does no harm, so they carry no idempotency
machinery and no confirmation — being generous with reads is the payoff of
keeping the two kinds of tool separate.
"""
from src.tools.base import ToolSpec


def _list_customer_products(fields: dict, desk) -> str:
    """The catalog lookup itself is done by the caller (the action agent
    holds the catalog); this handler formats holdings the customer sent."""
    holdings = fields.get("holdings") or []
    if not holdings:
        return "You do not hold any products with us yet."
    return "Your products: " + ", ".join(holdings)


def _request_status(fields: dict, desk) -> str:
    record = desk.status(fields["reference"])
    return f"Request {record['reference']}: {record['status']}"


READ_TOOLS = [
    ToolSpec(
        name="list_customer_products",
        description=("List the products the customer currently holds with the "
                     "bank: their accounts, credit cards, and loans. Use when "
                     "the customer asks what they have, which cards are on "
                     "their profile, or wants their products shown."),
        kind="read",
        required_fields=(),
        handler=_list_customer_products,
    ),
    ToolSpec(
        name="request_status",
        description=("Look up the current status of an existing service "
                     "request by its reference number: a complaint ticket, a "
                     "call back booking, a cheque book order, or a card block. "
                     "Use when the customer asks what happened to a request "
                     "they already raised."),
        kind="read",
        required_fields=("reference",),
        handler=_request_status,
    ),
]
