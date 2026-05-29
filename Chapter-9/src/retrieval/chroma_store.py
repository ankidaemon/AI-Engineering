import logging
import chromadb
from chromadb.config import Settings as ChromaSettings
from chromadb.utils import embedding_functions
from src.config import settings
from src.ingestion.chunker import Chunk

logger = logging.getLogger(__name__)


class ChromaVectorStore:
    """
    Persistent ChromaDB collection with HNSW indexing.

    HNSW parameters explained:
    - hnsw:M (default 16, set to 32): number of bidirectional links per node.
      Higher M improves recall at the cost of more memory and slower indexing.
      32 is a good balance for academic text retrieval.
    - hnsw:construction_ef (default 100, set to 200): candidate list size during
      index construction. Higher = better index quality, slower to build.
    - hnsw:search_ef (default 10, set to 100): candidate list during query.
      Higher = better recall, slower queries. 100 is the ChromaDB recommendation
      for production quality.
    """

    def __init__(self, ephemeral: bool = False):
        if ephemeral:
            self._client = chromadb.EphemeralClient()
        else:
            self._client = chromadb.PersistentClient(
                path=settings.chroma_persist_directory,
                settings=ChromaSettings(anonymized_telemetry=False)
            )

        self._embedding_fn = (
            embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name=settings.embedding_model,
                normalize_embeddings=True
            )
        )
        self._collection = self._init_collection()

    def _init_collection(self):
        return self._client.get_or_create_collection(
            name=settings.chroma_collection_name,
            embedding_function=self._embedding_fn,
            metadata={
                "hnsw:space":           "cosine",
                "hnsw:M":               32,
                "hnsw:construction_ef": 200,
                "hnsw:search_ef":       100
            }
        )

    def upsert(self, chunks: list[Chunk]) -> int:
        """
        ChromaDB computes embeddings internally when an embedding_function
        is attached to the collection. This means you pass raw text rather
        than pre-computed vectors — simpler ingestion code, at the cost of
        not being able to share pre-computed embeddings between ChromaDB
        and Pinecone. For the dev workflow in this chapter, the simplicity
        is worth it.
        """
        if not chunks:
            return 0

        self._collection.upsert(
            ids=[c.chunk_id for c in chunks],
            documents=[c.content for c in chunks],
            metadatas=[
                {
                    "doc_id":      c.doc_id,
                    "chunk_index": c.chunk_index,
                    "title":       str(c.metadata.get("title", ""))[:500],
                    "section":     str(c.metadata.get("section", "")),
                    "published":   str(c.metadata.get("published", ""))[:10],
                    "arxiv_id":    str(c.metadata.get("arxiv_id", "")),
                    "source":      str(c.metadata.get("source", ""))
                }
                for c in chunks
            ]
        )
        logger.info(f"ChromaDB: upserted {len(chunks)} chunks")
        return len(chunks)

    def query(
        self,
        query_text: str,
        top_k: int = 10,
        where: dict | None = None
    ) -> list[dict]:
        count = self._collection.count()
        if count == 0:
            return []

        n = min(top_k, count)
        params: dict = {
            "query_texts": [query_text],
            "n_results":   n,
            "include":     ["documents", "metadatas", "distances"]
        }
        if where:
            params["where"] = where

        result = self._collection.query(**params)

        return [
            {
                "chunk_id": f"{m.get('doc_id', '')}_{m.get('chunk_index', 0)}",
                "content":  doc,
                "metadata": m,
                # ChromaDB returns squared L2 distance for cosine space.
                # Convert to a [0, 1] similarity score.
                "score":    max(0.0, 1.0 - dist)
            }
            for doc, m, dist in zip(
                result["documents"][0],
                result["metadatas"][0],
                result["distances"][0]
            )
        ]

    def count(self) -> int:
        return self._collection.count()

    def reset_collection(self):
        """Wipe and recreate the collection. Useful during development."""
        self._client.delete_collection(settings.chroma_collection_name)
        self._collection = self._init_collection()
        logger.info("ChromaDB collection reset")
