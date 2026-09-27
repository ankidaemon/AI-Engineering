"""
Background tasks: the slow work, off the request path (§7.3, §7.5).

The rule: if a piece of work does not have to finish before you can answer
the customer, it does not run while the customer waits. Re-indexing a
changed document and ingesting a batch both go here.

Each task is a thin Celery wrapper around a plain function that takes its
dependencies as arguments, so the logic is tested by calling the function
directly — no broker, no worker, no network. Batch ingestion fans out into
one small job per document (§7.5): the work spreads across workers, one
document's failure retries alone, and the queue paces the load instead of
letting it arrive as a spike (Failure 6).
"""
from src.workers.celery_app import app


# ── The plain functions (tested directly) ────────────────────────────

def reindex_document_impl(doc_id: str, pipeline) -> dict:
    doc = pipeline.load_document(doc_id)        # slow: fetch and parse
    chunks = pipeline.split_and_embed(doc)      # slow: split; embeds on entry
    pipeline.index.replace(doc_id, chunks)      # swap old chunks for new
    return {"doc_id": doc_id, "chunks": len(chunks)}


def ingest_batch_impl(doc_ids: list, enqueue) -> dict:
    """One small job per document, not one giant job (§7.5)."""
    for doc_id in doc_ids:
        enqueue(doc_id)
    return {"queued": len(doc_ids)}


def ingest_web_page_impl(url: str, doc_id: str, pipeline, fetch) -> dict:
    """Index a public page the bank does not own the file for (§8.10).

    The only difference from `reindex_document_impl` is where the text comes
    from: a scrape through somebody else's MCP server instead of a file on
    disk. Everything after that is the same pipeline, because `fetch` returns
    Documents in the same metadata shape every other loader produces.
    """
    docs = fetch(url, doc_id)                   # slow: a network round trip
    chunks = pipeline.split_and_embed(docs)
    pipeline.index.replace(doc_id, chunks)
    return {"doc_id": doc_id, "url": url, "chunks": len(chunks)}


def remember_exchange_impl(customer_id: str, message: str, reply: str,
                           memory) -> dict:
    """Feed a finished exchange to the memory layer (§2.5, §8.8). Mem0's
    extraction spends a fast model call, which is exactly why this runs in
    a worker after the reply has already gone out, never on the request
    path."""
    memory.remember(customer_id, message, reply)
    return {"customer_id": customer_id, "remembered": True}


# ── The Celery tasks (thin wrappers) ─────────────────────────────────

@app.task
def reindex_document(doc_id: str) -> dict:
    return reindex_document_impl(doc_id, _default_pipeline())


@app.task
def ingest_batch(doc_ids: list) -> dict:
    return ingest_batch_impl(doc_ids, enqueue=lambda d: reindex_document.delay(d))


@app.task
def ingest_web_page(url: str, doc_id: str) -> dict:
    from src.mcp_client import fetch_page
    return ingest_web_page_impl(url, doc_id, _default_pipeline(), fetch=fetch_page)


@app.task
def remember_exchange(customer_id: str, message: str, reply: str) -> dict:
    return remember_exchange_impl(customer_id, message, reply,
                                  _default_memory())


def _default_pipeline():
    """Built lazily so importing this module never touches the network."""
    from src.config import settings
    from src.knowledge.ingest import IngestionPipeline
    from src.vectorstores.faiss_store import KnowledgeIndex
    index = KnowledgeIndex(persist_dir=settings.faiss_persist_dir)
    return IngestionPipeline(index)


def _default_memory():
    """Lazy for the same reason: importing this module stays free."""
    from src.config import settings
    from src.memory.service import MemoryService
    return MemoryService(recall_k=settings.memory_recall_k)
