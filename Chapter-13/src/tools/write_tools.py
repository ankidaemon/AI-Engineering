"""
Write tools: strict on purpose (§6.3, §6.5).

Each write tool is deliberately narrow — one thing, a clear set of required
fields — because a narrow tool is one the model can call correctly and one
you can reason about. Refusing to proceed without the required fields is
better than guessing.

`execute_write` is the one gate every write goes through: validate the
fields, derive the idempotency key, return the original reference on a
repeat, otherwise act and remember. High-impact tools additionally carry
`requires_confirmation`, which the action agent enforces before this gate
is ever reached (§6.6).
"""
from src.tools.base import ActionResult, ToolSpec
from src.tools.idempotency import derive_key


def check_fields(spec: ToolSpec, fields: dict):
    """None when every required field is filled with an allowed value,
    otherwise the question to ask. Called before asking for confirmation
    too, so a customer is never asked to approve an action that cannot run."""
    missing = [f for f in spec.required_fields if not fields.get(f)]
    wrong = [f for f, allowed in spec.allowed_values.items()
             if fields.get(f) and fields[f] not in allowed]
    if not (missing or wrong):
        return None
    asks = [_ask_for(spec, f) for f in missing + wrong]
    return ActionResult(
        status="needs_info", missing_fields=missing + wrong,
        message="I need a little more information: " + "; ".join(asks),
    )


def execute_write(spec: ToolSpec, fields: dict, desk, idem_store) -> ActionResult:
    problem = check_fields(spec, fields)
    if problem is not None:
        return problem
    same = spec.same_request_fields or spec.required_fields
    key = derive_key(spec.name, {f: fields[f] for f in same})
    prior = idem_store.recall(key)
    if prior is not None:
        # The same request was already acted on: return the original
        # reference instead of creating a second record (Failure 3).
        return ActionResult(status="done", reference=prior, duplicate=True,
                            message=f"That request already exists: {prior}")
    reference = spec.handler(fields, desk)
    idem_store.remember(key, reference)
    return ActionResult(status="done", reference=reference,
                        message=f"Done. Your reference is {reference}.")


def _ask_for(spec: ToolSpec, name: str) -> str:
    """'reason (one of: lost, stolen, ...)' when the choices are fixed."""
    allowed = spec.allowed_values.get(name)
    return f"{name} (one of: {', '.join(allowed)})" if allowed else name


# ── Why a card was blocked ───────────────────────────────────────────
# The full list the bank records. The first four come from the customer.
# bank_initiated is set by the bank's own fraud and risk systems, so a tool
# acting for a customer must never be able to choose it.
BLOCK_REASONS = {
    "lost": "the customer cannot find the card",
    "stolen": "the card was taken from the customer",
    "fraud": "the customer sees a payment they did not make",
    "customer_initiated": "the customer wants it stopped for their own reason",
    "bank_initiated": "the bank stopped it, for example after a fraud alert",
}
CUSTOMER_BLOCK_REASONS = ("lost", "stolen", "fraud", "customer_initiated")


# ── Handlers: each creates one record and returns its reference ──────

def _raise_complaint(fields, desk):
    return desk.create("complaint", {
        "customer_id": fields["customer_id"], "topic": fields["topic"],
        "details": fields.get("details", ""),
    })


def _request_callback(fields, desk):
    return desk.create("callback", {
        "customer_id": fields["customer_id"], "phone": fields["phone"],
        "preferred_time": fields.get("preferred_time", "any"),
    })


def _order_cheque_book(fields, desk):
    return desk.create("cheque_book", {
        "customer_id": fields["customer_id"], "account": fields["account"],
        "delivery_address": fields["delivery_address"],
    })


def _block_card(fields, desk):
    return desk.create("card_block", {
        "customer_id": fields["customer_id"], "card_id": fields["card_id"],
        "reason": fields["reason"],
    })


WRITE_TOOLS = [
    ToolSpec(
        name="raise_complaint",
        description=("Raise a formal complaint or grievance on the customer's "
                     "behalf: a wrong charge, a failed transaction, poor "
                     "service, a dispute about a fee. Creates a complaint "
                     "ticket and returns its number."),
        kind="write",
        required_fields=("customer_id", "topic"),
        handler=_raise_complaint,
    ),
    ToolSpec(
        name="request_callback",
        description=("Book a call back so a bank agent phones the customer: "
                     "when they want to speak to a person, discuss something "
                     "by phone, or be called at a preferred time. Returns a "
                     "booking reference."),
        kind="write",
        required_fields=("customer_id", "phone"),
        handler=_request_callback,
    ),
    ToolSpec(
        name="order_cheque_book",
        description=("Order a new cheque book for one of the customer's "
                     "accounts, delivered to their address. Use when the "
                     "customer asks for cheques, a cheque book, or a cheque "
                     "leaf refill. Returns a tracking id."),
        kind="write",
        required_fields=("customer_id", "account", "delivery_address"),
        handler=_order_cheque_book,
    ),
    ToolSpec(
        name="block_card",
        description=("Block or freeze one of the customer's cards immediately: "
                     "a lost card, a stolen card, a suspicious transaction, or "
                     "the customer wants a specific card stopped. Record why: "
                     "lost, stolen, fraud if they see a payment they did not "
                     "make, or customer_initiated for any other reason of "
                     "their own. If they have not said why, leave reason "
                     "empty so they are asked. High impact, so it is "
                     "confirmed before acting."),
        kind="write",
        required_fields=("customer_id", "card_id", "reason"),
        allowed_values={"reason": CUSTOMER_BLOCK_REASONS},
        # one card, one block: asking again with another reason is the same
        # request, not a second block
        same_request_fields=("customer_id", "card_id"),
        requires_confirmation=True,   # a worried customer gets to say no (§6.6)
        handler=_block_card,
    ),
]
