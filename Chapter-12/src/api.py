"""
The Real-Time Intelligence Monitor API.

Wires the pieces together: FireCrawl for ingestion, pgvector for memory, the
LangGraph pipeline for analysis, SSE for streaming the brief to the browser, and
the production monitor for observability. Run it with:

    uvicorn src.api:app --host 0.0.0.0 --port 8095 --reload

This module is the only trust boundary in the project. It authenticates the
caller, resolves the conversation that caller is allowed to touch, and puts the
resulting customer id into the pipeline's state. Nothing downstream re-derives
either value, and nothing downstream reads them from the request body.
"""
import re
import uuid
import asyncio
import logging
import pathlib
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from src.config import settings
from src.vectorstores.pgvector_store import make_vector_store
from src.ingestion.firecrawl_loader import FireCrawlLoader
from src.ingestion.content_monitor import ContentMonitor
from src.monitor.graph import build_intelligence_graph
from src.streaming.stream_handler import StreamingResponseHandler
from src.observability.monitoring import ProductionMonitor, MetricThresholds
from src.observability.tracing import CostTracker, log_user_feedback
from src.tenancy.auth import ApiKeyAuthenticator, Unauthenticated
from src.tenancy.conversations import make_conversation_store, ConversationAccessDenied

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

state: dict = {}          # holds the wired components after startup
topics: dict = {}         # topic_id -> config
cost_tracker = CostTracker()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Real-Time Intelligence Monitor")
    pathlib.Path("./data").mkdir(exist_ok=True)

    vectors = make_vector_store(
        kind=settings.vector_store,
        postgres_url=settings.postgres_url,
        collection=settings.vector_collection,
    )
    graph = build_intelligence_graph(vectors)
    loader = FireCrawlLoader()
    monitor = ProductionMonitor(
        project_name=settings.langsmith_project,
        thresholds=MetricThresholds(max_p95_latency_ms=15000),
    )
    state.update({
        "vectors": vectors,
        "graph": graph,
        "loader": loader,
        "handler": StreamingResponseHandler(graph),
        "content_monitor": ContentMonitor(vectors, loader),
        "prod_monitor": monitor,
        "auth": ApiKeyAuthenticator(settings.api_keys),
        "conversations": make_conversation_store(
            kind=settings.conversation_store, postgres_url=settings.postgres_url
        ),
    })
    monitor_task = asyncio.create_task(monitor.start())
    yield
    monitor.stop()
    monitor_task.cancel()
    logger.info("Intelligence Monitor shutdown complete")


app = FastAPI(title="Real-Time Intelligence Monitor", version="1.0.0", lifespan=lifespan)


async def current_customer(x_api_key: Optional[str] = Header(default=None)) -> str:
    """
    The authenticated customer id. Every route that touches customer data depends
    on this, and no route accepts a customer id as a parameter.
    """
    try:
        return state["auth"].customer_for(x_api_key)
    except Unauthenticated as exc:
        raise HTTPException(401, str(exc))


class MonitorTopicRequest(BaseModel):
    topic: str = Field(..., min_length=3, max_length=200)
    sources: list = Field(..., min_length=1, max_length=10)
    poll_minutes: int = Field(default=60, ge=5, le=1440)


class AnalyzeRequest(BaseModel):
    url: str
    topic: str
    # Optional, and never trusted: checked against the caller before it is used
    # as a thread id. Omit it to start a new conversation.
    conversation_id: Optional[str] = None


class FeedbackRequest(BaseModel):
    run_id: str
    score: float = Field(..., ge=0.0, le=1.0)
    comment: str = ""


def topic_slug(topic: str) -> str:
    """Turn a topic into a stable tag suffix: `AI regulation` -> `ai-regulation`."""
    return re.sub(r"[^a-z0-9]+", "-", topic.lower()).strip("-") or "unknown"


def run_config(conversation_id: str, customer_id: str, topic: str, url: str) -> dict:
    """
    The config every pipeline run is invoked with. `configurable` drives the
    checkpointer; the rest is what LangSmith records. `run_name` gives the trace
    a readable name instead of `LangGraph`, `tags` make runs filterable by topic
    and by customer, and `metadata` records which conversation and page produced
    the run, so a brief in the UI can always be traced back to the request that
    created it.

    The thread id is the conversation id and nothing else. It is a server minted
    uuid whose owner was checked before we got here, so there is no prefix doing
    security work and no client string anywhere in the key.
    """
    return {
        "configurable": {"thread_id": conversation_id},
        "run_name": f"intel::{topic}",
        "tags": ["chapter-12", f"topic:{topic_slug(topic)}", f"customer:{customer_id}"],
        "metadata": {
            "conversation_id": conversation_id,
            "customer_id": customer_id,
            "topic": topic,
            "content_url": url,
        },
    }


@app.post("/monitor/add")
async def add_monitor_topic(req: MonitorTopicRequest,
                            customer_id: str = Depends(current_customer)):
    topic_id = str(uuid.uuid4())
    topics[topic_id] = {**req.model_dump(), "customer_id": customer_id}
    for url in req.sources:
        state["content_monitor"].add_source(url, customer_id, label=req.topic)
    return {"topic_id": topic_id, "topic": req.topic, "status": "monitoring"}


@app.post("/analyze/stream")
async def analyze_and_stream(req: AnalyzeRequest,
                             customer_id: str = Depends(current_customer)):
    try:
        conversation_id = state["conversations"].resolve(customer_id, req.conversation_id)
    except ConversationAccessDenied as exc:
        raise HTTPException(403, str(exc))

    try:
        doc = state["loader"].scrape_page(req.url)
    except Exception as exc:
        raise HTTPException(422, f"Failed to scrape {req.url}: {exc}")

    config = run_config(conversation_id, customer_id, req.topic, req.url)
    initial = {
        "content_url": req.url,
        "content_text": doc.page_content,
        "content_title": doc.metadata.get("title", req.url),
        "topic": req.topic,
        "monitor_id": conversation_id,
        "customer_id": customer_id,
        "errors": [],
        "messages": [],
    }
    return StreamingResponse(
        state["handler"].stream(initial, config),
        media_type="text/event-stream",
        headers={"X-Conversation-Id": conversation_id},
    )


@app.post("/feedback")
async def submit_feedback(req: FeedbackRequest,
                          customer_id: str = Depends(current_customer)):
    ok = log_user_feedback(req.run_id, req.score, req.comment)
    return {"status": "feedback_recorded" if ok else "feedback_failed"}


@app.get("/metrics")
async def get_metrics(customer_id: str = Depends(current_customer)):
    m = await state["prod_monitor"].collect_metrics(window_minutes=60)
    return {
        "run_count": m.run_count,
        "error_count": m.error_count,
        "p95_latency_ms": m.p95_latency_ms,
        "cost_usd": m.estimated_cost_usd,
        "active_topics": sum(1 for t in topics.values()
                             if t["customer_id"] == customer_id),
    }


@app.get("/health")
async def health():
    """Unauthenticated on purpose, so it reveals nothing about any customer."""
    return {"status": "healthy"}
