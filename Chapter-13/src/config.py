"""
Central configuration for the Multi-Agent Banking Assistant (chapter §8.3).

Every value can be overridden with an environment variable or a `.env` file,
so the same code runs on a laptop and in a container without edits. See
`.env.example` for the full list. Gathering the tunables most likely to need
adjustment under real load into one visible place is itself a production habit.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # ── Models (served locally by Ollama) ────────────────────────────
    fast_model: str = "llama3.1:8b"          # cheap: routing, rewrites
    quality_model: str = "llama3.1:70b"      # slower: grounded answers, advice
    embedding_model: str = "nomic-embed-text"
    ollama_base_url: str = "http://localhost:11434"

    # ── Vector store and documents ───────────────────────────────────
    faiss_persist_dir: str = "./data/faiss"
    documents_dir: str = "./data/documents"

    # ── Redis: Celery broker AND shared cache (Section VII) ──────────
    redis_url: str = "redis://localhost:6379/0"

    # ── Retrieval (Section IV) ───────────────────────────────────────
    retrieval_k: int = 6
    min_relevance: float = 0.25   # below this the knowledge agent declines

    # ── Routing (Section III): intent retrieval, no model call ──────
    router_min_score: float = 0.2    # weaker match than this: route to question
    router_min_margin: float = 0.05  # closer call than this: route to question

    # ── Tool selection (Section VI) ──────────────────────────────────
    tool_top_k: int = 4           # tools handed to the model per action
    history_turns: int = 6        # turns given to the contextualizer

    # ── Semantic cache (Section VII) ─────────────────────────────────
    cache_similarity_threshold: float = 0.92
    cache_ttl_seconds: int = 3600

    # ── Long-term memory: Mem0, kept in-house (Section II) ───────────
    memory_dir: str = "./data/memory"
    memory_recall_k: int = 3      # memories folded into an advice query

    # ── Consuming somebody else's MCP server (§1.5, §8.10) ───────────
    # A server on the internet needs a credential; the bank's own server,
    # launched as a child process, does not.
    firecrawl_api_key: str = ""
    firecrawl_mcp_url: str = "https://mcp.firecrawl.dev/v2/mcp"

    # ── Serving ──────────────────────────────────────────────────────
    api_port: int = 8100


settings = Settings()
