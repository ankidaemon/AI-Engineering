"""
Self-querying retrieval (Section 4.3, Strategy 2).

Some questions secretly contain filters: "contracts signed after 2023 with a
liability cap under $1M" is part semantic search and part metadata filter.
Self-querying lets the model translate the natural-language question into both.
You enable it by describing the metadata fields — names, types, meanings — so the
model knows what it may filter on. Those descriptions are written for the model.
"""
from langchain.chains.query_constructor.base import AttributeInfo
from langchain.retrievers.self_query.base import SelfQueryRetriever

from src.models import get_quality_model

_METADATA_FIELDS = [
    AttributeInfo(name="doc_type",
                  description="Document type: legal, technical, financial, general",
                  type="string"),
    AttributeInfo(name="date",
                  description="Document date in YYYY-MM-DD format", type="string"),
    AttributeInfo(name="risk_level",
                  description="Pre-assessed risk: low, medium, high, critical",
                  type="string"),
    AttributeInfo(name="total_pages",
                  description="Number of pages in the document", type="integer"),
]

_CONTENT_DESCRIPTION = (
    "Legal, technical, and financial documents indexed for analysis — contracts, "
    "specifications, reports, and policy documents."
)


def build_self_querying_retriever(vectorstore, model_name: str | None = None):
    return SelfQueryRetriever.from_llm(
        llm=get_quality_model(temperature=0),
        vectorstore=vectorstore,
        document_contents=_CONTENT_DESCRIPTION,
        metadata_field_info=_METADATA_FIELDS,
        verbose=True,   # log the generated structured query while developing
    )
