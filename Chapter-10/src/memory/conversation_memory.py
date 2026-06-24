"""
Conversation memory factories (Chapter 10, Section III).

The post-analysis Q&A layer uses ConversationSummaryBufferMemory — the
recommended production default. It keeps recent turns verbatim (precision) and
compresses older turns into a running summary (token efficiency), so it handles
both short and long sessions without unbounded growth (Failure 2).

`build_vector_store_memory` is an optional alternative for very long sessions
where semantic recall of distant turns matters more than recency.
"""
from langchain.memory import ConversationSummaryBufferMemory
from src.models import get_fast_model
from src.config import settings


def build_conversation_memory() -> ConversationSummaryBufferMemory:
    """Recommended default — summary buffer with a bounded token limit."""
    return ConversationSummaryBufferMemory(
        llm=get_fast_model(),
        max_token_limit=settings.memory_max_token_limit,
        return_messages=True,
        memory_key="chat_history",
    )


def build_vector_store_memory(k: int = 3):
    """
    Optional: semantic memory backed by Chroma + Ollama embeddings.

    Retrieves the k most relevant past turns by similarity rather than recency.
    Imports are local so the heavier vector-store deps are only pulled in when
    this strategy is actually used.
    """
    from langchain.memory import VectorStoreRetrieverMemory
    from langchain_community.vectorstores import Chroma
    from langchain_community.embeddings import OllamaEmbeddings

    embeddings = OllamaEmbeddings(
        model="nomic-embed-text",
        base_url=settings.ollama_base_url,
    )
    store = Chroma(
        collection_name="conversation_memory",
        embedding_function=embeddings,
        persist_directory=settings.chroma_persist_dir,
    )
    return VectorStoreRetrieverMemory(
        retriever=store.as_retriever(search_kwargs={"k": k}),
        memory_key="relevant_history",
    )
