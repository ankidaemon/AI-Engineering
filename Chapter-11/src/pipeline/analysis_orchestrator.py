"""
Analysis orchestrator (Section 6.5).

This is where the chapter's adaptivity becomes concrete: the orchestrator picks
*how* to analyze based on *what* the document is. Legal and technical documents
go to ReAct agents armed with the right toolkit; financial and general documents
take a cheaper direct-LLM path; high-stakes work can request the reflection
wrapper. Matching the cost of the method to the difficulty of the document is what
keeps the system affordable at scale.

The retrieval stack is wired once at startup: base FAISS retriever → multi-query
→ contextual compression → the search tool the agents share.
"""
import logging

from langchain_core.messages import HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from src.agents.react_agent import build_react_agent, run_agent
from src.agents.reflection_agent import build_reflection_agent
from src.config import settings
from src.models import get_quality_model
from src.retrieval.contextual_compression import build_contextual_compression_retriever
from src.retrieval.multi_query import build_multi_query_retriever
from src.tools.document_toolkit import LegalDocumentToolkit, TechnicalDocumentToolkit
from src.vectorstores.faiss_store import FAISSVectorStore

logger = logging.getLogger(__name__)

LEGAL_SYSTEM_PROMPT = """You are a senior legal analyst reviewing contracts and \
agreements. Your analysis must be specific (cite clauses and sections), balanced \
(risks AND protections), and actionable (every risk gets a recommendation).
Work systematically: size the document, search for clauses, extract obligations, \
flag unusual provisions, and cross-reference for inconsistencies."""

TECHNICAL_SYSTEM_PROMPT = """You are a senior software architect and security \
reviewer. Cover architecture soundness, security and compliance gaps, scalability, \
maintainability, and integration/dependency risks. Use document_search to locate \
specific sections before analyzing them."""


class DocumentAnalysisOrchestrator:
    def __init__(self, faiss_store: FAISSVectorStore):
        self._faiss = faiss_store
        self._quality = get_quality_model(temperature=0.1)

        # Compose the retrieval stack once: base → multi-query → compression.
        base = faiss_store.as_retriever(k=settings.retrieval_k)
        retriever = base
        if settings.use_multi_query:
            retriever = build_multi_query_retriever(retriever)
        retriever = build_contextual_compression_retriever(retriever)

        legal_tools = LegalDocumentToolkit(
            retriever=retriever, llm=get_quality_model(temperature=0)).get_tools()
        technical_tools = TechnicalDocumentToolkit(
            retriever=retriever, llm=get_quality_model(temperature=0)).get_tools()

        self._legal_agent = build_react_agent(
            tools=legal_tools, model_name=settings.quality_model,
            max_tool_calls=settings.max_tool_calls)
        self._technical_agent = build_react_agent(
            tools=technical_tools, model_name=settings.quality_model,
            max_tool_calls=settings.max_tool_calls)
        self._reflection_agent = build_reflection_agent(
            model_name=settings.quality_model,
            max_iterations=settings.max_reflection_iter)

    def analyze(self, doc_id: str, doc_type: str, full_text: str,
                use_reflection: bool = False) -> dict:
        logger.info("Analyzing doc_id=%s type=%s", doc_id, doc_type)
        if doc_type == "legal":
            return self._analyze_legal(full_text, use_reflection)
        if doc_type == "technical":
            return self._analyze_technical(full_text)
        return self._analyze_general(full_text, doc_type)

    def _analyze_legal(self, text: str, use_reflection: bool) -> dict:
        query = (
            "Perform a comprehensive legal analysis. Focus on (1) obligations and "
            "rights, (2) liability and indemnification, (3) unusual or risky clauses, "
            "(4) missing standard provisions, (5) key dates.\n\n"
            f"Document (first 2000 chars):\n{text[:2000]}"
        )
        if use_reflection:
            result = self._reflection_agent.invoke({
                "task": query, "iteration": 0,
                "max_iterations": settings.max_reflection_iter, "messages": [],
            })
            analysis = result["messages"][-1].content if result.get("messages") else ""
            agent = "legal_react_with_reflection"
        else:
            analysis = run_agent(self._legal_agent, query, LEGAL_SYSTEM_PROMPT)
            agent = "legal_react"
        return {"type": "legal", "analysis": analysis, "agent": agent}

    def _analyze_technical(self, text: str) -> dict:
        query = (
            "Perform a comprehensive technical review. Focus on (1) architecture, "
            "(2) security and compliance, (3) scalability and performance, "
            "(4) maintainability, (5) dependencies and integration risk.\n\n"
            f"Document (first 2000 chars):\n{text[:2000]}"
        )
        analysis = run_agent(self._technical_agent, query, TECHNICAL_SYSTEM_PROMPT)
        return {"type": "technical", "analysis": analysis, "agent": "technical_react"}

    def _analyze_general(self, text: str, doc_type: str) -> dict:
        prompt = ChatPromptTemplate.from_messages([
            ("system",
             f"You are an expert analyst for {doc_type} documents. Provide a thorough "
             f"structured analysis: key findings, risks, opportunities, recommendations."),
            ("human", f"Analyze this document:\n\n{text[:4000]}"),
        ])
        analysis = (prompt | self._quality | StrOutputParser()).invoke({})
        return {"type": doc_type, "analysis": analysis, "agent": "general_llm"}

    def synthesize(self, analyses: list[dict], original_query: str = "") -> str:
        joined = "\n\n".join(
            f"=== {a['type'].upper()} ANALYSIS ===\n{a['analysis']}" for a in analyses
        )
        prompt = (
            f"Synthesize these specialist analyses into a unified executive report.\n\n"
            f"{joined}\n\n"
            + (f"Original request: {original_query}\n\n" if original_query else "")
            + "Use sections: Executive Summary, Key Findings, Risk Assessment, "
            "Recommendations, Next Steps."
        )
        return self._quality.invoke([HumanMessage(content=prompt)]).content
