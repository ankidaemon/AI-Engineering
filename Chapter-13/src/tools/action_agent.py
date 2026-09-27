"""
The action agent: the only part allowed to change anything (§6.1–§6.6).

The flow per message: contextualize the request and retrieve the few tools
that match (selector), let the model pick one of those tools and fill its
arguments, then enforce the guards — confirmation for high-impact tools,
required fields, and the idempotency gate — before anything touches the
service desk. Restraint is the feature: an unknown or unmatched request is
declined, not improvised.

The tool-choosing model is injected. Tests use a fake that returns a fixed
choice; production binds the retrieved tools to a tool-calling model.
"""
import json

from src.tools.base import ActionResult
from src.tools.pending import PendingActions
from src.tools.read_tools import READ_TOOLS
from src.tools.selector import select_tools
from src.tools.write_tools import WRITE_TOOLS, check_fields, execute_write

CHOOSE_PROMPT = """You are a banking assistant choosing exactly one tool for \
the customer's request. Reply with JSON only: \
{{"tool": "<name>", "args": {{...}}}} using a tool from the list, or \
{{"tool": "none"}} if none of them fits.

Tools:
{tools}

Customer id: {customer_id}
Request: {request}

JSON:"""

DECLINE_MESSAGE = ("I am not able to do that here. "
                   "Let me connect you to someone who can help.")


class ActionAgent:
    def __init__(self, tool_index, desk, idem_store, model=None, top_k: int = 4,
                 pending=None):
        self._tool_index = tool_index
        self._pending = pending or PendingActions()
        self._desk = desk
        self._idem = idem_store
        self._model = model
        self._top_k = top_k
        self._specs_by_name = {s.name: s for s in READ_TOOLS + WRITE_TOOLS}

    def handle(self, message: str, history: list, customer_id: str,
               confirmed: bool = False) -> ActionResult:
        if confirmed:
            held = self._pending.take(customer_id)
            if held is not None:
                # The customer said yes to this exact action. Run it as it
                # was chosen: no second model call, no second decision.
                name, fields = held
                fields["customer_id"] = customer_id
                return execute_write(self._specs_by_name[name], fields,
                                     self._desk, self._idem)
            # Nothing is waiting (it expired, or was never asked about), so
            # this is a new request and goes through the questions below.

        standalone, candidates = select_tools(
            message, history, self._tool_index, k=self._top_k, model=self._model)
        if not candidates:
            return ActionResult(status="unknown_tool", message=DECLINE_MESSAGE)

        choice = self._choose(standalone, candidates, customer_id)
        spec = self._specs_by_name.get(choice.get("tool", "none"))
        if spec is None or spec not in candidates:
            # The model picked nothing, or something it was not offered.
            return ActionResult(status="unknown_tool", message=DECLINE_MESSAGE)

        fields = dict(choice.get("args", {}))
        # Always the session's id, even if the model wrote one: who the
        # customer is comes from their login, never from generated text.
        fields["customer_id"] = customer_id

        if spec.kind == "read":
            return ActionResult(status="done",
                                message=str(spec.handler(fields, self._desk)))

        # Fields first: asking "shall I go ahead?" about an action that is
        # missing its reason wastes a turn and a model call (§8.16).
        problem = check_fields(spec, fields)
        if problem is not None:
            return problem

        if spec.requires_confirmation:
            # A customer who was only worried, not certain, gets a chance
            # to say so before the card stops working (§6.6). The choice is
            # held, so the yes runs exactly this (§8.16).
            self._pending.hold(customer_id, spec.name, fields)
            return ActionResult(
                status="needs_confirmation",
                message=(f"Just to confirm: you want me to {spec.name.replace('_', ' ')} "
                         f"now. Shall I go ahead?"),
            )
        return execute_write(spec, fields, self._desk, self._idem)

    def _choose(self, request: str, candidates: list, customer_id: str) -> dict:
        model = self._model or _default_model()
        tools_text = "\n".join(describe_for_model(s) for s in candidates)
        prompt = CHOOSE_PROMPT.format(tools=tools_text, request=request,
                                      customer_id=customer_id)
        response = model.invoke(prompt)
        return parse_tool_choice(getattr(response, "content", str(response)))


def describe_for_model(spec) -> str:
    """One line per tool: what it does, and the argument names to fill.

    Without the names the model has to guess them, and a guess like "card"
    instead of "card_id" fails the required-field check even when the model
    understood the customer perfectly. customer_id is left out because the
    agent fills it from the session, never from the model."""
    needs = [f for f in spec.required_fields if f != "customer_id"]
    args = ", ".join(
        f"{f} (one of: {', '.join(spec.allowed_values[f])})"
        if f in spec.allowed_values else f
        for f in needs) or "none"
    return f"- {spec.name}: {spec.description} Arguments: {args}."


def parse_tool_choice(text: str) -> dict:
    """Pull the JSON tool choice out of a model reply; fail soft to 'none'."""
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        return {"tool": "none"}
    try:
        parsed = json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return {"tool": "none"}
    if not isinstance(parsed, dict) or "tool" not in parsed:
        return {"tool": "none"}
    return parsed


def _default_model():
    from langchain_ollama import ChatOllama
    from src.config import settings
    return ChatOllama(model=settings.fast_model,
                      base_url=settings.ollama_base_url)
