import logging
from sentence_transformers import SentenceTransformer
from src.config import settings
from src.ingestion.chunker import Chunk

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Wraps sentence-transformers for batch and single-item embedding.

    All embeddings are L2-normalized. This makes dot-product equivalent
    to cosine similarity, which is required for Pinecone's dotproduct
    metric and produces consistent results across stores.
    """

    def __init__(self):
        device = self._best_device()
        logger.info(f"Loading '{settings.embedding_model}' on {device}")
        self._model = SentenceTransformer(
            settings.embedding_model,
            device=device
        )

    def embed_chunks(
        self,
        chunks: list[Chunk],
        batch_size: int = 64,
        show_progress: bool = False
    ) -> list[tuple[Chunk, list[float]]]:
        texts = [c.content for c in chunks]
        vectors = self._model.encode(
            texts,
            batch_size=batch_size,
            normalize_embeddings=True,
            show_progress_bar=show_progress or len(texts) > 200
        )
        return list(zip(chunks, vectors.tolist()))

    def embed_query(self, query: str) -> list[float]:
        vec = self._model.encode([query], normalize_embeddings=True)
        return vec[0].tolist()

    def _best_device(self) -> str:
        try:
            import torch
            if torch.cuda.is_available():
                return "cuda"
            if torch.backends.mps.is_available():
                return "mps"
        except ImportError:
            pass
        return "cpu"
