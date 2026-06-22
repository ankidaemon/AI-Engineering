"""
FastAPI application — the serving layer (RAG stage 7).

Exposes the system over HTTP and applies per-IP rate limiting (60 req/min).
Endpoints:
    POST   /query                 Ask a question; returns answer + sources + session_id
    GET    /health                Readiness of Ollama and Redis
    DELETE /session/{session_id}  Clear a conversation's history
    POST   /cache/invalidate      Flush all cached query results

Note: paper ingestion is NOT an endpoint — it is a CLI batch job in
scripts/ingest_papers.py, kept out of the request path on purpose.
See the project README for the full endpoint reference.
"""
import uuid
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from src.rag_engine import RAGEngine, RAGResponse
from src.cache.redis_cache import RedisCache
from src.generation.llama_client import LlamaClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s"
)
logger = logging.getLogger(__name__)

engine: RAGEngine
cache: RedisCache


@asynccontextmanager
async def lifespan(app: FastAPI):
    global engine, cache
    logger.info("Starting Research Assistant...")
    cache  = RedisCache()
    engine = RAGEngine(use_pinecone=True, use_query_expansion=True)
    logger.info("Research Assistant ready")
    yield
    await cache.close()


app = FastAPI(
    title="Research Assistant",
    description="RAG-powered academic literature review assistant using Llama 3.1",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"]
)


class QueryRequest(BaseModel):
    query:      str = Field(..., min_length=3, max_length=2000,
                            description="The research question to answer")
    session_id: str | None = Field(
        default=None,
        description="Session ID for multi-turn conversation. "
                    "Omit for a new session."
    )
    categories: list[str] | None = Field(
        default=None,
        description="arXiv category filters e.g. ['cs.CL', 'cs.AI']"
    )


class QueryResponse(BaseModel):
    answer:           str
    sources:          list[dict]
    session_id:       str
    expanded_queries: list[str]
    cache_hit:        bool


@app.post("/query", response_model=QueryResponse)
async def query(
    body:            QueryRequest,
    request:         Request,
    x_forwarded_for: str | None = Header(default=None)
):
    client_ip = x_forwarded_for or (
        request.client.host if request.client else "unknown"
    )

    # Rate limiting
    allowed, remaining = await cache.check_rate_limit(client_ip)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Maximum 60 requests per minute."
        )

    session_id = body.session_id or str(uuid.uuid4())

    # Build optional Pinecone metadata filter
    metadata_filter: dict | None = None
    if body.categories:
        metadata_filter = {"categories": {"$in": body.categories}}

    result = await engine.query(
        query=body.query,
        session_id=session_id,
        metadata_filter=metadata_filter
    )

    return QueryResponse(
        answer=result.answer,
        sources=result.sources,
        session_id=result.session_id,
        expanded_queries=result.expanded_queries,
        cache_hit=result.cache_hit
    )


@app.get("/health")
async def health():
    llama_ok = await LlamaClient().health_check()
    redis_ok = await cache.ping()
    status   = "healthy" if (llama_ok and redis_ok) else "degraded"
    return {
        "status": status,
        "llama":  "ok" if llama_ok else "unavailable",
        "redis":  "ok" if redis_ok else "unavailable"
    }


@app.delete("/session/{session_id}")
async def clear_session(session_id: str):
    await cache._r.delete(f"session:{session_id}")
    return {"cleared": session_id}


@app.post("/cache/invalidate")
async def invalidate_cache():
    count = await cache.invalidate_all_query_cache()
    return {"invalidated_keys": count}
