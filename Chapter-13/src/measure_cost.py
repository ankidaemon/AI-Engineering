"""
Measure what each kind of request really costs (§8.16).

Runs the real assistant against the real local models and prints, for every
request, each model call it made with its input tokens, output tokens and
time, plus how many times it embedded text. Then it hands one exchange to
Mem0 in a throwaway folder, to show what remembering costs in the
background. Nothing is estimated: the token counts are the ones Ollama
reports for the call.

    python -m src.measure_cost

Needs Ollama running with the models in `.env`. Redis is not needed: the
cache and the idempotency store use an in-memory stand-in, which changes
where keys live but not a single model call.
"""
import tempfile
import time

LOG = []


class CountedModel:
    """Wraps a chat model and records every call it makes."""

    def __init__(self, inner, tier):
        self._inner, self._tier = inner, tier

    def invoke(self, prompt):
        started = time.time()
        response = self._inner.invoke(prompt)
        meta = response.response_metadata
        LOG.append({"call": self._tier,
                    "tokens_in": meta.get("prompt_eval_count", 0),
                    "tokens_out": meta.get("eval_count", 0),
                    "secs": round(time.time() - started, 2)})
        return response


class CountedEmbeddings:
    """Wraps the embedder and counts how many texts it embedded. Callable,
    because the FAISS store calls its embedder as a function."""

    def __init__(self, inner):
        self._inner = inner

    def embed_query(self, text):
        LOG.append({"call": "embed"})
        return self._inner.embed_query(text)

    def embed_documents(self, texts):
        return self._inner.embed_documents(texts)     # startup, not per request

    def __call__(self, text):
        return self.embed_query(text)


def _build():
    import fakeredis
    from langchain_ollama import ChatOllama, OllamaEmbeddings

    from src.assistant import Assistant
    from src.cache.semantic_cache import RedisBackend, SemanticCache
    from src.config import settings
    from src.knowledge.agent import KnowledgeService
    from src.products.advisor import Customer, ProductAdvisor
    from src.products.catalog import DEFAULT_CATALOG, build_product_index
    from src.router import Router
    from src.tools.action_agent import ActionAgent
    from src.tools.idempotency import IdempotencyStore
    from src.tools.pending import PendingActions
    from src.tools.read_tools import READ_TOOLS
    from src.tools.selector import build_tool_index
    from src.tools.service_desk import ServiceDesk
    from src.tools.write_tools import WRITE_TOOLS
    from src.vectorstores.faiss_store import KnowledgeIndex

    def chat(name, tier):
        return CountedModel(ChatOllama(model=name, temperature=0,
                                       base_url=settings.ollama_base_url), tier)

    embeddings = CountedEmbeddings(OllamaEmbeddings(
        model=settings.embedding_model, base_url=settings.ollama_base_url))
    fast = chat(settings.fast_model, "fast")
    quality = chat(settings.quality_model, "quality")
    redis_client = fakeredis.FakeRedis()
    demo = Customer(customer_id="demo", income=50000,
                    holdings=["everyday-savings"], profile_notes="")

    assistant = Assistant(
        KnowledgeService(KnowledgeIndex(persist_dir=settings.faiss_persist_dir,
                                        embeddings=embeddings),
                         model=quality, k=settings.retrieval_k,
                         min_relevance=settings.min_relevance),
        ProductAdvisor(build_product_index(DEFAULT_CATALOG, embeddings),
                       model=quality),
        ActionAgent(build_tool_index(READ_TOOLS + WRITE_TOOLS, embeddings),
                    desk=ServiceDesk(), idem_store=IdempotencyStore(redis_client),
                    model=fast, top_k=settings.tool_top_k,
                    pending=PendingActions(redis_client)),
        Router(embeddings, min_score=settings.router_min_score,
               min_margin=settings.router_min_margin),
        cache=SemanticCache(embeddings, backend=RedisBackend(redis_client),
                            threshold=settings.cache_similarity_threshold),
        get_customer=lambda cid: demo,
        remember=lambda *args: None,      # measured separately, below
    )
    return assistant, fast


def _report(label, reply, secs):
    calls = [c for c in LOG if c["call"] != "embed"]
    embeds = len(LOG) - len(calls)
    print(f"\n{label}  ({secs:.2f}s, {embeds} embeds)  -> {reply.text[:70]!r}")
    for c in calls:
        print(f"    {c['call']:8} in={c['tokens_in']:>6}  "
              f"out={c['tokens_out']:>4}  {c['secs']}s")
    if not calls:
        print("    no model call")
    LOG.clear()


def _measure_memory():
    """One exchange handed to Mem0 with the chapter's own settings, in a
    temporary folder so no real customer memory is touched."""
    from mem0 import Memory

    from src.config import settings
    with tempfile.TemporaryDirectory() as folder:
        memory = Memory.from_config({
            "llm": {"provider": "ollama",
                    "config": {"model": settings.fast_model,
                               "ollama_base_url": settings.ollama_base_url}},
            "embedder": {"provider": "ollama",
                         "config": {"model": settings.embedding_model,
                                    "ollama_base_url": settings.ollama_base_url}},
            "vector_store": {"provider": "faiss",
                             "config": {"path": folder,
                                        "collection_name": "measure",
                                        "embedding_model_dims": 768}},
        })
        original = memory.llm.generate_response

        def counted(*args, **kwargs):
            messages = kwargs.get("messages") or args[0]
            chars = sum(len(m.get("content", "")) for m in messages)
            started = time.time()
            out = original(*args, **kwargs)
            print(f"    mem0     prompt of {chars} characters  "
                  f"{time.time() - started:.2f}s")
            return out

        memory.llm.generate_response = counted
        for message in ["I travel to Singapore for work most months",
                        "Actually I moved to Dubai last month"]:
            print(f"\nremember {message!r}")
            memory.add([{"role": "user", "content": message},
                        {"role": "assistant", "content": "Noted."}],
                       user_id="measure")


def main():
    assistant, fast = _build()
    fast.invoke("hello")                     # load the model before timing
    LOG.clear()

    history = ["Customer: which cards do I have?",
               "Assistant: You have card-1 (debit) and card-2 (travel credit card)."]
    runs = [
        ("question, first time", "what is the interest free period on the travel card?", [], False),
        ("same question again", "what is the interest free period on the travel card?", [], False),
        ("question the documents cannot answer", "what will the stock market do next year?", [], False),
        ("advice", "which card is best for me? I travel abroad a lot", [], False),
        ("block a card, asks first", "I lost my card, please block it", [], False),
        ("block a card, confirmed", "I lost my card, please block it", [], True),
        ("follow-up, asks first", "block the second one, it was stolen", history, False),
        ("follow-up, confirmed", "block the second one, it was stolen", history, True),
    ]
    for label, message, turns, confirmed in runs:
        started = time.time()
        reply = assistant.handle("demo", message, history=turns,
                                 confirmed=confirmed)
        _report(label, reply, time.time() - started)

    _measure_memory()


if __name__ == "__main__":
    main()
