"""
Risk assessment chain (LangChain LCEL).

Consumes the upstream analysis (summary, key points, action items) and produces
risk flags, an overall risk level, decision-support options, and a verdict on
whether human review is required. Runs on the quality model.
"""
from typing import List
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from src.models import get_quality_model


class RiskAssessmentResult(BaseModel):
    risk_flags:            List[str]  = Field(description="Specific risks identified")
    risk_level:            str        = Field(description="Overall: low | medium | high | critical")
    requires_human_review: bool       = Field(description="True if risk_level is high or critical")
    recommendations:       List[str]  = Field(description="Risk mitigation recommendations")
    decision_options:      List[dict] = Field(
        description="2-3 options, each a dict with 'option', 'pros' (list), 'cons' (list)"
    )


def build_risk_chain():
    parser = JsonOutputParser(pydantic_object=RiskAssessmentResult)
    prompt = ChatPromptTemplate.from_messages([
        ("system",
         "You are a risk assessment specialist. Based on the document analysis "
         "provided, identify risks and generate decision-support options. "
         "{format_instructions}"),
        ("human",
         "Document type: {document_type}\n\n"
         "Analysis summary:\n{summary}\n\n"
         "Key points:\n{key_points}\n\n"
         "Action items:\n{action_items}\n\n"
         "Perform a comprehensive risk assessment and generate 2-3 decision options."),
    ])
    return (
        prompt.partial(format_instructions=parser.get_format_instructions())
        | get_quality_model()
        | parser
    )
