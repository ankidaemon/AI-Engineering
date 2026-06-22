"""
Hybrid retrieval (RAG stage 4) — combines dense and sparse search.

Runs dense vector search (Pinecone, or ChromaDB as a local fallback) alongside
sparse BM25 keyword search, merges the two ranked lists with Reciprocal Rank
Fusion (RRF), and deduplicates. The HYBRID_ALPHA setting weights dense vs.
sparse. Results are handed to the cross-encoder reranker (see reranker.py)
before generation. See the project README ("What You'll Build & Learn").
"""
import logging
from src.retrieval.pinecone_store import PineconeVectorStore
from src.retrieval.chroma_store import ChromaVectorStore
from src.retrieval.bm25_index import BM25Index
from src.ingestion.embedder import EmbeddingService
from src.config import settings

logger = logging.getLogger(__name__)


class HybridRetriever:
    """
    Combines dense vector retrieval with BM25 sparse retrieval,
    merging results via Reciprocal Rank Fusion.

    Fails over from Pinecone to ChromaDB automatically so that
    local development and cloud production use identical code paths.
    The alpha parameter controls the balance:
        alpha = 1.0  ->  pure dense retrieval
        alpha = 0.0  ->  pure BM25
        alpha = 0.7  ->  70% dense weight (recommended default)
    """

    RRF_K = 60  # Smoothing constant (Cormack et al., 2009)

    def __init__(
        self,
        use_pinecone: bool = True,
        alpha: float | None = None
    ):
        self._alpha = alpha if alpha is not None else settings.hybrid_alpha
        self._embedder = EmbeddingService()
        self._bm25 = BM25Index()
        self._vector_store = self._init_vector_store(use_pinecone)

    def _init_vector_store(self, use_pinecone: bool):
        if use_pinecone:
            try:
                store = PineconeVectorStore()
                logger.info("Using Pinecone as primary vector store")
                return store
            except Exception as exc:
                logger.warning(
                    f"Pinecone unavailable ({exc}), falling back to ChromaDB"
                )
        logger.info("Using ChromaDB as primary vector store")
        return ChromaVectorStore()

    def retrieve(
        self,
        query: str,
        top_k: int | None = None,
        metadata_filter: dict | None = None
    ) -> list[dict]:
        k = top_k or settings.retrieval_top_k

        # Dense retrieval
        query_embedding = self._embedder.embed_query(query)
        if isinstance(self._vector_store, PineconeVectorStore):
            dense = self._vector_store.query(
                embedding=query_embedding,
                top_k=k,
                metadata_filter=metadata_filter
            )
        else:
            dense = self._vector_store.query(query_text=query, top_k=k)

        # Sparse retrieval
        sparse = self._bm25.query(query_text=query, top_k=k)

        # Merge with RRF. Return the wider candidate pool (retrieval_top_k),
        # not the final rerank_top_k — the cross-encoder reranker downstream
        # needs enough candidates to have a real choice. When reranking is
        # disabled, the RAG engine trims this pool by RRF order instead.
        merged = self._rrf_merge(dense, sparse)
        return merged[:settings.retrieval_top_k]

    def _rrf_merge(
        self,
        dense: list[dict],
        sparse: list[dict]
    ) -> list[dict]:
        scores: dict[str, float] = {}
        result_map: dict[str, dict] = {}

        for rank, doc in enumerate(dense, start=1):
            key = doc.get("chunk_id") or doc["content"][:64]
            result_map[key] = doc
            scores[key] = scores.get(key, 0.0) + \
                self._alpha / (self.RRF_K + rank)

        for rank, doc in enumerate(sparse, start=1):
            key = doc.get("chunk_id") or doc["content"][:64]
            result_map.setdefault(key, doc)
            scores[key] = scores.get(key, 0.0) + \
                (1 - self._alpha) / (self.RRF_K + rank)

        ranked = sorted(scores.keys(), key=lambda k: scores[k], reverse=True)
        return [
            {**result_map[k], "rrf_score": scores[k]}
            for k in ranked
        ]
