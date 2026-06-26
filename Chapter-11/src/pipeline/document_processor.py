"""
Ingestion pipeline (Section 6.4).

When a document arrives it passes through a fixed sequence before it is
searchable: load (with the fallback loader), classify if needed, split into
overlapping chunks, stamp metadata on every chunk, and index into FAISS. The
splitter prefers structural break points and overlaps chunks so a sentence on a
boundary still appears whole in a neighbor.
"""
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from langchain_core.documents import Document
from langchain_core.messages import HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.config import settings
from src.loaders.advanced_document_loader import MultiFormatLoader, LoaderConfig
from src.models import get_fast_model
from src.vectorstores.faiss_store import FAISSVectorStore

logger = logging.getLogger(__name__)


class DocumentProcessor:
    def __init__(self, faiss_store: FAISSVectorStore):
        self._loader = MultiFormatLoader(LoaderConfig(
            max_pages=settings.max_pdf_pages,
            min_page_chars=settings.min_page_chars,
        ))
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=600,
            chunk_overlap=80,
            separators=["\n\n", "\n", ". ", " ", ""],   # prefer structure
            keep_separator=True,
        )
        self._faiss = faiss_store

    def process(
        self,
        file_path: str,
        doc_type: Optional[str] = None,
        doc_id: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> dict:
        doc_id = doc_id or str(uuid.uuid4())
        file_name = Path(file_path).name
        start = datetime.now(timezone.utc)
        logger.info("Processing %s (id=%s)", file_name, doc_id)

        pages = self._loader.load(file_path)
        if not pages:
            return {"error": f"No content extracted from {file_name}", "doc_id": doc_id}

        full_text = "\n\n".join(p.page_content for p in pages)
        if not doc_type:
            doc_type = self._classify_type(full_text[:1000])

        chunks = self._splitter.split_documents(pages)

        base_meta = {
            "doc_id": doc_id, "doc_type": doc_type, "filename": file_name,
            "file_path": str(file_path), "date_indexed": start.isoformat(),
            "total_pages": len(pages), "total_chunks": len(chunks),
            **(metadata or {}),
        }
        enriched = [
            Document(page_content=c.page_content,
                     metadata={**c.metadata, **base_meta, "chunk_index": i})
            for i, c in enumerate(chunks)
        ]
        indexed = self._faiss.add_documents(enriched)

        elapsed_ms = int((datetime.now(timezone.utc) - start).total_seconds() * 1000)
        logger.info("Indexed %d chunks from %s in %dms", indexed, file_name, elapsed_ms)
        return {
            "doc_id": doc_id, "doc_type": doc_type, "filename": file_name,
            "pages_loaded": len(pages), "chunks_indexed": indexed,
            "processing_ms": elapsed_ms, "full_text": full_text,
        }

    def _classify_type(self, excerpt: str) -> str:
        prompt = (
            f"Classify this document as exactly one word: legal, technical, "
            f"financial, or general.\n\nExcerpt:\n{excerpt}"
        )
        result = (get_fast_model(temperature=0) | StrOutputParser()).invoke(
            [HumanMessage(content=prompt)]
        )
        result = result.strip().lower()
        return result if result in ("legal", "technical", "financial") else "general"
