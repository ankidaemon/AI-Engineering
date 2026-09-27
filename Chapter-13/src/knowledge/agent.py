"""
The knowledge agent: grounded, cited, and willing to decline (§4.4).

The single most important property here is that it does not make things up.
Two habits carry that: grounding (answer only from the retrieved passages,
and when they are weak or absent, decline and hand off instead of guessing)
and citation (every answer carries the sources it was built from, so a
customer or an auditor can check it, and a missing source is a signal the
agent should not have answered).

The model is injected so tests run offline; production defaults to the
quality model served by Ollama.
"""
from dataclasses import dataclass, field

DEFAULT_MIN_RELEVANCE = 0.25   # below this, retrieval is too weak to answer from

HANDOFF_MESSAGE = ("I could not find a confident answer to that. "
                   "Let me connect you to someone who can help.")

GROUNDED_PROMPT = """You are a banking assistant. Answer the customer's \
question using only the numbered context passages below. Each passage ends \
with its source in [brackets]; cite the sources you used. If the passages do \
not contain the answer, reply with exactly: I don't know. Never invent fees, \
rates, dates, or terms.

Context passages:
{context}

Customer question: {question}

Answer:"""


@dataclass
class Answer:
    text: str
    sources: list = field(default_factory=list)
    handed_off: bool = False


def best_score(retrieved: list) -> float:
    return max((p.relevance for p in retrieved), default=0.0)


def handoff(message: str = HANDOFF_MESSAGE) -> Answer:
    """Declining is a feature, not a failure (§4.4)."""
    return Answer(text=message, handed_off=True)


def format_with_sources(retrieved: list) -> str:
    """Each passage keeps its source, so the answer can cite it."""
    lines = []
    for i, passage in enumerate(retrieved, 1):
        lines.append(f"{i}. {passage.text}  [{passage.source}]")
    return "\n".join(lines)


def grounded_response(question: str, context: str, model=None) -> str:
    """Answer only from the context; the prompt carries the grounding rule."""
    model = model or _default_model()
    prompt = GROUNDED_PROMPT.format(context=context, question=question)
    response = model.invoke(prompt)
    return getattr(response, "content", str(response)).strip()


def answer(question: str, retrieved: list, model=None,
           min_relevance: float = None) -> Answer:
    """`min_relevance` is the decline threshold. It is a parameter rather than
    a constant read in place, because the right value depends on the embedding
    model's distance scale and has to be tuned per deployment (§4.4). Left
    unset, it comes from config, so MIN_RELEVANCE in .env actually takes
    effect."""
    if min_relevance is None:
        min_relevance = _configured_min_relevance()
    if not retrieved or best_score(retrieved) < min_relevance:
        return handoff()
    context = format_with_sources(retrieved)   # each passage keeps its source
    text = grounded_response(question, context, model=model)
    if is_non_answer(text):
        # The passages were close enough to try, but the model found no
        # answer in them. That is a decline too: the customer is offered a
        # person, and because it is handed off it is never cached (§8.16).
        return handoff()
    return Answer(text=text, sources=[p.source for p in retrieved])


def is_non_answer(text: str) -> bool:
    """True when the model said it does not know, which the prompt asks it
    to say in exactly those words."""
    start = text.strip().lower().replace("\u2019", "'")
    return start.startswith(("i don't know", "i do not know"))


class KnowledgeService:
    """Retrieval + the grounded agent, wired around one index (§8.4)."""

    def __init__(self, index, model=None, k: int = 6, min_relevance: float = None):
        self._index = index
        self._model = model
        self._k = k
        self._min_relevance = min_relevance

    def ask(self, question: str) -> Answer:
        retrieved = self._index.search(question, k=self._k)
        return answer(question, retrieved, model=self._model,
                      min_relevance=self._min_relevance)


def _configured_min_relevance() -> float:
    """Lazy, so importing this module never touches config or the network."""
    try:
        from src.config import settings
        return settings.min_relevance
    except Exception:
        return DEFAULT_MIN_RELEVANCE


def _default_model():
    from langchain_ollama import ChatOllama
    from src.config import settings
    return ChatOllama(model=settings.quality_model,
                      base_url=settings.ollama_base_url)
