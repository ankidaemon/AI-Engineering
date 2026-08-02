# Chapter 12 — start the system 

One file, everything you need. 

Run everything from the repo root:

## Start from cold (3 steps)

**1. Start Ollama and Postgres** (models, plus the store that holds vectors,
checkpoints and conversation ownership):

```bash
brew services start ollama
sleep 3 && curl -s localhost:11434/api/tags >/dev/null && echo "ollama up"

docker compose up -d postgres          # pgvector/pgvector:pg16
```

**2. Export the environment into this shell** (the LangSmith SDK reads real OS env
vars, not just `.env`, so this export is required for tracing to work; `API_KEYS`
must be set here too or every request is rejected):

```bash
set -a && source .env && set +a
echo "$LANGSMITH_TRACING $LANGSMITH_PROJECT"   # -> true real-time-intelligence-monitor
echo "$API_KEYS"                              # -> dev-key-acme:acme,dev-key-globex:globex
```

**3. Start the API** (leave it running in this terminal):

```bash
.venv/bin/uvicorn src.api:app --host 0.0.0.0 --port 8095
# health check from another terminal:  curl -s localhost:8095/health
```

Traces start flowing to LangSmith the moment the pipeline makes a model call.

---

### A. Real scrape-driven runs through the API (the full front door)

Each call scrapes a live page, runs the pipeline, and streams the brief. Use `-N` to
watch the SSE events. Replace URLs/topics as you like; any public article works.

Every request needs `X-API-Key`. The customer id comes from that key alone, so
using two different keys is what puts two customers in the project.

```bash
# On-topic -> full brief
curl -N -s -X POST localhost:8095/analyze/stream \
  -H "X-API-Key: dev-key-acme" -H "Content-Type: application/json" \
  -d '{"url":"https://en.wikipedia.org/wiki/Artificial_Intelligence_Act","topic":"AI regulation"}'

# A second topic
curl -N -s -X POST localhost:8095/analyze/stream \
  -H "X-API-Key: dev-key-acme" -H "Content-Type: application/json" \
  -d '{"url":"https://en.wikipedia.org/wiki/Semiconductor","topic":"semiconductor supply chain"}'

# Off-topic for the topic -> stops early at the relevance gate
curl -N -s -X POST localhost:8095/analyze/stream \
  -H "X-API-Key: dev-key-acme" -H "Content-Type: application/json" \
  -d '{"url":"https://en.wikipedia.org/wiki/Association_football","topic":"AI regulation"}'

# A second customer, so the runs carry customer:globex and see none of acme's briefs
curl -N -s -X POST localhost:8095/analyze/stream \
  -H "X-API-Key: dev-key-globex" -H "Content-Type: application/json" \
  -d '{"url":"https://en.wikipedia.org/wiki/Cloud_computing","topic":"cloud security"}'
```

Run five or six across different topics so the charts have variety.

### A2. Show an isolation boundary refusing a request

The stream returns an `X-Conversation-Id` header. Replay it as the wrong customer
and you get a 403, which is the screenshot-worthy proof that thread ids are not
guessable keys:

```bash
CONV=$(curl -sS -D - -o /dev/null -X POST localhost:8095/analyze/stream \
  -H "X-API-Key: dev-key-acme" -H "Content-Type: application/json" \
  -d '{"url":"https://en.wikipedia.org/wiki/Semiconductor","topic":"chips"}' \
  | awk -F': ' '/[Xx]-[Cc]onversation-[Ii]d/{print $2}' | tr -d '\r')

curl -s -o /dev/null -w '%{http_code}\n' -X POST localhost:8095/analyze/stream \
  -H "X-API-Key: dev-key-globex" -H "Content-Type: application/json" \
  -d "{\"url\":\"https://en.wikipedia.org/wiki/Semiconductor\",\"topic\":\"chips\",\"conversation_id\":\"$CONV\"}"
# -> 403
```

### B. Attach user feedback to a run (for the feedback screenshot)

The stream does not print the run id, so take it from the LangSmith UI: open a run,
copy its **Run ID**, then:

```bash
curl -s -X POST localhost:8095/feedback \
  -H "X-API-Key: dev-key-acme" -H "Content-Type: application/json" \
  -d '{"run_id":"PASTE-RUN-ID","score":1.0,"comment":"Clear and actionable."}'
```

Do one `score:1.0` and one `score:0.0` so both show up.

### C. Read the live metrics (what the monitoring view charts)

```bash
curl -s -H "X-API-Key: dev-key-acme" localhost:8095/metrics | .venv/bin/python -m json.tool
```

### D. To force a real errored run (for the errored-run screenshot)

Stop Ollama for a moment, fire one call, then restart it. The model call genuinely
fails and is recorded red; the run still completes because the node fails open.

```bash
brew services stop ollama
curl -N -s -X POST localhost:8095/analyze/stream \
  -H "X-API-Key: dev-key-acme" -H "Content-Type: application/json" \
  -d '{"url":"https://en.wikipedia.org/wiki/Cloud_computing","topic":"cyber threats"}'
brew services start ollama
```


| # | View (where) | Show | Chapter section |
|---|---|---|---|
| 1 | Project > Runs (table) | run list: name, latency, tokens, status columns; a stopped-early row | I.2 four tools |
| 2 | Open one relevant run, expand tree | nested nodes check_relevance > retrieve_context > analyze_content > generate_brief > store_brief; expand one LLM call to show prompt + completion | I.3 tracing |
| 3 | Same run, header | total latency, input/output tokens, per-node timing | I.5 cost tracking |
| 4 | Run > Metadata / Tags | the `topic:*` tags and `monitor_id` metadata | I.3 tracing |
| 5 | Filter Status = Error, open one | red errored child run inside a run that still completed | I.7 monitoring |
| 6 | The run you gave feedback | the `user_score` feedback (a 1.0 and a 0.0 with comment) | I.5 / I.6 |
| 7 | Project > Monitor (charts) | trace volume, error rate, p50/p95 latency, token/cost trend | I.7 monitoring, alerts |
| 8 | On a good run: Add to Dataset > `intel-monitor-golden`, then Datasets & Experiments | dataset examples promoted from real runs (inputs vs expected brief) | I.6 evaluation |

The project holds 11 root runs. **Set the time filter to 7 days** — the default 1 day hides
everything except the four runs from this morning, including both feedback runs.



## Stop everything

```bash
# stop the API: Ctrl-C in its terminal, or:
pkill -f "uvicorn src.api"
brew services stop ollama
```

---

## Troubleshooting

- **Nothing in LangSmith.** You forgot step 2 in the same terminal as the API.
  `LANGSMITH_TRACING` and `LANGSMITH_API_KEY` must be exported, not only in `.env`.
  Check with `echo "$LANGSMITH_TRACING"` and restart uvicorn.
- **`/analyze/stream` returns 422.** FireCrawl could not scrape that URL; try another
  public article. Confirm `FIRECRAWL_API_KEY` is set (`echo "$FIRECRAWL_API_KEY"`).
- **Ollama connection refused.** `brew services start ollama` must be up before the API.
- **70B is very slow or swaps hard.** Set `QUALITY_MODEL=llama3.1:8b`, re-export, restart.
- **Every request returns 401.** `API_KEYS` is unset or was not exported. It has
  no default; see step 2.
- **Every request returns 403.** You sent a `conversation_id` belonging to a
  different key. Omit it to start a fresh conversation.
- **Startup fails on the vector store.** `docker compose up -d postgres` has not
  run, or `POSTGRES_URL` points somewhere without the `vector` extension.
- **Sanity check anytime:** `.venv/bin/python -m pytest -q` (71 tests, fully offline).
