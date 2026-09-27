"""
A tiny in-memory cosine-similarity index.

The product catalog (§5.2), the tool selector (§6.4), and the semantic cache
(§7.4) all need the same small thing: embed a handful of descriptions once,
then find the closest ones to a query. A full vector database is overkill for
a few hundred items that fit in memory, so this module provides the minimal
version. The large corpus (FAQs and policy) lives in FAISS instead — see
`faiss_store.py`.

The embeddings object is injected, so tests run with a deterministic fake and
production runs with Ollama embeddings. It only needs two methods,
`embed_documents(texts)` and `embed_query(text)`, the standard interface.
"""
import math


def cosine(a: list, b: list) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


class CosineIndex:
    """Embed (text, payload) pairs once; retrieve payloads nearest a query."""

    def __init__(self, embeddings):
        self._embeddings = embeddings
        self._vectors: list = []
        self._payloads: list = []

    def add(self, items: list) -> int:
        """items: list of (text, payload) pairs."""
        if not items:
            return 0
        texts = [text for text, _ in items]
        self._vectors.extend(self._embeddings.embed_documents(texts))
        self._payloads.extend(payload for _, payload in items)
        return len(items)

    def top_k(self, query: str, k: int = 4) -> list:
        """Returns [(payload, score)] sorted best-first."""
        if not self._vectors:
            return []
        q = self._embeddings.embed_query(query)
        scored = [(payload, cosine(q, vec))
                  for payload, vec in zip(self._payloads, self._vectors)]
        scored.sort(key=lambda pair: pair[1], reverse=True)
        return scored[:k]
