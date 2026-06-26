"""
FastAPI interface for the Dynamic Document Reader (Section 6.6).

The endpoints are deliberately thin: they validate input, call into the pipeline
objects built once at startup, and shape the response. All the intelligence lives
in the orchestrator and agents — the API is just the door.
"""
import logging
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from src.config import settings
from src.pipeline.analysis_orchestrator import DocumentAnalysisOrchestrator
from src.pipeline.document_processor import DocumentProcessor
from src.vectorstores.faiss_store import FAISSVectorStore

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s — %(message)s")
logger = logging.getLogger(__name__)

# Populated in the lifespan handler below.
faiss_store: FAISSVectorStore
processor: DocumentProcessor
orchestrator: DocumentAnalysisOrchestrator


@asynccontextmanager
async def lifespan(app: FastAPI):
    global faiss_store, processor, orchestrator
    logger.info("Starting Dynamic Document Reader...")
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    faiss_store = FAISSVectorStore(persist_dir=settings.faiss_persist_dir)
    processor = DocumentProcessor(faiss_store)
    orchestrator = DocumentAnalysisOrchestrator(faiss_store)
    logger.info("Ready — %d vectors in FAISS index", faiss_store.get_vector_count())
    yield


app = FastAPI(
    title="Dynamic Document Reader",
    description="AI-powered document ingestion and analysis (Chapter 11)",
    version="1.0.0",
    lifespan=lifespan,
)


class AnalysisRequest(BaseModel):
    doc_id: str
    doc_type: Optional[str] = None
    use_reflection: bool = False
    query: Optional[str] = None


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=3)
    doc_id: Optional[str] = None
    doc_type: Optional[str] = None
    k: int = Field(default=5, ge=1, le=20)


@app.post("/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    doc_type: Optional[str] = Form(default=None),
    doc_id: Optional[str] = Form(default=None),
):
    """Upload and ingest a document (PDF, DOCX, TXT, HTML, CSV)."""
    doc_id = doc_id or str(uuid.uuid4())
    save_path = Path(settings.upload_dir) / f"{doc_id}_{file.filename}"
    save_path.write_bytes(await file.read())

    result = processor.process(file_path=str(save_path), doc_type=doc_type, doc_id=doc_id)
    if "error" in result:
        raise HTTPException(status_code=422, detail=result["error"])
    return {
        "message": "Document ingested successfully",
        "doc_id": result["doc_id"], "doc_type": result["doc_type"],
        "chunks_indexed": result["chunks_indexed"],
        "processing_ms": result["processing_ms"],
    }


@app.post("/documents/analyze")
async def analyze_document(req: AnalysisRequest):
    """Run agent-based analysis on a previously uploaded document."""
    candidates = list(Path(settings.upload_dir).glob(f"{req.doc_id}_*"))
    if not candidates:
        raise HTTPException(404, f"Document {req.doc_id} not found")

    pages = processor._loader.load(str(candidates[0]))
    full_text = "\n\n".join(p.page_content for p in pages)
    doc_type = req.doc_type or processor._classify_type(full_text[:1000])

    analysis = orchestrator.analyze(
        doc_id=req.doc_id, doc_type=doc_type, full_text=full_text,
        use_reflection=req.use_reflection,
    )
    return {"doc_id": req.doc_id, "doc_type": doc_type,
            "analysis": analysis["analysis"], "agent": analysis["agent"]}


@app.post("/documents/query")
async def query_documents(req: QueryRequest):
    """Search indexed documents using advanced retrieval."""
    results = faiss_store.similarity_search_with_score(query=req.question, k=req.k)
    return {
        "question": req.question,
        "results": [
            {
                "content": doc.page_content[:500], "score": round(score, 4),
                "source": doc.metadata.get("filename", ""),
                "page": doc.metadata.get("page", ""),
                "doc_type": doc.metadata.get("doc_type", ""),
                "doc_id": doc.metadata.get("doc_id", ""),
            }
            for doc, score in results
            if (not req.doc_type or doc.metadata.get("doc_type") == req.doc_type)
            and (not req.doc_id or doc.metadata.get("doc_id") == req.doc_id)
        ],
    }


@app.get("/index/stats")
async def index_stats():
    return {"vector_count": faiss_store.get_vector_count(),
            "persist_dir": settings.faiss_persist_dir}


@app.get("/health")
async def health():
    """Liveness + a real check that Ollama is reachable (report 'degraded' if not)."""
    import httpx
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{settings.ollama_base_url}/api/tags")
            ollama_ok = resp.status_code == 200
    except Exception:
        ollama_ok = False
    return {"status": "healthy" if ollama_ok else "degraded", "ollama": ollama_ok}
