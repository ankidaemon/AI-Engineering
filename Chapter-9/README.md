# Chapter 9 — RAG-Powered Research Assistant

A production-ready Retrieval-Augmented Generation (RAG) system that answers research questions by searching and synthesising arXiv papers. The system combines dense vector search, sparse BM25 retrieval, query expansion, semantic caching, and multi-turn conversation support.

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
| Orchestration | `src/rag_engine.py` | 8-step RAG pipeline |
| Ingestion | `src/ingestion/` | arXiv loader, semantic chunker, embedder |
| Retrieval | `src/retrieval/` | Pinecone, ChromaDB, BM25, hybrid fusion |
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
