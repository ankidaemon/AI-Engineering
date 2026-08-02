"""
Central configuration for the Real-Time Intelligence Monitor.

Every value can be overridden with an environment variable or a `.env` file,
so the same code runs on a laptop and in a container without edits. See
`.env.example` for the full list.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # ── Models (served locally by Ollama) ────────────────────────────
    fast_model: str = "llama3.1:8b"          # cheap, quick classification and routing
    quality_model: str = "llama3.1:70b"      # slower, used for the hard reasoning
    embedding_model: str = "nomic-embed-text"
    ollama_base_url: str = "http://localhost:11434"

    # ── Vector store ─────────────────────────────────────────────────
    # "memory" | "pgvector". pgvector filters by customer in SQL, which is what
    # makes one shared table safe to serve every customer from.
    vector_store: str = "pgvector"
    vector_collection: str = "intelligence"

    # ── Checkpointing (LangGraph memory) ─────────────────────────────
    # "memory" | "sqlite" | "postgres". Sqlite is the default for local runs.
    checkpointer: str = "sqlite"
    sqlite_path: str = "./data/intel.db"
    postgres_url: str = "postgresql://intel:intel@localhost:5432/intel"

    # ── Tenancy ──────────────────────────────────────────────────────
    # Where conversation ownership lives: "memory" | "postgres".
    conversation_store: str = "memory"
    # `key1:customer-a,key2:customer-b`. Empty means every request gets a 401,
    # which is the right default: there is no anonymous customer to fall back to.
    api_keys: str = ""

    # ── Observability (LangSmith) ────────────────────────────────────
    langsmith_project: str = "real-time-intelligence-monitor"
    langsmith_tracing: bool = False          # off by default so tests never phone home
    trace_sampling_rate: float = 0.2         # sample 20% of production traffic
    alert_webhook_url: str = ""

    # ── FireCrawl (web ingestion) ────────────────────────────────────
    firecrawl_api_key: str = ""
    firecrawl_requests_per_minute: int = 80  # stay under the provider ceiling

    # ── Cost control ─────────────────────────────────────────────────
    hourly_budget_usd: float = 10.00
    max_output_tokens: int = 500
    llm_requests_per_minute: int = 60
    max_concurrent_llm_calls: int = 10


settings = Settings()
