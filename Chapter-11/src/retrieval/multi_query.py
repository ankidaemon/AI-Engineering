"""
Multi-query retrieval (Section 4.3, Strategy 1; fix for Failure 3).

One phrasing of a question can miss passages worded differently. Multi-query has
a model rewrite the question several ways, searches with each, and merges the
results. The danger is letting the rewrites drift off-topic, so the prompt demands
*equivalent rephrasings* (not related questions) and `filter_irrelevant_results`
drops any result that wandered too far from the original query.
"""
from langchain.retrievers import MultiQueryRetriever
from langchain_core.documents import Document
from langchain_core.prompts import PromptTemplate

from src.models import get_fast_model

# Constrained expansion prompt — same information, different words, same scope.
_EXPANSION_PROMPT = PromptTemplate(
    input_variables=["question"],
    template=(
        "Generate 3 alternative phrasings of this question. Each alternative must:\n"
        "- ask for the SAME information\n"
        "- use different but equivalent terminology\n"
        "- stay within the same domain and scope\n"
        "- NOT introduce new topics absent from the original\n\n"
        "Original: {question}\n\n"
        "Alternatives (one per line, no numbering, no explanation):"
    ),
)


def build_multi_query_retriever(base_retriever, model_name: str | None = None):
    model = get_fast_model(temperature=0.3)
    return MultiQueryRetriever.from_llm(
        retriever=base_retriever, llm=model, prompt=_EXPANSION_PROMPT
    )


def filter_irrelevant_results(
    results: list[Document],
    original_query: str,
    embeddings,
    threshold: float = 0.70,
) -> list[Document]:
    """Drop results too dissimilar to the ORIGINAL query (second line of defense)."""
    q = embeddings.embed_query(original_query)
    kept: list[Document] = []
    for doc in results:
        d = embeddings.embed_query(doc.page_content[:200])
        similarity = float(sum(a * b for a, b in zip(q, d)))
        if similarity >= threshold:
            kept.append(doc)
    return kept
