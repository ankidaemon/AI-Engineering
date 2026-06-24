"""
Synthesis chain (LangChain LCEL) — optional executive narrative.

The workflow's `finalize` node assembles the final report *deterministically*
(no LLM) so it is fast, cheap, and unit-testable. This chain is a separate,
opt-in helper for when you want a polished prose executive summary that weaves
the structured fields together — e.g. for an email digest or a cover page.

It is intentionally NOT wired into the graph so that report generation stays
deterministic; call it explicitly where you want narrative output.
"""
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from src.models import get_quality_model


def build_synthesis_chain():
    prompt = ChatPromptTemplate.from_messages([
        ("system",
         "You are an executive briefing writer. Given a structured document "
         "analysis, write a concise (4-6 sentence) executive narrative that a "
         "decision-maker could read in under a minute. Be specific; cite the "
         "risk level and the single most important recommendation."),
        ("human",
         "Document type: {document_type}\n"
         "Risk level: {risk_level}\n\n"
         "Summary:\n{summary}\n\n"
         "Key risk flags:\n{risk_flags}\n\n"
         "Recommendations:\n{recommendations}"),
    ])
    return prompt | get_quality_model() | StrOutputParser()
