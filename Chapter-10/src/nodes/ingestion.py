"""
Ingestion node — the workflow's entry point.

Validates and lightly cleans the input text. In a fuller deployment this is
where PDF/DOCX/HTML extraction would live (pypdf is already a dependency); here
we accept pre-extracted text and normalize whitespace.

Also stamps the state schema version. If a resumed checkpoint carries an older
version than the running code, we restart from scratch rather than silently
operating on a mismatched shape (Chapter 10, Failure 5).
"""
import re
import time
import logging
from langchain_core.messages import AIMessage
from src.state import WorkflowState, STATE_SCHEMA_VERSION

logger = logging.getLogger(__name__)


def ingest_document(state: WorkflowState) -> dict:
    start = time.time()

    stored_version = state.get("state_schema_version", STATE_SCHEMA_VERSION)
    if stored_version < STATE_SCHEMA_VERSION:
        logger.warning(
            "Resuming workflow with old schema v%s (current v%s) — restarting fresh.",
            stored_version, STATE_SCHEMA_VERSION,
        )

    text = state.get("document_text", "").strip()

    errors: list[str] = []
    if not text:
        errors.append("Document text is empty")
        return {
            "state_schema_version": STATE_SCHEMA_VERSION,
            "errors": errors,
            "current_step": "ingest_document",
        }

    if len(text) < 50:
        errors.append("Document too short to analyze meaningfully")

    # Collapse runs of blank lines and horizontal whitespace, preserving paragraphs.
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)

    word_count = len(text.split())
    elapsed = int((time.time() - start) * 1000)

    return {
        "state_schema_version": STATE_SCHEMA_VERSION,
        "document_text":        text,
        "current_step":         "ingest_document",
        "errors":               errors,
        "processing_time_ms":   {"ingest": elapsed},
        "messages":             [AIMessage(content=f"Document ingested: {word_count} words")],
    }
