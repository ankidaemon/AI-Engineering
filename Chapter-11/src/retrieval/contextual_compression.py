"""
Contextual compression (Section 4.3, Strategy 3; fix for Failure 4).

A retrieved passage is often mostly irrelevant — a long page where two sentences
matter. Compression keeps only the relevant parts before they reach the
generator. The hazard is that naive compression discards cross-references and
exception clauses that *looked* irrelevant but were essential, so
`ReferencePreservingCompressor` always keeps the connective tissue (exceptions,
definitions, cross-references) even when it scores as low-relevance.
"""
import re

from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.document_compressors import (
    LLMChainExtractor,
    EmbeddingsFilter,
)

from src.config import settings
from src.models import get_fast_model, get_embeddings


def build_contextual_compression_retriever(
    base_retriever,
    method: str = "extraction",   # "extraction" (better) or "embeddings_filter" (faster)
):
    if method == "extraction":
        compressor = LLMChainExtractor.from_llm(get_fast_model(temperature=0))
    else:
        compressor = EmbeddingsFilter(
            embeddings=get_embeddings(),
            similarity_threshold=settings.compression_threshold,
        )
    return ContextualCompressionRetriever(
        base_compressor=compressor, base_retriever=base_retriever
    )


class ReferencePreservingCompressor:
    """
    Wraps a base compressor and re-attaches any sentence carrying a cross-reference
    or exception that the base compressor tried to drop.
    """

    PRESERVE_PATTERNS = [
        r"(?:as defined|as set forth|per Section|see Section)\s+\d+",
        r"(?:except|unless|notwithstanding|subject to|provided that)",
        r"(?:hereinafter|shall mean|is defined as|means)",
    ]

    def __init__(self, base_compressor):
        self._compressor = base_compressor
        self._pattern = re.compile("|".join(self.PRESERVE_PATTERNS), re.IGNORECASE)

    def compress_documents(self, documents, query):
        compressed = self._compressor.compress_documents(documents, query)
        result = []
        for orig, comp in zip(documents, compressed):
            if not comp:
                continue
            orig_refs = {str(r).lower() for r in self._pattern.findall(orig.page_content)}
            comp_refs = {str(r).lower() for r in self._pattern.findall(comp.page_content)}
            for missing in orig_refs - comp_refs:
                for sentence in orig.page_content.split("."):
                    if missing in sentence.lower():
                        comp.page_content += f"\n[Preserved reference]: {sentence.strip()}."
            result.append(comp)
        return result
