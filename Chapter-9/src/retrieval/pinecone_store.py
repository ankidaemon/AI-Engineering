import logging
from pinecone import Pinecone, ServerlessSpec
from src.config import settings
from src.ingestion.chunker import Chunk

logger = logging.getLogger(__name__)


class PineconeVectorStore:
    """
    Manages a Pinecone serverless index for production vector retrieval.

    Index uses dotproduct metric because embeddings are L2-normalized —
    dotproduct on unit vectors equals cosine similarity but Pinecone's
    infrastructure computes it faster than the cosine variant.

    IMPORTANT: Tenant isolation uses namespaces, not metadata filters.
    Metadata filters are applied post-ANN search and are NOT a security
    boundary for separating different users' documents.
    """

    UPSERT_BATCH_SIZE = 100

    def __init__(self):
        self._pc = Pinecone(api_key=settings.pinecone_api_key)
        self._index = self._get_or_create_index()

    def _get_or_create_index(self):
        existing = [idx.name for idx in self._pc.list_indexes()]
        if settings.pinecone_index_name not in existing:
            logger.info(f"Creating index '{settings.pinecone_index_name}'")
            self._pc.create_index(
                name=settings.pinecone_index_name,
                dimension=settings.embedding_dimension,
                metric="dotproduct",
                spec=ServerlessSpec(
                    cloud="aws",
                    region=settings.pinecone_environment
                )
            )
        return self._pc.Index(settings.pinecone_index_name)

    def upsert(
        self,
        chunk_embeddings: list[tuple[Chunk, list[float]]],
        namespace: str = "papers"
    ) -> int:
        """
        Upsert chunks in batches of 100 (Pinecone's recommended batch size).
        Larger batches increase the risk of hitting the 2MB request size limit.
        """
        vectors = [
            {
                "id": chunk.chunk_id,
                "values": embedding,
                "metadata": {
                    # Pinecone metadata is limited to 40KB per vector.
                    # Truncate content to 3000 characters to stay safe.
                    "content":     chunk.content[:3000],
                    "doc_id":      chunk.doc_id,
                    "chunk_index": chunk.chunk_index,
                    "title":       str(chunk.metadata.get("title", ""))[:500],
                    "section":     str(chunk.metadata.get("section", "")),
                    "published":   str(chunk.metadata.get("published", ""))[:10],
                    "arxiv_id":    str(chunk.metadata.get("arxiv_id", "")),
                    "authors":     ", ".join(
                        chunk.metadata.get("authors", [])[:5]
                    )[:400],
                    "source":      str(chunk.metadata.get("source", ""))
                }
            }
            for chunk, embedding in chunk_embeddings
        ]

        total = 0
        for i in range(0, len(vectors), self.UPSERT_BATCH_SIZE):
            batch = vectors[i: i + self.UPSERT_BATCH_SIZE]
            response = self._index.upsert(vectors=batch, namespace=namespace)
            total += response.upserted_count

        logger.info(f"Pinecone: upserted {total} vectors to namespace '{namespace}'")
        return total

    def query(
        self,
        embedding: list[float],
        top_k: int = 10,
        namespace: str = "papers",
        metadata_filter: dict | None = None
    ) -> list[dict]:
        params = {
            "vector":           embedding,
            "top_k":            top_k,
            "include_metadata": True,
            "namespace":        namespace
        }
        if metadata_filter:
            params["filter"] = metadata_filter

        response = self._index.query(**params)
        return [
            {
                "chunk_id": m.id,
                "score":    float(m.score),
                "content":  m.metadata.get("content", ""),
                "metadata": dict(m.metadata)
            }
            for m in response.matches
        ]

    def delete_document(self, doc_id: str, namespace: str = "papers"):
        """Remove all chunks belonging to a document."""
        self._index.delete(
            filter={"doc_id": {"$eq": doc_id}},
            namespace=namespace
        )

    def stats(self) -> dict:
        return self._index.describe_index_stats().to_dict()
