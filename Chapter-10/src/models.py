"""
Shared LLM instances.

Two tiers, chosen per task to balance latency and quality:

    get_fast_model()    -> 8B  — classification, routing, history summarization
    get_quality_model() -> 70B — analysis, risk assessment, user-facing Q&A

Both return a ChatOllama configured from settings. Because the rest of the
codebase depends only on the LangChain ChatModel interface, swapping providers
(ChatOpenAI, ChatAnthropic, ...) is a change confined to this module.
"""
from langchain_ollama import ChatOllama
from src.config import settings


def get_fast_model() -> ChatOllama:
    """Fast 8B model — cheap, suitable for classification/routing/extraction."""
    return ChatOllama(
        model=settings.primary_model,
        base_url=settings.ollama_base_url,
        temperature=0.1,
        num_predict=1024,
    )


def get_quality_model() -> ChatOllama:
    """Higher-quality 70B model — summarization, analysis, generation."""
    return ChatOllama(
        model=settings.advanced_model,
        base_url=settings.ollama_base_url,
        temperature=0.1,
        num_predict=2048,
    )
