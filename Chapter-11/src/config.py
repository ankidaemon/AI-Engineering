"""
Central configuration for the Dynamic Document Reader (Chapter 11).

Values are read from environment variables (and an optional .env file) via
pydantic-settings. Field names map case-insensitively to env vars, so
`FAST_MODEL` populates `fast_model`. Every field has a default, so the app boots
without any configuration as long as Ollama is reachable.

The agent safety limits (max_tool_calls, max_agent_iter, max_reflection_iter)
live here on purpose: they are the values most likely to need tuning under real
load, and surfacing them as configuration keeps them out of the logic.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        protected_namespaces=(),   # we use field names like *_model freely
    )

    # ── Models (Ollama) ───────────────────────────────────────────────
    ollama_base_url: str = "http://localhost:11434"
    fast_model:      str = "llama3.1:8b"     # classification, tool use, query expansion
    quality_model:   str = "llama3.1:70b"    # analysis, synthesis, reflection
    embedding_model: str = "nomic-embed-text"

    # ── FAISS (local vector store) ────────────────────────────────────
    faiss_persist_dir: str = "./data/faiss_index"
    faiss_index_type:  str = "Flat"          # Flat | IVFFlat | HNSW

    # ── Chroma (local, persistent vector database) ────────────────────
    use_chroma:         bool = False         # opt-in alternative to FAISS
    chroma_persist_dir: str  = "./data/chroma"
    chroma_collection:  str  = "documents"

    # ── Retrieval ─────────────────────────────────────────────────────
    retrieval_k:           int   = 8
    use_multi_query:       bool  = True
    use_hyde:              bool  = False      # opt in; disable for existence queries
    compression_threshold: float = 0.76

    # ── Agent safety limits ───────────────────────────────────────────
    max_tool_calls:      int = 12            # per-agent hard cap (Failure 1)
    max_agent_iter:      int = 8             # supervisor hard cap
    max_reflection_iter: int = 2             # reflection generate/critique rounds

    # ── Document loading ──────────────────────────────────────────────
    max_pdf_pages:  int = 300
    min_page_chars: int = 50
    upload_dir:     str = "./data/uploads"


settings = Settings()
