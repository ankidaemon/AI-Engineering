"""
RAG pipeline orchestration — the heart of the Research Assistant.

Ties every stage together into the request/response flow:

    rate-limit -> cache lookup -> query expansion -> hybrid retrieval
    -> dedup + rerank -> session-history injection -> generation
    -> cache + session update

Owns RAG stages 5 (query understanding / expansion) and 6 (generation), and
calls into the retrieval (stage 4), cache, and generation modules. See the
project README ("What You'll Build & Learn") for how each stage maps to a file.
"""
import re
import logging
import asyncio
from dataclasses import dataclass
from src.retrieval.hybrid_retriever import HybridRetriever
from src.retrieval.reranker import CrossEncoderReranker
from src.cache.redis_cache import RedisCache
from src.generation.llama_client import LlamaClient
from src.generation.prompt_builder import (
    build_rag_messages,
    build_query_expansion_messages
)
from src.config import settings

logger = logging.getLogger(__name__)


@dataclass
class RAGResponse:
    answer: str
    sources: list[dict]
    query: str
    expanded_queries: list[str]
    cache_hit: bool
    session_id: str


class RAGEngine:
    """
    Orchestrates the full RAG pipeline in nine steps:

    1.  Rate limit check (via Redis)
    2.  Cache lookup — return immediately on hit
    3.  Query expansion — generate alternative phrasings (Llama 3.1)
    4.  Hybrid retrieval — run all query variants through dense + sparse retrieval
    5.  Deduplication — merge candidates and deduplicate by chunk_id
    6.  Reranking — cross-encoder re-scores the candidate pool by relevance
        (recall → precision; the "needle" stage of Section 1.9). Falls back to
        RRF order when reranking is disabled.
    7.  Token budget check — ensure retrieved context fits the context window
    8.  Generation — build prompt, call Llama 3.1, receive answer
    9.  Persistence — cache result, update session history
    """

    # Llama 3.1 has 128K tokens. We reserve a budget for each component.
    CONTEXT_WINDOW        = 128_000
    SYSTEM_PROMPT_BUDGET  = 600
    HISTORY_BUDGET        = 1_500
    QUERY_BUDGET          = 400
    GENERATION_BUDGET     = 2_048
    MAX_CONTEXT_TOKENS    = (
        CONTEXT_WINDOW
        - SYSTEM_PROMPT_BUDGET
        - HISTORY_BUDGET
        - QUERY_BUDGET
        - GENERATION_BUDGET
    )  # ~123,352 tokens — extraordinarily large; a practical cap of ~8,000 is
       # more appropriate to keep responses focused.
    PRACTICAL_CONTEXT_CAP = 8_000

    def __init__(
        self,
        use_pinecone: bool = True,
        use_query_expansion: bool = True,
        use_reranker: bool = True
    ):
        self._retriever  = HybridRetriever(use_pinecone=use_pinecone)
        self._cache      = RedisCache()
        self._llama      = LlamaClient()
        self._expand     = use_query_expansion
        # Construct the cross-encoder once and reuse it across requests; loading
        # the model is expensive. None disables the second stage (RRF order only).
        self._reranker   = CrossEncoderReranker() if use_reranker else None

    async def query(
        self,
        query: str,
        session_id: str,
        metadata_filter: dict | None = None
    ) -> RAGResponse:

        # Step 1: Cache lookup
        cached = await self._cache.get_cached(query)
        if cached:
            return RAGResponse(
                answer           = cached["answer"],
                sources          = cached["sources"],
                query            = query,
                expanded_queries = cached.get("expanded_queries", []),
                cache_hit        = True,
                session_id       = session_id
            )

        # Step 2: Query expansion
        expanded = [query]
        if self._expand:
            try:
                expansion_messages = build_query_expansion_messages(query)
                expansion_text = await self._llama.generate(
                    expansion_messages, temperature=0.3
                )
                additional = self._parse_expanded_queries(expansion_text)
                expanded.extend(additional)
                logger.info(f"Expanded to {len(expanded)} query variants")
            except Exception as exc:
                logger.warning(f"Query expansion failed (continuing): {exc}")

        # Step 3: Retrieve for all query variants and deduplicate
        all_chunks: dict[str, dict] = {}
        for q in expanded:
            for chunk in self._retriever.retrieve(
                query=q,
                metadata_filter=metadata_filter
            ):
                key = chunk.get("chunk_id") or chunk["content"][:64]
                all_chunks.setdefault(key, chunk)

        # Step 4: Rerank the candidate pool (recall -> precision). The
        # cross-encoder reads each (query, chunk) pair jointly, which RRF never
        # does. When the reranker is disabled, fall back to RRF order.
        candidates = list(all_chunks.values())
        if self._reranker:
            ranked_chunks = self._reranker.rerank(
                query, candidates, top_k=settings.rerank_top_k
            )
        else:
            ranked_chunks = sorted(
                candidates,
                key=lambda c: c.get("rrf_score", c.get("score", 0)),
                reverse=True
            )

        # Step 5: Apply token budget to the reranked chunks
        budget_chunks = self._apply_token_budget(ranked_chunks)

        # Step 6: Load session history (for multi-turn context)
        session  = await self._cache.get_session(session_id)
        history  = self._cache.format_history_for_prompt(session)

        # Step 7: Generate answer
        messages = build_rag_messages(query, budget_chunks, history)
        answer   = await self._llama.generate(messages)

        # Step 8: Format sources for API response
        sources = [
            {
                "title":     c.get("metadata", {}).get("title", ""),
                "arxiv_id":  c.get("metadata", {}).get("arxiv_id", ""),
                "published": c.get("metadata", {}).get("published", "")[:10],
                "section":   c.get("metadata", {}).get("section", ""),
                "score":     round(
                    c.get("rerank_score", c.get("rrf_score", c.get("score", 0))), 4
                )
            }
            for c in budget_chunks
        ]

        response = RAGResponse(
            answer           = answer,
            sources          = sources,
            query            = query,
            expanded_queries = expanded[1:],
            cache_hit        = False,
            session_id       = session_id
        )

        # Step 9: Persist cache + session (run concurrently)
        await asyncio.gather(
            self._cache.set_cached(query, {
                "answer":           answer,
                "sources":          sources,
                "expanded_queries": expanded[1:]
            }),
            self._cache.append_turn(session_id, "user",      query),
            self._cache.append_turn(session_id, "assistant", answer[:600])
        )

        return response

    def _apply_token_budget(self, chunks: list[dict]) -> list[dict]:
        """
        Selects the highest-scoring chunks that fit within the practical
        context budget. Uses a word-count approximation (1 token ~= 0.75 words)
        to avoid importing a full tokenizer at runtime.
        """
        selected = []
        used_tokens = 0
        for chunk in chunks:
            est_tokens = int(len(chunk["content"].split()) / 0.75)
            if used_tokens + est_tokens > self.PRACTICAL_CONTEXT_CAP:
                break
            selected.append(chunk)
            used_tokens += est_tokens
        return selected

    def _parse_expanded_queries(self, text: str) -> list[str]:
        lines = text.strip().split("\n")
        queries = []
        for line in lines:
            m = re.match(r'^\s*\d+[.):\-]\s+(.+)$', line.strip())
            if m:
                queries.append(m.group(1).strip())
        return queries[:3]
