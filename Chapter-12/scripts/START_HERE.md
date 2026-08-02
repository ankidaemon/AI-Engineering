# Chapter 12 — start the system and take LangSmith screenshots

One file, everything you need. The setup below is already done on this machine; you
only need the "Start from cold" and "Take the screenshots" sections when you come back.

Run everything from the repo root:

```bash
cd /Users/ankitm/Music/git/AI-Engineering/Chapter-12
```

---

## What is already set up (no need to redo)

- **Ollama** installed via Homebrew.
- **Models pulled:** `llama3.1:8b` (fast) and `nomic-embed-text` (embeddings).
  `llama3.1:70b` (quality) is **not** finished downloading (the pull was paused).
- **`.env`** is created and filled in (gitignored, keys stay local):
  - `LANGSMITH_API_KEY` set, `LANGSMITH_TRACING=true`,
    `LANGSMITH_PROJECT=real-time-intelligence-monitor`
  - `FIRECRAWL_API_KEY` set
  - `QUALITY_MODEL=llama3.1:8b` (lighter, so it runs now; see "Higher quality" below)
  - `API_KEYS=dev-key-acme:acme,dev-key-globex:globex` — **required**. With no
    keys configured every request returns 401, on purpose: there is no anonymous
    customer to fall back to.
- **Python deps** installed in `.venv`. Offline tests pass (71).
- The bug that crashed `generate_brief` on model output containing `{`/`}` is fixed,
  with a regression test.

---

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

## Generate runs to screenshot

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

---

## Take the screenshots

> **Already done (2026-07-30).** All eleven screenshots are captured in
> `Chapter-12/screenshots/`, with a file-by-file caption table in
> `Chapter-12/screenshots/README.md`. Read that README before writing captions: it records
> three things the images do not show on their own (LangSmith reports $0 cost for local
> Ollama models, tags exist only on the older seeded runs, and how the golden dataset was
> built). The section below is what to repeat if you want fresher or better runs.

Open https://smith.langchain.com, select project **real-time-intelligence-monitor**.
Set the browser to light mode and a clean width. Capture these eight:

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

### Concrete targets already in the project (checked 2026-07-30)

The project holds 11 root runs. **Set the time filter to 7 days** — the default 1 day hides
everything except the four runs from this morning, including both feedback runs.

Base URL:
`https://smith.langchain.com/o/d81e137c-5cb8-4dc3-9552-89482fbdeecc/projects/p/03be72dd-b6ac-4648-ad08-ef32ecabdca9`

Append `?timeModel=%7B%22duration%22%3A%227d%22%7D&runview=runs` for the 7 day run table,
and `&peek=<run-id>` to open a specific run.

| Shot | Run to open | Why this one |
|---|---|---|
| 2, 3 | `019fb20c-009c-79e2-9068-aadcb0e50702` | today's real run, 4,667 tokens, full node tree |
| 4 (tags/metadata) | `019f8e2b-e0a7-71b3-ac8c-dfabdabc2193` | has `topic:cyber` + `chapter-12` tags and `monitor_id` |
| 5 (error) | `019fb213-39bb-7681-8dab-b54053aa433b` | today's Ollama-refused run; red child `ChatOllama` inside |
| 6 (feedback) | `019f8e42-...b0be` (score 1.0) and `019f8e2b-e0a7-...` (score 0.0) | the only two runs carrying `user_score` |
| 8 (dataset) | any good run | no dataset exists yet; create `intel-monitor-golden` via **Add to Dataset** |

Runs created before 2026-07-30 12:48 are named `LangGraph` and carry no tags: `/analyze/stream`
only started naming and tagging its runs when `run_config` was added to `src/api.py`. Anything
you run from now on arrives as `intel::<topic>` with `chapter-12`, `topic:<slug>` and
`customer:<id>` tags, and `conversation_id` / `customer_id` / `topic` / `content_url` metadata.
Runs from 2026-07-30 carry the older `monitor_id` metadata key instead of `conversation_id`,
so `05-tags-metadata.png` shows the earlier shape.

Caption crib sheet:
- 1: "Every request is recorded the moment tracing is on, no code changes."
- 2: "One trace, fully expanded: relevance, retrieval, analysis, brief, storage."
- 3: "Token counts come for free; the CostTracker turns them into a running cost."
- 5: "A model call failed (red), but the run completed because the node fails open."
- 6: "A user rating attached to the exact run it refers to."
- 7: "Volume, error rate, latency percentiles, and cost — what the thresholds alert on."
- 8: "A golden dataset grown from real production runs."

---

## Higher quality briefs (optional, for the final screenshots)

The 8B model works but its briefs are rough. For better output:

```bash
ollama pull llama3.1:70b          # resumes where the paused pull left off (~40 GB)
```

Then set `QUALITY_MODEL=llama3.1:70b` in `.env`, re-export
(`set -a && source .env && set +a`), and restart the API. Inference is slower (tens of
seconds per brief) but the briefs are much better.

---

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
