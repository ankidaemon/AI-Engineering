"""
Content monitor.

Polls a set of sources on a schedule, and for each page decides whether it is
new. The decision is a content hash check: if the page's hash matches what we
saw last time, nothing has changed and we skip it. New pages are chunked,
embedded and indexed into the vector store. Deduplication is the whole point,
because re-embedding unchanged pages wastes money and pollutes retrieval with
duplicates.

Sources belong to a customer, so both halves of this class are keyed by customer:
chunks are written through that customer's scope, and the seen-hash set is keyed
by customer too. A global hash set would be a quiet cross customer bug, because
one customer indexing a public page would make it look unchanged to everybody
else, and they would never get it at all.

The vector store and the loader are both injected, so the dedup logic tests
offline with fakes.
"""
import asyncio
import logging
from typing import Optional
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.ingestion.firecrawl_loader import content_hash

logger = logging.getLogger(__name__)


class ContentMonitor:
    def __init__(self, vector_store, loader, poll_interval_seconds: int = 3600):
        self._store = vector_store
        self._loader = loader
        self._poll = poll_interval_seconds
        self._sources: dict = {}          # url -> (customer_id, label)
        self._seen_hashes: set = set()    # (customer_id, hash) already indexed
        self._splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
        self._running = False

    def add_source(self, url: str, customer_id: str, label: str = "") -> None:
        if not customer_id:
            raise ValueError("a monitored source must belong to a customer")
        self._sources[url] = (customer_id, label)

    def stop(self) -> None:
        self._running = False

    def is_new(self, document, customer_id: str) -> bool:
        """True if this customer has not indexed this page's content before."""
        h = document.metadata.get("content_hash") or content_hash(document.page_content)
        key = (customer_id, h)
        if key in self._seen_hashes:
            return False
        self._seen_hashes.add(key)
        return True

    async def _index_new_content(self, documents: list, customer_id: str) -> int:
        """Chunk and index only the documents that are genuinely new."""
        fresh = [d for d in documents if self.is_new(d, customer_id)]
        if not fresh:
            return 0
        chunks = self._splitter.split_documents(fresh)
        self._store.for_customer(customer_id).add_documents(chunks)
        logger.info("Indexed %d new chunks from %d new pages for %s",
                    len(chunks), len(fresh), customer_id)
        return len(chunks)

    async def poll_once(self) -> int:
        """Scrape every source once and index whatever is new, per customer."""
        by_customer: dict = {}
        for url, (customer_id, _label) in self._sources.items():
            try:
                by_customer.setdefault(customer_id, []).append(
                    self._loader.scrape_page(url)
                )
            except Exception as exc:
                logger.error("Scrape failed for %s: %s", url, exc)

        indexed = 0
        for customer_id, docs in by_customer.items():
            indexed += await self._index_new_content(docs, customer_id)
        return indexed

    async def run(self) -> None:
        self._running = True
        while self._running:
            try:
                await self.poll_once()
            except Exception as exc:
                logger.error("Poll cycle failed: %s", exc)
            await asyncio.sleep(self._poll)
