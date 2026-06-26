"""
Shared model factories.

Two chat tiers and one embedding model, all served by Ollama and configured from
settings. Because the rest of the codebase depends only on the LangChain
interfaces, swapping providers is confined to this module.

    get_fast_model()    -> 8B  — classification, tool selection, query expansion
    get_quality_model() -> 70B — analysis, synthesis, reflection
    get_embeddings()    -> embedding model for the vector store
"""
from langchain_ollama import ChatOllama, OllamaEmbeddings

from src.config import settings


def get_fast_model(temperature: float = 0.0) -> ChatOllama:
    """Fast 8B model. Temperature defaults to 0 — tool/route choices want consistency."""
    return ChatOllama(
        model=settings.fast_model,
        base_url=settings.ollama_base_url,
        temperature=temperature,
    )


def get_quality_model(temperature: float = 0.1) -> ChatOllama:
    """Higher-quality 70B model for analysis, synthesis, and reflection."""
    return ChatOllama(
        model=settings.quality_model,
        base_url=settings.ollama_base_url,
        temperature=temperature,
    )


def get_embeddings() -> OllamaEmbeddings:
    """Embedding model used by FAISS / Chroma and the HyDE retriever."""
    return OllamaEmbeddings(
        model=settings.embedding_model,
        base_url=settings.ollama_base_url,
    )
