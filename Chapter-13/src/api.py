"""
The API: a thin door (§8.11).

Endpoints validate input, call into the services built at startup, and shape
the response — all the intelligence lives behind them. The health check does
real work: it pings the model server, Redis, and the Celery workers, and
reports "degraded" when any of them is unreachable, so a broken dependency
is noticed before customers feel it. `summarize_health` is a pure function
so that logic is testable offline.

Ingestion endpoints only ENQUEUE — the slow work happens in a worker
(§7.3), and so does remembering: the assistant's `remember` seam is wired
to a Celery task here, so Mem0's extraction never runs on the request path.

This process also serves the chat window in `web/` as static files, so the
whole assistant is one thing to start and http://localhost:8100/ is a
working front door rather than a curl command.
"""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from src.config import settings


class ChatRequest(BaseModel):
    customer_id: str
    message: str
    history: list = []
    confirmed: bool = False


class IngestRequest(BaseModel):
    doc_ids: list


def summarize_health(components: dict) -> str:
    """healthy when everything answers, degraded otherwise — never a lie."""
    return "healthy" if all(components.values()) else "degraded"


def _build_assistant():
    """Real wiring, built once at startup. Everything the tests use is
    injected elsewhere; this is the production composition root."""
    from langchain_ollama import OllamaEmbeddings
    import redis as redis_lib
    from src.assistant import Assistant
    from src.cache.semantic_cache import RedisBackend, SemanticCache
    from src.knowledge.agent import KnowledgeService
    from src.memory.service import MemoryService
    from src.products.advisor import Customer, ProductAdvisor
    from src.products.catalog import DEFAULT_CATALOG, build_product_index
    from src.router import Router
    from src.tools.action_agent import ActionAgent
    from src.tools.idempotency import IdempotencyStore
    from src.tools.pending import PendingActions
    from src.tools.read_tools import READ_TOOLS
    from src.tools.selector import build_tool_index
    from src.tools.service_desk import ServiceDesk
    from src.tools.write_tools import WRITE_TOOLS
    from src.vectorstores.faiss_store import KnowledgeIndex

    embeddings = OllamaEmbeddings(model=settings.embedding_model,
                                  base_url=settings.ollama_base_url)
    redis_client = redis_lib.from_url(settings.redis_url)

    knowledge = KnowledgeService(
        KnowledgeIndex(persist_dir=settings.faiss_persist_dir,
                       embeddings=embeddings),
        k=settings.retrieval_k,
        min_relevance=settings.min_relevance,
    )
    advisor = ProductAdvisor(build_product_index(DEFAULT_CATALOG, embeddings))
    actions = ActionAgent(
        build_tool_index(READ_TOOLS + WRITE_TOOLS, embeddings),
        desk=ServiceDesk(),
        idem_store=IdempotencyStore(redis_client),
        top_k=settings.tool_top_k,
        pending=PendingActions(redis_client),
    )
    cache = SemanticCache(embeddings, backend=RedisBackend(redis_client),
                          threshold=settings.cache_similarity_threshold,
                          ttl_seconds=settings.cache_ttl_seconds)
    router = Router(embeddings,
                    min_score=settings.router_min_score,
                    min_margin=settings.router_min_margin)
    memory = MemoryService(recall_k=settings.memory_recall_k)

    def remember_in_background(customer_id, message, reply_text):
        from src.workers.tasks import remember_exchange
        remember_exchange.delay(customer_id, message, reply_text)

    # Demo customer lookup; in production this is the bank's customer system.
    demo = Customer(customer_id="demo", income=50000,
                    holdings=["everyday-savings"], profile_notes="")
    return Assistant(knowledge, advisor, actions, router, cache=cache,
                     get_customer=lambda cid: demo,
                     memory=memory, remember=remember_in_background)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.assistant = _build_assistant()
    yield


app = FastAPI(title="Multi-Agent Banking Assistant", lifespan=lifespan)


@app.post("/chat")
def chat(req: ChatRequest):
    reply = app.state.assistant.handle(
        req.customer_id, req.message, history=req.history,
        confirmed=req.confirmed)
    return {
        "kind": reply.kind, "text": reply.text, "reference": reply.reference,
        "needs_confirmation": reply.needs_confirmation,
        "sources": reply.sources, "from_cache": reply.from_cache,
    }


@app.post("/ingest")
def ingest(req: IngestRequest):
    from src.workers.tasks import ingest_batch
    ingest_batch.delay(req.doc_ids)          # enqueue only; workers do the work
    return {"queued": len(req.doc_ids)}


@app.get("/health")
def health():
    components = {
        "model_server": _ping_ollama(),
        "redis": _ping_redis(),
        "workers": _ping_workers(),
    }
    return {"status": summarize_health(components), "components": components}


# The chat window. Mounted last, so /chat, /ingest and /health are matched
# before the catch-all, and served by the same process as the API so a reader
# needs no second server, no build step and no node installed.
_WEB_DIR = Path(__file__).resolve().parent.parent / "web"
if _WEB_DIR.is_dir():
    app.mount("/", StaticFiles(directory=_WEB_DIR, html=True), name="web")


def _ping_ollama() -> bool:
    try:
        import httpx
        response = httpx.get(f"{settings.ollama_base_url}/api/tags", timeout=2)
        return response.status_code == 200
    except Exception:
        return False


def _ping_redis() -> bool:
    try:
        import redis as redis_lib
        return bool(redis_lib.from_url(settings.redis_url,
                                       socket_connect_timeout=2).ping())
    except Exception:
        return False


def _ping_workers() -> bool:
    try:
        from src.workers.celery_app import app as celery_app
        replies = celery_app.control.ping(timeout=1)
        return bool(replies)
    except Exception:
        return False
