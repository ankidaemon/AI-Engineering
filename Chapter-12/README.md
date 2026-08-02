# Chapter 12: Running AI Systems in Production

Runnable code for Chapter 12, the **Real Time Intelligence Monitor**. It watches
topics across the web, analyses new content with a LangGraph pipeline, streams
short briefs over Server Sent Events, records everything in LangSmith, and keeps
cost and reliability under control.

The chapter (`chapter-12.md`) explains the ideas in prose and shows trimmed code.
This repo holds the full, tested implementation. The whole test suite runs
offline: no model server, no database, no network, using fakes and injected
clients throughout.

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m pytest -q          # 71 tests, all offline
```

To run the live application you also need Ollama and Postgres. Postgres is not
optional any more: it holds the brief vectors, the LangGraph checkpoints and the
conversation ownership table.

```bash
docker-compose up -d         # Ollama and Postgres (pgvector/pgvector:pg16)
ollama pull llama3.1:8b && ollama pull llama3.1:70b && ollama pull nomic-embed-text
cp .env.example .env         # API_KEYS must be set or every request gets a 401
uvicorn src.api:app --host 0.0.0.0 --port 8095 --reload
```

Every request that touches customer data carries an API key, and the customer id
comes from that key alone:

```bash
curl -N -s -X POST localhost:8095/analyze/stream \
  -H "X-API-Key: dev-key-acme" -H "Content-Type: application/json" \
  -d '{"url":"https://en.wikipedia.org/wiki/Artificial_Intelligence_Act","topic":"AI regulation"}'
```

The response carries an `X-Conversation-Id` header. Send it back as
`conversation_id` to continue that conversation; send another customer's and you
get a 403.

Test defaults in `src/config.py` keep the suite offline, so `pytest` needs no
`.env` and no database. Copy `.env.example` to `.env` for anything live.

## Where each idea lives

| Chapter section | Module | What it does |
|-----------------|--------|--------------|
| I.5 Cost tracking | `src/observability/tracing.py` | `CostTracker`, `traced`, `log_user_feedback` (injectable client) |
| I.6 Evaluation | `src/observability/evaluation.py` | Pure evaluators + `EvaluationDatasetManager` |
| I.7 Monitoring | `src/observability/monitoring.py` | `check_thresholds` (pure) + `ProductionMonitor` |
| II.1 Streaming | `src/streaming/stream_handler.py` | SSE formatting + `StreamingResponseHandler` |
| II.2 Persistence | `src/persistence/checkpointer.py` | memory / sqlite / postgres factory |
| II.3 Isolation | `src/tenancy/auth.py` | API key to customer id, the only place a customer id is decided |
| II.3 Isolation | `src/tenancy/conversations.py` | Server minted thread ids, ownership checked on every reuse |
| II.4 Circuit breaker | `src/resilience/circuit_breaker.py` | Closed / open / half open with fallback |
| III FireCrawl | `src/ingestion/firecrawl_loader.py` | Scrape to `Document` + content hash |
| III Content monitor | `src/ingestion/content_monitor.py` | Poll, deduplicate by hash, index new content |
| IV.2 Estimation | `src/cost/estimator.py` | Token count, per request and monthly cost |
| IV.3 Budget cap | `src/cost/budget.py` | `BudgetGuard`, hard rolling window cap per key |
| IV.4 Throttling | `src/cost/throttle.py` | Token bucket + concurrency ceiling |
| IV.5 Outages | `src/cost/resilient_call.py` | Backoff with jitter + fallback chain |
| V Project | `src/monitor/` | `state.py`, `nodes.py`, `graph.py` (all injectable) |
| V Vector memory | `src/vectorstores/pgvector_store.py` | One pgvector table; `for_customer` is the only way in |
| V API | `src/api.py` | FastAPI app, SSE streaming, metrics, feedback |

## Tests

| File | Covers |
|------|--------|
| `tests/test_cost.py` | Estimation, budget caps, throttling, resilient calls |
| `tests/test_circuit_breaker.py` | State transitions and fallback |
| `tests/test_observability.py` | Cost tracker, feedback, thresholds, evaluators |
| `tests/test_streaming.py` | SSE formatting and the streaming handler |
| `tests/test_ingestion.py` | FireCrawl loader and per customer dedup, with fakes |
| `tests/test_tenancy.py` | Auth, conversation ownership, and that no customer's vectors reach another |
| `tests/test_monitor_graph.py` | The whole pipeline end to end with fake models |

## Design notes

Everything that touches an outside service (the model, LangSmith, FireCrawl, the
database) takes that dependency as an injected argument. Production passes the
real client; tests pass a fake. That is what makes the suite fully offline and
what keeps the modules easy to reason about. See `chapter-12.md` for the full
explanation of each piece.
