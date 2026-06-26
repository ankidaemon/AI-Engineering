"""
Structured, class-based tools that take several parameters (Section 2.2).

For multi-argument tools we declare the input shape with a Pydantic schema and
attach it as `args_schema`. The schema does double duty: it tells the model
exactly what each argument means, and it validates the model's call before our
code runs (e.g. `top_k` is constrained to 1..20).
"""
import logging
from typing import Any, Optional, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ── document_search ───────────────────────────────────────────────────────

class DocumentSearchInput(BaseModel):
    query:      str           = Field(description="Semantic search query")
    top_k:      int           = Field(default=5, ge=1, le=20,
                                      description="Number of results to return")
    doc_type:   Optional[str] = Field(default=None,
                                      description="Filter by type: legal, technical, financial")
    date_after: Optional[str] = Field(default=None,
                                      description="Only documents after this date (YYYY-MM-DD)")


class DocumentSearchTool(BaseTool):
    """Searches the user's indexed documents using semantic similarity."""

    name:        str = "document_search"
    description: str = (
        "Searches the USER'S UPLOADED DOCUMENTS indexed in this session using "
        "semantic similarity. Use this when the user asks about their specific "
        "contract, report, or uploaded file. Returns verbatim excerpts with their "
        "source and page. Do NOT use this for general knowledge questions."
    )
    args_schema: Type[BaseModel] = DocumentSearchInput
    # Declared as a field (typed Any) so pydantic v2 accepts the injected retriever.
    retriever: Any = None

    def _run(
        self,
        query:      str,
        top_k:      int = 5,
        doc_type:   Optional[str] = None,
        date_after: Optional[str] = None,
        run_manager: Optional[Any] = None,
    ) -> str:
        try:
            docs = self.retriever.invoke(query)

            if doc_type:
                docs = [d for d in docs if d.metadata.get("doc_type") == doc_type]
            if date_after:
                docs = [d for d in docs if str(d.metadata.get("date", "")) > date_after]
            docs = docs[:top_k]

            if not docs:
                return "No relevant documents found for this query."

            blocks = []
            for i, doc in enumerate(docs, 1):
                source = doc.metadata.get("filename", doc.metadata.get("source", "Unknown"))
                page   = doc.metadata.get("page", "")
                header = f"[Result {i}] Source: {source}" + (f", Page {page}" if page else "")
                blocks.append(f"{header}\n{doc.page_content[:800]}")
            return "\n\n---\n\n".join(blocks)

        except Exception as exc:                       # tools must fail soft
            logger.error("DocumentSearchTool error: %s", exc)
            return f"Search failed: {exc}"

    async def _arun(self, *args, **kwargs) -> str:
        return self._run(*args, **kwargs)


# ── cross_reference ───────────────────────────────────────────────────────

class CrossReferenceInput(BaseModel):
    section_a: str = Field(description="First section or clause text to compare")
    section_b: str = Field(description="Second section or clause text to compare")
    aspect:    str = Field(default="obligations",
                           description="Aspect to compare: obligations, rights, risks, dates")


class CrossReferenceTool(BaseTool):
    """Compares two passages to surface agreements, conflicts, and gaps."""

    name:        str = "cross_reference"
    description: str = (
        "Compares two sections of text to identify points of agreement, conflicts "
        "or contradictions, and gaps where one section is silent. Useful for "
        "contract consistency checking and comparing clauses across documents."
    )
    args_schema: Type[BaseModel] = CrossReferenceInput
    llm: Any = None

    def _run(
        self,
        section_a: str,
        section_b: str,
        aspect: str = "obligations",
        run_manager: Optional[Any] = None,
    ) -> str:
        from langchain_core.messages import HumanMessage
        prompt = (
            f"Compare these two document sections regarding their {aspect}.\n\n"
            f"Section A:\n{section_a[:1000]}\n\n"
            f"Section B:\n{section_b[:1000]}\n\n"
            f"Identify: (1) points of agreement, (2) conflicts or contradictions, "
            f"(3) gaps where one section is silent on what the other addresses."
        )
        try:
            return self.llm.invoke([HumanMessage(content=prompt)]).content
        except Exception as exc:
            logger.error("CrossReferenceTool error: %s", exc)
            return f"Comparison failed: {exc}"

    async def _arun(self, *args, **kwargs) -> str:
        return self._run(*args, **kwargs)
