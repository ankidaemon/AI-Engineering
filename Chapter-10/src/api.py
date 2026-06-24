"""
FastAPI interface for the AI Workflow Designer.

Endpoints
    POST /analyze                  submit a document; returns the report or
                                   status="awaiting_review" if it paused
    POST /review                   submit a human decision and resume
    POST /ask                      ask a follow-up question about the report
    GET  /session/{id}/state       inspect a session's workflow state
    GET  /health                   liveness + Ollama reachability

Sessions are held in an in-process dict keyed by session_id. The LangGraph
checkpointer is the durable store; this dict just maps a session to its
WorkflowConversation wrapper for the lifetime of the process.
"""
import uuid
import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from src.conversation import WorkflowConversation
from src.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

sessions: dict[str, WorkflowConversation] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("AI Workflow Designer starting...")
    yield
    logger.info("AI Workflow Designer shutdown")


app = FastAPI(
    title="AI Workflow Designer",
    description="Document analysis and decision support using LangChain and LangGraph",
    version="1.0.0",
    lifespan=lifespan,
)


class AnalyzeRequest(BaseModel):
    document_text: str = Field(..., min_length=50)
    document_id:   str = Field(default="DOC-001")
    session_id:    str | None = None


class ReviewRequest(BaseModel):
    session_id: str
    decision:   str = Field(..., pattern="^(approved|needs_revision)$")
    feedback:   str = ""


class QuestionRequest(BaseModel):
    session_id: str
    question:   str = Field(..., min_length=3)


@app.post("/analyze")
async def analyze_document(req: AnalyzeRequest):
    session_id = req.session_id or str(uuid.uuid4())
    if session_id not in sessions:
        sessions[session_id] = WorkflowConversation()

    result = sessions[session_id].analyze_document(
        document_text=req.document_text,
        document_id=req.document_id,
    )
    return {**result, "session_id": session_id}


@app.post("/review")
async def submit_review(req: ReviewRequest):
    if req.session_id not in sessions:
        raise HTTPException(404, "Session not found")
    return sessions[req.session_id].submit_human_review(
        decision=req.decision,
        feedback=req.feedback,
    )


@app.post("/ask")
async def ask_question(req: QuestionRequest):
    if req.session_id not in sessions:
        raise HTTPException(404, "Session not found. Analyze a document first.")
    answer = sessions[req.session_id].ask(req.question)
    return {"answer": answer, "session_id": req.session_id}


@app.get("/session/{session_id}/state")
async def get_session_state(session_id: str):
    if session_id not in sessions:
        raise HTTPException(404, "Session not found")
    from src.graph import workflow_app
    config = {"configurable": {"thread_id": session_id}}
    state = workflow_app.get_state(config)
    return {
        "current_step":    state.values.get("current_step"),
        "risk_level":      state.values.get("risk_level"),
        "awaiting_review": bool(state.next),
        "revision_count":  state.values.get("revision_count", 0),
    }


@app.get("/health")
async def health():
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{settings.ollama_base_url}/api/tags")
            ollama_ok = resp.status_code == 200
    except Exception:
        ollama_ok = False
    return {"status": "healthy" if ollama_ok else "degraded", "ollama": ollama_ok}
