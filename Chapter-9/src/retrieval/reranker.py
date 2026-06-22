"""
Cross-encoder reranking (RAG stage 4, second stage).

The hybrid retriever returns RETRIEVAL_TOP_K cheap candidates; this module
re-scores each (query, chunk) pair with a cross-encoder — slower but far more
accurate than the bi-encoder embeddings used for first-stage recall — and keeps
the top RERANK_TOP_K to send to the model. This is the precision step that
follows the recall step. See the project README ("What You'll Build & Learn").
"""
import logging
from sentence_transformers import CrossEncoder
from src.config import settings

logger = logging.getLogger(__name__)


class CrossEncoderReranker:
    """
    Second-stage reranker using a cross-encoder.

    Unlike the bi-encoder used for first-stage retrieval, a cross-encoder
    scores a (query, passage) PAIR in a single forward pass, letting every
    query token attend to every passage token. This is far more accurate
    than comparing independently-computed vectors, but it cannot be
    precomputed — so we only run it over the handful of candidates that
    survived first-stage retrieval.

    Model note: 'cross-encoder/ms-marco-MiniLM-L-6-v2' is a strong,
    lightweight default trained on the MS MARCO passage ranking task.
    For higher quality at greater cost, swap in 'BAAI/bge-reranker-large'.
    """

    def __init__(self, model_name: str | None = None):
        name = model_name or settings.reranker_model
        logger.info(f"Loading cross-encoder reranker '{name}'")
        self._model = CrossEncoder(name, max_length=512)

    def rerank(
        self,
        query: str,
        candidates: list[dict],
        top_k: int | None = None
    ) -> list[dict]:
        """
        Re-score candidates against the query and return the top_k by
        relevance. Each returned chunk gains a 'rerank_score' field.
        """
        if not candidates:
            return []

        pairs = [(query, c["content"]) for c in candidates]
        scores = self._model.predict(pairs)

        for candidate, score in zip(candidates, scores):
            candidate["rerank_score"] = float(score)

        ranked = sorted(
            candidates,
            key=lambda c: c["rerank_score"],
            reverse=True
        )
        k = top_k or settings.rerank_top_k
        return ranked[:k]
