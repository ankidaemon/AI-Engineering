# Chapter 9 — RAG-Powered Research Assistant

A production-ready Retrieval-Augmented Generation (RAG) system that answers research questions by searching and synthesising arXiv papers. The system combines dense vector search, sparse BM25 retrieval, query expansion, semantic caching, and multi-turn conversation support.

> **This README is the canonical, self-contained guide to the project.** The book
> (Chapter 9, Section II) walks through the *why* behind each design decision, but every
> instruction needed to run, understand, and extend the system lives here and in the
> docstrings of each module. You do not need the book open to use this repository.

## What This Project Is

A **Research Assistant** — a question-answering service that sits on top of a corpus of
arXiv research papers. You ask it a natural-language question
("What are the trade-offs between dense and sparse retrieval?") and it returns a grounded
answer with citations back to the exact papers it used.

It is deliberately small but **production-shaped**: it has an HTTP API, it caches, it
rate-limits, it keeps conversational state across turns, and it degrades gracefully when
a cloud dependency (Pinecone) is unavailable by falling back to a local store (ChromaDB).

**Why research papers?** They are public and freely downloadable, long enough that
"stuff everything in the prompt" fails (forcing real retrieval), and dense with factual
claims where hallucination is obvious — which keeps the focus on *groundedness*, the
whole point of RAG.

## What You'll Build & Learn (End-to-End RAG)

The codebase is organised in the order data flows through a RAG pipeline. Each stage is a
self-contained module with its own tests, so you can read it top to bottom or jump to the
stage you want to understand and swap its implementation — the tests are the contract.

| # | Stage | Module(s) | What it teaches |
|---|-------|-----------|-----------------|
| 1 | **Ingestion** | `src/ingestion/document_loader.py` | The document model; parsing; why "plain text" is rung 1 of a longer ladder |
| 2 | **Chunking & embedding** | `src/ingestion/chunker.py`, `embedder.py` | Chunk-size trade-offs; what the embedding model does (and doesn't) see |
| 3 | **Indexing** | `src/retrieval/pinecone_store.py`, `chroma_store.py`, `bm25_index.py` | The vector-store contract; why metadata lives *beside* the vector, not inside it |
| 4 | **Retrieval** | `src/retrieval/hybrid_retriever.py`, `reranker.py` | Hybrid (dense + sparse) search; RRF fusion; deduplication; cross-encoder reranking |
| 5 | **Query understanding** | `src/rag_engine.py` (query expansion) | Why the retrieval query and the user's words are not the same thing |
| 6 | **Generation** | `src/rag_engine.py`, `src/generation/` | Context construction; grounding; citation enforcement |
| 7 | **Serving & operations** | `src/api.py`, `src/cache/redis_cache.py` | API, caching, rate limiting, sessions, health checks — what separates a demo from a system |

## How to Follow Along

1. Clone this project and create a virtual environment (see **Setup** below).
2. Bring the stack up with Docker Compose and Ollama — **the defaults run entirely on your
   machine.** ChromaDB stands in for Pinecone and Llama 3.1 8B runs locally via Ollama, so
   you can complete the whole project with **no paid cloud accounts**.
3. Ingest some papers (`scripts/ingest_papers.py`), start the API, and query it.
4. To move to production-grade backends, set `PINECONE_API_KEY` in `.env` and pull
   `llama3.1:70b` — no code changes required, just configuration.

## Architecture

```
User Query
    │
    ▼
Redis Cache ──── hit ────► cached answer
    │ miss
    ▼
Query Expansion (Llama 3.1)
    │  generates 3 alternative phrasings
    ▼
Hybrid Retrieval (per query variant)
    ├── Dense:  Pinecone (sentence-transformers embeddings)
    └── Sparse: BM25 (ChromaDB fallback)
    │  RRF fusion + deduplication
    ▼
Token Budget Check (≤ 8 000 tokens of context)
    │
    ▼
Generation — Llama 3.1 via Ollama
    │
    ▼
Cache result + append session history
    │
    ▼
API Response (answer, sources, session_id)
```

## Components

| Layer | Module | Responsibility |
|-------|--------|----------------|
| API | `src/api.py` | FastAPI endpoints, rate limiting (60 req/min/IP) |
| Orchestration | `src/rag_engine.py` | 9-step RAG pipeline |
| Ingestion | `src/ingestion/` | arXiv loader, semantic chunker, embedder |
| Retrieval | `src/retrieval/` | Pinecone, ChromaDB, BM25, hybrid fusion, cross-encoder reranking |
| Generation | `src/generation/` | Llama 3.1 client, prompt builder |
| Cache | `src/cache/redis_cache.py` | Query cache (1 h TTL), session history (24 h TTL) |
| Config | `src/config.py` | Pydantic settings, `.env` support |

## Prerequisites

- Python 3.11+
- [Ollama](https://ollama.com) with `llama3.1:8b` pulled
- Docker (for Redis)
- Pinecone account (or use ChromaDB-only mode)

## Setup

```bash
# 1. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env — set PINECONE_API_KEY at minimum

# 4. Start Redis
docker-compose up -d

# 5. Pull the language model
ollama pull llama3.1:8b
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PINECONE_API_KEY` | _(required)_ | Pinecone API key |
| `PINECONE_ENVIRONMENT` | `us-east-1` | Pinecone region |
| `PINECONE_INDEX_NAME` | `research-assistant` | Index name |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `LLAMA_MODEL` | `llama3.1:8b` | Model tag |
| `REDIS_URL` | `redis://localhost:6379` | Redis connection string |
| `REDIS_CACHE_TTL` | `3600` | Query cache TTL (seconds) |
| `REDIS_SESSION_TTL` | `86400` | Session TTL (seconds) |
| `EMBEDDING_MODEL` | `sentence-transformers/all-mpnet-base-v2` | Embedding model |
| `RETRIEVAL_TOP_K` | `12` | Candidates before reranking |
| `RERANK_TOP_K` | `5` | Final chunks sent to model |
| `HYBRID_ALPHA` | `0.7` | Dense vs sparse weight (1.0 = dense only) |

## Ingesting Papers

```bash
python scripts/ingest_papers.py \
    --query "retrieval augmented generation" \
    --max-results 30 \
    --categories cs.CL cs.IR
```

The script is idempotent — re-running with the same papers will upsert, not duplicate.

## Running the API

```bash
uvicorn src.api:app --reload --port 8000
```

Interactive docs are available at `http://localhost:8000/docs`.

## API Endpoints

### `POST /query`

```json
{
  "query": "How does RAG compare to fine-tuning for knowledge-intensive tasks?",
  "session_id": "optional-uuid-for-multi-turn",
  "categories": ["cs.CL", "cs.AI"]
}
```

Response:

```json
{
  "answer": "...",
  "sources": [{"title": "...", "arxiv_id": "...", "published": "2024-01-15", "score": 0.87}],
  "session_id": "...",
  "expanded_queries": ["...", "..."],
  "cache_hit": false
}
```

### `GET /health`

Returns `"healthy"` when both Ollama and Redis are reachable, `"degraded"` otherwise.

### `DELETE /session/{session_id}`

Clears conversation history for a session.

### `POST /cache/invalidate`

Flushes all cached query results.

## Running Tests

```bash
pytest tests/ -v
```

## Configuration Defaults (Chunking & Retrieval)

- Chunk size: 512 tokens with 2-sentence overlap
- Minimum chunk size: 100 tokens
- Token budget per response: 8 000 tokens of retrieved context
- Rate limit: 60 requests per minute per IP
