"""
Ingest arXiv papers into all three vector stores (Pinecone, ChromaDB, BM25).

Usage:
    python scripts/ingest_papers.py \
        --query "retrieval augmented generation" \
        --max-results 30 \
        --categories cs.CL cs.IR

The script is idempotent: re-running with the same papers will update existing
entries rather than creating duplicates (both Pinecone and ChromaDB use upsert).
"""
import sys
import asyncio
import argparse
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ingestion.document_loader import ArxivLoader
from src.ingestion.chunker import SemanticChunker
from src.ingestion.embedder import EmbeddingService
from src.retrieval.pinecone_store import PineconeVectorStore
from src.retrieval.chroma_store import ChromaVectorStore
from src.retrieval.bm25_index import BM25Index
from src.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s — %(message)s"
)
logger = logging.getLogger(__name__)


async def run_ingestion(
    query: str,
    max_results: int,
    categories: list[str]
):
    loader   = ArxivLoader()
    chunker  = SemanticChunker(
        max_tokens=settings.chunk_size,
        min_tokens=settings.min_chunk_size,
        overlap_sentences=settings.chunk_overlap_sentences
    )
    embedder = EmbeddingService()
    pinecone = PineconeVectorStore()
    chroma   = ChromaVectorStore()
    bm25     = BM25Index()

    papers       = 0
    chunks_total = 0

    async for doc in loader.load_papers(
        query=query,
        max_results=max_results,
        categories=categories or None
    ):
        title = doc.metadata.get("title", "untitled")
        logger.info(f"Processing [{papers + 1}]: {title[:70]}")

        chunks = list(chunker.chunk_document(doc))
        if not chunks:
            logger.warning("  No usable chunks extracted — skipping")
            continue

        # Pinecone needs pre-computed embeddings
        chunk_embeddings = embedder.embed_chunks(chunks, show_progress=False)
        pinecone.upsert(chunk_embeddings)

        # ChromaDB handles its own embedding
        chroma.upsert(chunks)

        # BM25 takes raw chunks
        bm25.index_chunks(chunks)

        papers       += 1
        chunks_total += len(chunks)
        logger.info(f"  + {len(chunks)} chunks | Running total: {chunks_total}")

    logger.info(
        f"\nIngestion complete — {papers} papers, {chunks_total} chunks"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest arXiv papers")
    parser.add_argument("--query",       required=True,  help="Search query")
    parser.add_argument("--max-results", type=int,  default=20)
    parser.add_argument("--categories",  nargs="+", default=[])
    args = parser.parse_args()

    asyncio.run(run_ingestion(args.query, args.max_results, args.categories))
