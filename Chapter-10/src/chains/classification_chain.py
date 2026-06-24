"""
Document classification chain (LangChain LCEL).

A cheap first pass on the fast model that decides how the rest of the workflow
routes: document type, language, complexity, and whether the document is
high-stakes enough to warrant human review. Returns a dict (JsonOutputParser
emits a dict, not a Pydantic instance).
"""
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from src.models import get_fast_model


class DocumentClassification(BaseModel):
    document_type:         str  = Field(description="One of: legal, technical, financial, general")
    document_language:     str  = Field(description="Primary language, e.g. 'English'")
    estimated_complexity:  str  = Field(description="One of: low, medium, high")
    requires_human_review: bool = Field(description="True if the document is complex or high-stakes")
    classification_notes:  str  = Field(description="Brief justification for the classification")


def build_classification_chain():
    """prompt | fast_model | json_parser -> dict."""
    parser = JsonOutputParser(pydantic_object=DocumentClassification)
    prompt = ChatPromptTemplate.from_messages([
        ("system",
         "You classify documents for a downstream analysis pipeline. "
         "Respond with structured data only. {format_instructions}"),
        ("human",
         "Classify this document excerpt:\n\n<document>\n{excerpt}\n</document>"),
    ])
    return (
        prompt.partial(format_instructions=parser.get_format_instructions())
        | get_fast_model()
        | parser
    )
