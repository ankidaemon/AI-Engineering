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

## Environment Setup

### 1. Python environment and dependencies

```bash
# Python 3.11 or higher is required.
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# All pinned dependencies live in requirements.txt (single source of truth).
pip install -r requirements.txt
```

### 2. Ollama (runs Llama 3.1 locally)

```bash
# Install Ollama
#   macOS:   brew install ollama
#   Linux:   curl -fsSL https://ollama.com/install.sh | sh
#   Windows: download from https://ollama.com

# Start the Ollama service (leave running in its own terminal)
ollama serve

# Pull the models (in a separate terminal)
ollama pull llama3.1:8b      # ~4.7 GB — development (the default)
ollama pull llama3.1:70b     # ~40 GB  — production quality (optional)
```

### 3. Redis (cache, sessions, rate limiting)

Redis runs via Docker Compose. The bundled `docker-compose.yml` configures it with
AOF persistence, a 1 GB `allkeys-lru` cap, and a healthcheck:

```bash
docker-compose up -d
```

### 4. Configuration

```bash
cp .env.example .env
# Edit .env — set PINECONE_API_KEY only if you want the cloud vector store.
# With the defaults the system runs fully locally (ChromaDB + Ollama).
```

## Environment Variables

All variables are read by `src/config.py` (Pydantic settings) and have working defaults;
see `.env.example` for the complete file. `PINECONE_API_KEY` is the only one you must set,
and only if you opt into the cloud vector store.

| Variable | Default | Description |
|----------|---------|-------------|
| `PINECONE_API_KEY` | _(required for cloud mode)_ | Pinecone API key; leave unset to run ChromaDB-only |
| `PINECONE_ENVIRONMENT` | `us-east-1` | Pinecone region |
| `PINECONE_INDEX_NAME` | `research-assistant` | Index name |
| `CHROMA_PERSIST_DIRECTORY` | `./data/chroma_db` | Local ChromaDB persistence path |
| `CHROMA_COLLECTION_NAME` | `research_papers` | Local ChromaDB collection |
| `REDIS_URL` | `redis://localhost:6379` | Redis connection string |
| `REDIS_CACHE_TTL` | `3600` | Query cache TTL (seconds) |
| `REDIS_SESSION_TTL` | `86400` | Session TTL (seconds) |
| `REDIS_RATE_LIMIT_RPM` | `60` | Requests per minute per IP |
| `EMBEDDING_MODEL` | `sentence-transformers/all-mpnet-base-v2` | Embedding model |
| `EMBEDDING_DIMENSION` | `768` | Embedding vector dimension (must match the model) |
| `LLAMA_MODEL` | `llama3.1:8b` | Model tag (`llama3.1:70b` for production) |
| `LLAMA_TEMPERATURE` | `0.1` | Generation temperature |
| `LLAMA_MAX_TOKENS` | `2048` | Max tokens per generated answer |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `RERANKER_MODEL` | `cross-encoder/ms-marco-MiniLM-L-6-v2` | Cross-encoder used for second-stage reranking |
| `RETRIEVAL_TOP_K` | `12` | Candidates retrieved before reranking (first-stage recall pool) |
| `RERANK_TOP_K` | `5` | Final chunks kept after reranking and sent to the model |
| `HYBRID_ALPHA` | `0.7` | Dense vs sparse weight (1.0 = dense only) |
| `CHUNK_SIZE` | `512` | Target tokens per chunk |
| `CHUNK_OVERLAP_SENTENCES` | `2` | Sentence overlap between chunks |
| `MIN_CHUNK_SIZE` | `100` | Discard chunks smaller than this |

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

## Retrieval & Reranking (Two-Stage: Recall → Precision)

Retrieval runs as a **two-stage funnel**, implemented in
`src/retrieval/hybrid_retriever.py` and `src/retrieval/reranker.py`:

1. **First stage — recall (cheap, wide).** Dense vector search (Pinecone/ChromaDB) and
   sparse BM25 each return candidates, merged with Reciprocal Rank Fusion (RRF) and
   deduplicated. RRF is a fusion of *ranks*, not a true relevance judgement, so this stage
   optimises for *not missing* relevant chunks. It returns a wide pool of `RETRIEVAL_TOP_K`
   (default **12**) candidates.
2. **Second stage — precision (expensive, narrow).** A **cross-encoder** (`RERANKER_MODEL`,
   default `cross-encoder/ms-marco-MiniLM-L-6-v2`) re-scores each `(query, chunk)` pair in a
   single forward pass — far more accurate than comparing independently-computed vectors,
   but it cannot be precomputed, so it only runs over the small first-stage pool. It keeps
   the top `RERANK_TOP_K` (default **5**) chunks to send to the model. Each surviving chunk
   gains a `rerank_score`.

**Why both stages.** The bi-encoder embeddings used for first-stage search are fast and
indexable but coarse; the cross-encoder is precise but too slow to run over the whole
corpus. Running recall first and precision second gives you most of the cross-encoder's
quality at a fraction of its cost. In practice this single addition tends to produce the
largest measurable jump in answer quality of any component in the pipeline.

**Tuning and toggling.**
- Keep the recall pool modest (20–50) and the final set small (3–8): a cross-encoder adds
  latency proportional to `RETRIEVAL_TOP_K` (reranking 30 candidates ≈ 30 short forward passes).
- For higher quality at greater cost, set `RERANKER_MODEL=BAAI/bge-reranker-large`.
- Reranking can be disabled by constructing the engine with `use_reranker=False`
  (see `src/rag_engine.py`); the pipeline then falls back to RRF order.

## Running Tests

```bash
pytest tests/ -v
```

Reranking behaviour is covered by `tests/test_reranker.py` (ordering, truncation to
`top_k`, pair construction, and the empty-candidates case).

## Configuration Defaults (Chunking & Retrieval)

- Chunk size: 512 tokens with 2-sentence overlap
- Minimum chunk size: 100 tokens
- Token budget per response: 8 000 tokens of retrieved context
- Rate limit: 60 requests per minute per IP
