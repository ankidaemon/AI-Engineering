# Chapter 13 — Multi-Agent Banking Assistant

A banking assistant with three separated
responsibilities behind one router: answering questions from an in-house
knowledge base (grounded, cited, willing to decline), recommending products
by combining need, profile, holdings, and remembered facts, and taking real
actions through read/write tools — with the same tools exposed over MCP for
any other assistant in the bank, Mem0 remembering each customer across
visits, and Celery workers with Redis keeping the slow work off the path a
customer waits on.

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m pytest -q          # 100 tests, fully offline: no model, no broker, no network
```

To run the whole system (Redis + Ollama + API + a Celery worker):

```bash
docker compose up --build
# then open the chat window:
open http://localhost:8100/
# scale background capacity:
docker compose up --scale worker=4
```

Or locally, with Redis and Ollama already running:

```bash
uvicorn src.api:app --port 8100
celery -A src.workers.celery_app.app worker --loglevel=info
python -m src.mcp_server     # the banking tools over MCP (stdio), for other assistants
```

Both directions of the protocol, in one command each:

```bash
python -m src.mcp_server     # exposing: the bank's tools, for anyone to call
python -m src.mcp_client     # consuming: list FireCrawl's tools, scrape one page
```

To see what each kind of request costs, in model calls, tokens and time
with Ollama running:

```bash
python -m src.measure_cost
```

`src.mcp_client` needs `FIRECRAWL_API_KEY` in `.env`, because unlike the bank's
own server it is talking to somebody else's, over HTTP, on the internet. The
offline tests cover it with the transport injected, so `pytest` still needs no
key and no network.

## The chat window

`http://localhost:8100/` is the assistant itself, served by the same process
as the API from `web/`. Plain HTML, CSS and JavaScript, no build step and no
node, because everything in this book has to run offline on your own machine.

It is built to make the system visible while you use it. Every reply is
labelled with the part that produced it, so the router's decision is on screen
rather than in a log. A knowledge answer lists its sources. An action that
changes something stops and asks, and only a real click sends the request back
with `confirmed`, which is the consent the guard in `src/tools/action_agent.py`
is waiting for. A completed action shows the reference number the customer
keeps. Cached answers are marked, and the header carries the same `/health`
status the operators read.

Try it:

```bash
# a question (knowledge base)
curl -X POST localhost:8100/chat -H "Content-Type: application/json" \
  -d '{"customer_id":"demo","message":"what is the interest free period on the travel card?"}'

# an action (needs confirmation, then acts)
curl -X POST localhost:8100/chat -H "Content-Type: application/json" \
  -d '{"customer_id":"demo","message":"I lost my card, please block it","confirmed":true}'

# enqueue re-indexing (workers do the slow part)
curl -X POST localhost:8100/ingest -H "Content-Type: application/json" \
  -d '{"doc_ids":["card-faq","fee-schedule","card-terms"]}'
```

## Module map (chapter section → code)

| Chapter section | Module |
|---|---|
| The MCP server (tools over the protocol, guards server-side) | `src/mcp_server.py` |
| The MCP client (consuming FireCrawl's server over HTTP) | `src/mcp_client.py` |
| Long-term memory (Mem0 behind a seam, per-customer namespace) | `src/memory/service.py` |
| The router (intent retrieval over exemplar utterances, no model call) | `src/router.py` |
| How a request moves through the system | the wiring in `src/assistant.py` + `src/api.py` |
| The chat window (agent labels, sources, confirmation, reference ids) | `web/index.html`, `web/app.js`, `web/styles.css` |
| Loaders, shared metadata (effective dates) | `src/knowledge/loaders.py` |
| Splitting, freshness, `reindex` | `src/knowledge/ingest.py` |
| FAISS index with `replace(doc_id, …)` | `src/vectorstores/faiss_store.py` |
| Grounded, cited agent that declines | `src/knowledge/agent.py` |
| Catalog described for retrieval, offers | `src/products/catalog.py` |
| Advisor: query, filter, explain, offer rules | `src/products/advisor.py` |
| Read vs write ToolSpec | `src/tools/base.py`, `src/tools/read_tools.py`, `src/tools/write_tools.py` |
| Service desk (references the customer keeps) | `src/tools/service_desk.py` |
| Tool selection + follow-up contextualization | `src/tools/selector.py` |
| Idempotency (keys in Redis) | `src/tools/idempotency.py` |
| Confirmation, restraint | `src/tools/action_agent.py` |
| Celery app (Redis broker) | `src/workers/celery_app.py` |
| Background tasks: re-indexing, batch fan-out, memory writes | `src/workers/tasks.py` |
| Semantic cache with the enforced boundary | `src/cache/semantic_cache.py` |
| shared cosine index | `src/vectorstores/cosine_index.py` |
| Assistant wiring | `src/assistant.py` |
| API + honest health check | `src/api.py` |
| What each request costs: model calls, tokens, time (needs Ollama) | `src/measure_cost.py` |
| Configuration | `src/config.py` |

## Design notes

- **Dispatch never spends a model call.** The router picks the kind of work by
  retrieving the nearest exemplar utterance (weak or tied matches fall to the
  safe "question" path), and the action agent picks its tool by retrieving over
  tool descriptions — the same intent-retrieval idea at two altitudes. The only
  LLM calls are the ones whose output the customer reads.
- **Memory reads on the request path, writes off it.** Recall is a vector
  search scoped to one customer and folded into the advisor's query; the
  finished exchange is queued and a worker hands it to Mem0, whose extraction
  (a fast model call) never runs while a customer waits. The customer-id
  namespace is enforced inside `MemoryService`, not left to callers, and the
  Mem0 client is private to that class so there is no unscoped call to make.
- **The MCP door shares the chat door's gate.** Every write exposed over the
  protocol flows through the same `execute_write` (field checks, idempotency,
  the duplicate answer), and `block_card` demands an explicit `confirmed=True`
  — a server never relies on the client behaving.
- **The client knows no vendor.** `src/mcp_client.py` takes an address, a tool
  name, and a dict; FireCrawl appears in one factory and one demo. Discovery
  happens at runtime, so the twenty five tool names it can call are written
  nowhere in this repo. Compare Chapter 12, which reached the same capability
  through the vendor's SDK and a loader shaped around it.
- **Everything is injected.** Models, embeddings, the Redis client, the
  service desk, the Mem0 client, and the clock are constructor arguments with
  lazy production defaults, so every piece runs under test with fakes and
  offline.
- **The failure stories are tested.** Failure 1 (stale fee) →
  `test_replace_swaps_a_changed_document`; Failure 2 (recommended an owned
  product) → the advisor filter tests; Failure 3 (duplicate complaint) →
  the idempotency tests, plus `test_the_idempotency_gate_guards_the_protocol_door_too`;
  Failure 5 ("block the second one") → `test_follow_up_only_resolves_with_history`;
  Failure 6 (queue backlog) → batch fan-out in `test_tasks.py`; Failure 7
  (another customer's memories) → `test_recall_returns_only_this_customers_facts`.
- **The cache enforces its own boundary.** `SemanticCache.put` refuses
  customer-specific answers and write results, so the safety rule does not
  depend on every caller remembering it. The cache and the memory are
  opposites: shared and never personal versus personal and never shared.
- **Sample corpus** in `data/documents/` (FAQ JSON, fee schedule CSV, terms
  markdown) is what `/ingest` and the tests' smoke path load.
