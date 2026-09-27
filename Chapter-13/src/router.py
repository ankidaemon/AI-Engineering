"""
The router: intent retrieval, no model call (§3.3, §8.7).

The earlier multi-agent chapter's retrieval-based tool routing eliminated the
model call from dispatch by embedding descriptions and retrieving the match.
The router applies the same idea one level up: a handful of exemplar
utterances per route are embedded once at startup, and routing a message is
one vector search for the nearest exemplar. Zero model calls to decide,
at both altitudes — here for the route, and again in the tool selector.

Two fail-safes, both pure code and both falling toward the harmless path,
because answering is safe and acting is not:
  * a weak best match (the message resembles no exemplar) routes to "question"
  * a close call between routes (top two routes nearly tied) routes to "question"

Adding a route, or sharpening one, means editing the exemplar list — no
retraining, no prompt change, no redeploy of anything but a text edit.
An LLM classifier remains a reasonable day-one stand-in before any exemplar
utterances exist; this replaces it the moment you can write ten of them.
"""
from src.vectorstores.cosine_index import CosineIndex

ROUTES = ("question", "advice", "action")

# Exemplar utterances, written the way customers actually type. These are the
# router's entire knowledge; keep them short, concrete, and per-route.
ROUTE_EXEMPLARS = {
    "question": [
        "what is the late payment fee",
        "what is the interest free period on the card",
        "how do I report a lost or stolen card",
        "why was I charged this fee",
        "how long does a cheque book take to arrive",
        "what are the terms for disputing a transaction",
    ],
    "advice": [
        "which credit card is best for me",
        "which card suits someone who travels often",
        "recommend a product for my needs",
        "what account should I open",
        "is there an offer that fits me",
        "help me choose between these cards",
    ],
    "action": [
        "block my card right now",
        "my card was stolen freeze it",
        "raise a complaint about this charge",
        "book a call back from an agent",
        "order a new cheque book for my account",
        "send me a replacement card",
        "check the status of my request",
    ],
}


class Router:
    def __init__(self, embeddings, exemplars: dict = None,
                 min_score: float = 0.2, min_margin: float = 0.05):
        self._exemplars = exemplars or ROUTE_EXEMPLARS
        self._min_score = min_score
        self._min_margin = min_margin
        self._index = CosineIndex(embeddings)
        items = [(utterance, route_name)
                 for route_name, utterances in self._exemplars.items()
                 for utterance in utterances]
        self._index.add(items)
        self._total = len(items)

    def route(self, message: str) -> str:
        hits = self._index.top_k(message, k=self._total)
        if not hits:
            return "question"

        # Best score per route (hits arrive sorted best-first, so the first
        # time a route appears is its best exemplar).
        best_per_route: dict = {}
        for route_name, score in hits:
            best_per_route.setdefault(route_name, score)
        ranked = sorted(best_per_route.items(), key=lambda kv: kv[1],
                        reverse=True)

        top_route, top_score = ranked[0]
        if top_score < self._min_score:
            return "question"            # resembles no exemplar: answer, do not act
        if (top_route != "question" and len(ranked) > 1
                and top_score - ranked[1][1] < self._min_margin):
            return "question"            # too close to call: answer, do not act
        return top_route
