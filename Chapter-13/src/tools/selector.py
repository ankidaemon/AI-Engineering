"""
Retrieval-based tool selection, plus follow-up contextualization (§6.4).

A real bank has hundreds of tools, and handing all of them to the model on
every message is slow, expensive, and error prone. Instead the selector
embeds every tool's description once, retrieves the handful whose
descriptions match what the customer asked, and only those few reach the
model. Two cheap retrieval steps replace one enormous call, which keeps
cost and latency flat as the tool catalog grows.

The wrinkle (Failure 5): retrieval works on the words in the current
message, and in a real conversation most messages depend on what came just
before. "Block the second one" retrieves nothing meaningful on its own. So
before selecting, a follow-up is rewritten into a standalone request using
the last few turns — in a banking assistant this step is not optional.
"""
from src.vectorstores.cosine_index import CosineIndex

REWRITE_PROMPT = """Rewrite the customer's latest message as one standalone \
request that makes sense on its own, resolving any references ("it", "that \
one", "the second one") using the conversation so far. Keep every detail the \
customer gave, such as a reason, an amount, a date, or a name, in their own \
words. Add nothing they did not say: no currency, no amount, no detail. Reply \
with the rewritten request only.

Conversation so far:
{history}

Latest message: {message}

Standalone request:"""


def build_tool_index(specs: list, embeddings) -> CosineIndex:
    """Embed every tool description once, at startup."""
    index = CosineIndex(embeddings)
    index.add([(spec.description, spec) for spec in specs])
    return index


def contextualize(message: str, history: list, model=None,
                  max_turns: int = None) -> str:
    """A message with no history is already standalone; otherwise rewrite it
    so 'block the second one' becomes a request retrieval can work with.

    Only the last `max_turns` turns are sent. A follow-up points at
    something said a moment ago, and sending the whole conversation would
    make this prompt, and its cost, grow with every message (§8.16)."""
    if not history:
        return message
    if max_turns is None:
        max_turns = _configured_history_turns()
    recent = list(history)[-max_turns:] if max_turns > 0 else []
    if not recent:
        return message
    model = model or _default_fast_model()
    prompt = REWRITE_PROMPT.format(history="\n".join(recent), message=message)
    response = model.invoke(prompt)
    rewritten = getattr(response, "content", str(response)).strip()
    return rewritten or message


def select_tools(message: str, history: list, tool_index: CosineIndex,
                 k: int = 4, model=None, max_turns: int = None) -> tuple:
    """Contextualize, then retrieve. Returns (standalone_request, [ToolSpec])."""
    standalone = contextualize(message, history, model=model,
                               max_turns=max_turns)
    specs = [spec for spec, _score in tool_index.top_k(standalone, k)]
    return standalone, specs


def _configured_history_turns() -> int:
    try:
        from src.config import settings
        return settings.history_turns
    except Exception:
        return 6


def _default_fast_model():
    from langchain_ollama import ChatOllama
    from src.config import settings
    return ChatOllama(model=settings.fast_model,
                      base_url=settings.ollama_base_url)
