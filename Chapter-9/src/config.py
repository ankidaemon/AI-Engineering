from pydantic_settings import BaseSettings
from pydantic import Field
from pydantic_settings import SettingsConfigDict


class Settings(BaseSettings):
    # Llama / Ollama
    llama_model: str = "llama3.1:8b"
    llama_temperature: float = Field(default=0.1, ge=0.0, le=1.0)
    llama_max_tokens: int = 2048
    ollama_base_url: str = "http://localhost:11434"

    # Pinecone
    pinecone_api_key: str = ""
    pinecone_environment: str = "us-east-1"
    pinecone_index_name: str = "research-assistant"

    # ChromaDB
    chroma_persist_directory: str = "./data/chroma_db"
    chroma_collection_name: str = "research_papers"

    # Redis
    redis_url: str = "redis://localhost:6379"
    redis_cache_ttl: int = 3600       # 1 hour for query results
    redis_session_ttl: int = 86400    # 24 hours for sessions
    redis_rate_limit_rpm: int = 60    # requests per minute per IP

    # Embeddings
    embedding_model: str = "sentence-transformers/all-mpnet-base-v2"
    embedding_dimension: int = 768

    # Retrieval
    retrieval_top_k: int = 12         # candidates before reranking
    rerank_top_k: int = 5             # final chunks sent to model
    hybrid_alpha: float = Field(default=0.7, ge=0.0, le=1.0)

    # Chunking
    chunk_size: int = 512             # target tokens per chunk
    chunk_overlap_sentences: int = 2  # sentence overlap between chunks
    min_chunk_size: int = 100         # discard chunks smaller than this

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)


# Singleton — import this everywhere
settings = Settings()
