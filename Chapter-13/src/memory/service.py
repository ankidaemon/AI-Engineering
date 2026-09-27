"""
Long-term memory: a thin seam over Mem0 (§2, §8.8).

Mem0 does two jobs on every write. A fast model EXTRACTS candidate facts
from the exchange, and each candidate is then RECONCILED against the
memories already stored — added if new, revised if it refines or
contradicts one, dropped if already known — so the store stays small and
current instead of accumulating transcripts (§2.3). Reading is only a
vector search, which is why recall is the one part of memory the request
path is allowed to pay for (§2.5).

The wrapper enforces the two rules the chapter insists on. The customer id
is a hard namespace stamped onto every call inside this class, and the Mem0
client itself is private, so there is no path to the store that skips it and one customer's memories can never
inform another's answer (Failure 7). And the production client is built
lazily, configured for local models through Ollama and an on-disk FAISS
store, so memories — personal data by definition — never leave the
machine (§2.4). Tests inject a fake client and never import mem0.
"""


class MemoryService:
    def __init__(self, client=None, recall_k: int = 3):
        self._client = client
        self._recall_k = recall_k

    @property
    def _store(self):
        """Private on purpose. The namespace rule below is only worth
        anything if there is no way to reach Mem0 around it, so the raw
        client is not part of this class's surface. Injection stays open
        through the constructor, which is how the tests supply a fake."""
        if self._client is None:
            self._client = _default_client()
        return self._client

    def remember(self, customer_id: str, message: str, reply: str) -> None:
        """Hand the finished exchange to Mem0; extraction decides what, if
        anything, is worth keeping. This costs a model call, so production
        runs it in a worker (§7.3), never while the customer waits."""
        self._store.add(
            [{"role": "user", "content": message},
             {"role": "assistant", "content": reply}],
            user_id=customer_id,
        )

    def recall(self, customer_id: str, query: str) -> list:
        """The few stored facts most relevant to this query, for this
        customer only. An embed and a vector search: no generative call,
        so recall cannot invent a memory that was never stored."""
        found = self._store.search(query, top_k=self._recall_k,
                                   filters={"user_id": customer_id})
        rows = found.get("results", []) if isinstance(found, dict) else found
        return [row["memory"] for row in rows]

    def forget(self, customer_id: str) -> None:
        """Erasure on request is a feature, not an afterthought (§2.5)."""
        self._store.delete_all(user_id=customer_id)


def _default_client():
    """Everything in-house: Ollama for extraction and embedding, an on-disk
    FAISS store for the memories themselves (§2.4)."""
    from mem0 import Memory

    from src.config import settings
    return Memory.from_config({
        "llm": {"provider": "ollama",
                "config": {"model": settings.fast_model,
                           "ollama_base_url": settings.ollama_base_url}},
        "embedder": {"provider": "ollama",
                     "config": {"model": settings.embedding_model,
                                "ollama_base_url": settings.ollama_base_url}},
        "vector_store": {"provider": "faiss",
                         "config": {"path": settings.memory_dir,
                                    "collection_name": "customer_memory",
                                    "embedding_model_dims": 768}},
    })
