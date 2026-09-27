"""
The banking tools, exposed over MCP (§1.5, §8.9).

Any assistant that speaks the protocol can list these tools, read their
descriptions, and call them — which is exactly why the guards cannot live
in the client. Every write here flows through the same `execute_write`
gate as the chat path (required fields, idempotency, the duplicate answer),
and `block_card` demands an explicit `confirmed=True` that a caller may
only set after its own user has agreed (§1.3: a server never relies on the
client behaving).

Run it over stdio:  python -m src.mcp_server
To serve it over HTTP inside the bank's network instead, replace
`server.run()` with `server.run(transport="streamable-http")` and put the
bank's usual auth in front — the protocol itself does not change (§1.4).

Dependencies are injectable so the tests exercise the server in-process,
with no transport and no Redis (§8.13).
"""


def build_server(desk=None, idem_store=None, get_customer=None):
    from mcp.server.fastmcp import FastMCP

    from src.tools.service_desk import ServiceDesk
    from src.tools.write_tools import WRITE_TOOLS, execute_write

    desk = desk or ServiceDesk()
    if idem_store is None:
        import redis as redis_lib

        from src.config import settings
        from src.tools.idempotency import IdempotencyStore
        idem_store = IdempotencyStore(redis_lib.from_url(settings.redis_url))
    specs = {spec.name: spec for spec in WRITE_TOOLS}

    server = FastMCP("banking-tools")

    def _write(name: str, fields: dict, confirmed: bool = False) -> str:
        """The one gate, shared with the chat path: same field checks, same
        idempotency, same words on a repeat."""
        spec = specs[name]
        if spec.requires_confirmation and not confirmed:
            return ("This is a high impact action. Confirm with the customer, "
                    "then call again with confirmed=true.")
        return execute_write(spec, fields, desk, idem_store).message

    @server.tool()
    def list_customer_products(customer_id: str) -> str:
        """List the products the customer currently holds with the bank:
        their accounts, credit cards, and loans."""
        customer = get_customer(customer_id) if get_customer else None
        holdings = customer.holdings if customer else []
        if not holdings:
            return "You do not hold any products with us yet."
        return "Your products: " + ", ".join(holdings)

    @server.tool()
    def request_status(reference: str) -> str:
        """Look up the current status of an existing service request by its
        reference number: a complaint ticket, a call back booking, a cheque
        book order, or a card block."""
        record = desk.status(reference)
        return f"Request {record['reference']}: {record['status']}"

    @server.tool()
    def raise_complaint(customer_id: str, topic: str, details: str = "") -> str:
        """Raise a formal complaint on the customer's behalf: a wrong
        charge, a failed transaction, poor service, a fee dispute. Returns
        the ticket number the customer keeps."""
        return _write("raise_complaint", {"customer_id": customer_id,
                                          "topic": topic, "details": details})

    @server.tool()
    def request_callback(customer_id: str, phone: str,
                         preferred_time: str = "any") -> str:
        """Book a call back so a bank agent phones the customer, optionally
        at a preferred time. Returns a booking reference."""
        return _write("request_callback", {"customer_id": customer_id,
                                           "phone": phone,
                                           "preferred_time": preferred_time})

    @server.tool()
    def order_cheque_book(customer_id: str, account: str,
                          delivery_address: str) -> str:
        """Order a new cheque book for one of the customer's accounts,
        delivered to their address. Returns a tracking id."""
        return _write("order_cheque_book",
                      {"customer_id": customer_id, "account": account,
                       "delivery_address": delivery_address})

    @server.tool()
    def block_card(customer_id: str, card_id: str, reason: str,
                   confirmed: bool = False) -> str:
        """Block one of the customer's cards immediately. reason is one of:
        lost, stolen, fraud (a payment the customer did not make), or
        customer_initiated. High impact: set confirmed=true only after the
        customer has explicitly agreed."""
        return _write("block_card", {"customer_id": customer_id,
                                     "card_id": card_id, "reason": reason},
                      confirmed=confirmed)

    return server


if __name__ == "__main__":
    build_server().run()          # stdio transport by default (§1.4)
