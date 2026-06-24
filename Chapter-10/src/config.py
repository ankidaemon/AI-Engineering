"""
Central configuration for the AI Workflow Designer.

Values are read from environment variables (and an optional .env file) via
pydantic-settings. Field names map case-insensitively to env vars, so
`PRIMARY_MODEL` populates `primary_model`. Every field has a default, so the
app boots without any configuration as long as Ollama is reachable.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Models (Ollama) ───────────────────────────────────────────────
    ollama_base_url: str = "http://localhost:11434"
    primary_model:   str = "llama3.1:8b"    # fast model — routing/classification
    advanced_model:  str = "llama3.1:70b"   # quality model — analysis/generation

    # ── Persistence ───────────────────────────────────────────────────
    checkpoint_db_path: str = "./data/conversations.db"
    chroma_persist_dir: str = "./data/chroma_memory"

    # ── Behaviour ─────────────────────────────────────────────────────
    memory_max_token_limit: int = 3000   # summary-buffer compression threshold
    max_revisions:          int = 3      # hard cap on human-review loops

    # ── LangSmith (optional observability) ────────────────────────────
    langchain_tracing_v2: bool = False
    langchain_api_key:    str | None = None
    langchain_project:    str = "ai-workflow-designer"


settings = Settings()
