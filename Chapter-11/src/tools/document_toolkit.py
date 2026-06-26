"""
Toolkits — named bundles of related tools (Section 2.3).

A toolkit is just "the right tools for this kind of job, gathered in one place."
Handing an agent a small, coherent set of tools (rather than everything) directly
improves how reliably it picks the right one.
"""
from typing import Any, List

from langchain_core.tools import BaseTool, BaseToolkit

from src.tools.document_tools import (
    word_count,
    extract_dates,
    calculate_readability,
)
from src.tools.retrieval_tools import DocumentSearchTool, CrossReferenceTool
from src.tools.legal_specific_tools import (
    extract_obligations_tool,
    flag_unusual_clauses_tool,
    compute_liability_exposure_tool,
)
from src.tools.technical_tools import (
    extract_api_specs_tool,
    identify_dependencies_tool,
    flag_security_concerns_tool,
    estimate_complexity_tool,
)


class LegalDocumentToolkit(BaseToolkit):
    """Tools tuned for legal contract analysis: search, extraction, comparison."""

    retriever: Any = None      # vector-store retriever
    llm:       Any = None      # model for the cross-reference tool

    def get_tools(self) -> List[BaseTool]:
        return [
            word_count,
            extract_dates,
            calculate_readability,
            DocumentSearchTool(retriever=self.retriever),
            CrossReferenceTool(llm=self.llm),
            extract_obligations_tool,
            flag_unusual_clauses_tool,
            compute_liability_exposure_tool,
        ]


class TechnicalDocumentToolkit(BaseToolkit):
    """Tools for technical specifications and architecture documents."""

    retriever: Any = None
    llm:       Any = None

    def get_tools(self) -> List[BaseTool]:
        return [
            word_count,
            calculate_readability,
            DocumentSearchTool(retriever=self.retriever),
            extract_api_specs_tool,
            identify_dependencies_tool,
            flag_security_concerns_tool,
            estimate_complexity_tool,
        ]
