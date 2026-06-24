# AI Workflow Designer

A document analysis and decision-support system built with **LangChain** and **LangGraph**, running entirely on open models via **Ollama** (Llama 3.1). It is the hands-on project for **Chapter 10 — LangChain and LangGraph: Building Modular, Stateful AI Applications**.

This README is self-contained: everything you need to set up, run, understand, and extend the project lives here and in the code comments. The book chapter explains the *why*; this repository is the *how*.

---

## What This Project Is

You hand the system a document. It:

1. **Ingests** and cleans the text.
2. **Classifies** it (legal / technical / financial / general) and gauges complexity and stakes.
3. **Analyzes** it with a domain-specific chain that emits structured fields.
4. **Assesses risk**, producing risk flags, an overall risk level, and decision options.
5. **Pauses for human review** when the risk warrants it (a true interrupt/resume, not a poll).
6. **Loops** back through analysis if the reviewer asks for revisions — bounded by a hard cap.
7. **Finalizes** a structured report (dict + markdown), deterministically.

After analysis you can hold a **multi-turn Q&A conversation** about the report, with memory that compresses as it grows.

The point of the project is not document analysis per se — it is to show how **LangChain** composes individual LLM steps and how **LangGraph** orchestrates them into a *stateful, cyclical, human-in-the-loop* workflow that plain chains cannot express.

---

## What You'll Build & Learn (End-to-End)

| Stage | Concept | Where it lives |
|-------|---------|----------------|
| 1. Models | Two-tier model strategy (fast 8B vs. quality 70B) behind one interface | `src/models.py` |
| 2. Prompts + Parsers | `ChatPromptTemplate` + `JsonOutputParser` with Pydantic schemas | `src/chains/*` |
| 3. Chains (LCEL) | `prompt \| model \| parser` composition; the `Runnable` protocol | `src/chains/*` |
| 4. State | A typed `WorkflowState` with an `operator.add` reducer for messages | `src/state.py` |
| 5. Nodes | Pure state→partial-state functions that never raise | `src/nodes/*` |
| 6. Graph | Conditional edges, cycles, `interrupt_before`, checkpointing | `src/graph.py` |
| 7. Human-in-the-loop | Pause → `update_state` → resume across a checkpoint | `src/conversation.py` |
| 8. Memory | `ConversationSummaryBufferMemory` for bounded Q&A history | `src/memory/conversation_memory.py` |
| 9. Serving | FastAPI over the conversation layer | `src/api.py` |
| 10. Self-critique | A generate→evaluate→retry wrapper (LCEL form of the graph's loop) | `src/chains/self_eval_chain.py` |

---

## Architecture

```
                         POST /analyze
                              │
                              ▼
        ┌──────────────────────────────────────────────────────┐
        │                  LangGraph workflow                    │
        │                                                        │
        │   START → ingest → classify                            │
        │                       │                                │
        │      ┌────────────────┼─────────────────┬──────────┐  │
        │      ▼                ▼                 ▼          ▼  │
        │  legal_analysis  technical_…     financial_…  general │
        │      └────────────────┴─────────────────┴──────────┘  │
        │                       ▼                                │
        │                risk_assessment                         │
        │                       │                                │
        │           requires_human_review? ──no──► finalize → END│
        │                       │ yes                            │
        │                       ▼                                │
        │             human_review_gate  ◄── interrupt_before    │
        │              │              │                          │
        │       approved        needs_revision                  │
        │              │              │                          │
        │              ▼              ▼                          │
        │          finalize     re_classify → classify (loop,    │
        │              │          capped at MAX_REVISIONS)        │
        │              ▼                                          │
        │             END                                        │
        └──────────────────────────────────────────────────────┘
                              │
            checkpointer (SQLite) persists state across the pause
```

**LangChain vs. LangGraph here:** each analysis/classification/risk step is a LangChain LCEL chain (linear, stateless, composable). LangGraph wraps them in a graph that adds the things chains can't do — persistent state, conditional routing, a revision *cycle*, and a human-review *pause*.

---

## Project Structure

```
Chapter-10/
├── src/
│   ├── config.py                  # pydantic-settings configuration
│   ├── models.py                  # get_fast_model / get_quality_model (Ollama)
│   ├── state.py                   # WorkflowState TypedDict + schema version
│   ├── chains/                    # LangChain LCEL chains (stateless)
│   │   ├── classification_chain.py
│   │   ├── analysis_chains.py     # legal / technical / financial / general
│   │   ├── risk_chain.py
│   │   ├── synthesis_chain.py     # optional executive-narrative helper
│   │   └── self_eval_chain.py     # generate → evaluate → retry
│   ├── nodes/                     # LangGraph nodes (stateful, delegate to chains)
│   │   ├── ingestion.py
│   │   ├── classification.py
│   │   ├── analysis.py
│   │   ├── risk_assessment.py
│   │   ├── human_review.py        # the interrupt gate
│   │   ├── re_analysis.py         # revision loop
│   │   └── finalization.py        # deterministic report assembly
│   ├── memory/
│   │   └── conversation_memory.py # summary-buffer (+ optional vector-store) memory
│   ├── graph.py                   # graph assembly, routing, checkpointer
│   ├── conversation.py            # stateful wrapper: analyze / review / ask
│   └── api.py                     # FastAPI interface
├── tests/                         # run offline — no model server needed
│   ├── test_chains.py
│   ├── test_nodes.py
│   └── test_graph.py
├── data/                          # SQLite checkpoints, vector stores (gitignored)
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── .env.example
```

---

## Setup

### 1. Python environment

```bash
cd Chapter-10
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Ollama + models

```bash
ollama serve                      # start the model server
ollama pull llama3.1:8b           # fast model (required)
ollama pull llama3.1:70b          # quality model (needs a capable GPU/host)
```

> No 70B-class hardware? Point both tiers at the 8B model: set `ADVANCED_MODEL=llama3.1:8b` in `.env`. Quality drops but the full workflow runs.

### 3. Configuration

```bash
cp .env.example .env              # optional — every value has a default
```

### 4. Data directory

```bash
mkdir -p data                     # holds the SQLite checkpoint DB
```

---

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `PRIMARY_MODEL` | `llama3.1:8b` | Fast model — classification, routing, history summarization |
| `ADVANCED_MODEL` | `llama3.1:70b` | Quality model — analysis, risk, Q&A |
| `CHECKPOINT_DB_PATH` | `./data/conversations.db` | LangGraph SQLite checkpoint store |
| `CHROMA_PERSIST_DIR` | `./data/chroma_memory` | Vector-store memory (optional strategy) |
| `MEMORY_MAX_TOKEN_LIMIT` | `3000` | Summary-buffer compression threshold |
| `MAX_REVISIONS` | `3` | Hard cap on human-review revision loops |
| `LANGCHAIN_TRACING_V2` | `false` | Enable LangSmith tracing (off by default; see Failure 4) |
| `LANGCHAIN_API_KEY` | — | LangSmith API key |
| `LANGCHAIN_PROJECT` | `ai-workflow-designer` | LangSmith project name |

---

## Running

```bash
uvicorn src.api:app --host 0.0.0.0 --port 8080 --reload
```

**Analyze a document:**
```bash
curl -X POST http://localhost:8080/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "document_text": "SERVICE AGREEMENT\n\nThis agreement is between Acme Corp (\"Provider\") and XYZ Ltd (\"Client\").\n\nSection 1: Services\nProvider agrees to deliver software development services per Schedule A.\n\nSection 2: Payment\nClient agrees to pay $50,000 per month, net 30 days...",
    "document_id": "CONTRACT-2024-001"
  }' | python -m json.tool
```

**If `status` is `awaiting_review`, submit a decision (using the returned `session_id`):**
```bash
curl -X POST http://localhost:8080/review \
  -H "Content-Type: application/json" \
  -d '{"session_id": "<session_id>", "decision": "approved"}' | python -m json.tool
```

**Ask follow-up questions:**
```bash
curl -X POST http://localhost:8080/ask \
  -H "Content-Type: application/json" \
  -d '{"session_id": "<session_id>", "question": "What is the biggest risk and how should we mitigate it?"}' | python -m json.tool
```

### Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/analyze` | Submit a document; returns the report or `status="awaiting_review"` |
| `POST` | `/review` | Submit a human decision (`approved` / `needs_revision`) and resume |
| `POST` | `/ask` | Ask a follow-up question about the current report |
| `GET` | `/session/{id}/state` | Inspect a session's workflow state |
| `GET` | `/health` | Liveness + Ollama reachability |

### Docker

```bash
docker compose up -d ollama
docker compose exec ollama ollama pull llama3.1:8b
docker compose up app           # serves on http://localhost:8080
```

---

## Testing

```bash
pytest -q
```

The tests run **offline** — no Ollama required. Pure-logic nodes (ingestion, finalization, routing) are tested directly; LLM-backed nodes and the self-evaluation loop are tested with mocked chains.

---

## Design Notes & Production Lessons

These mirror Chapter 10, Section VI (Known Production Failures) and are baked into the code:

- **Bounded cycles.** Every loop has a termination condition independent of model output. The revision loop is capped by `MAX_REVISIONS` in `route_after_human_review` (Failure 1).
- **Bounded memory.** Q&A uses `ConversationSummaryBufferMemory`, never unbounded buffer memory (Failure 2).
- **Defensive nodes.** Nodes catch their own exceptions, record them in `errors`, and return safe defaults instead of raising; unknown classifications fall back to `general` (Failure 3).
- **Tracing off by default.** `LANGCHAIN_TRACING_V2=false`; enable deliberately and sample/async-upload in production (Failure 4).
- **Schema versioning.** `WorkflowState` carries `state_schema_version`; the ingest node detects stale checkpoints (Failure 5).
- **Prompt-injection framing.** Analysis prompts wrap untrusted document text in `<document>` tags with explicit injection-resistance rules (Failure 6).
- **Robust checkpointer.** `graph.py` builds a real `SqliteSaver` from an explicit connection (avoiding the `from_conn_string` context-manager pitfall) and falls back to an in-memory saver if SQLite is unavailable.

### A note on the stack

The book's snippets target the pinned versions in `requirements.txt`. This codebase makes a few faithful corrections for them: it uses **native Pydantic v2** (`from pydantic import BaseModel`) rather than the deprecated `langchain_core.pydantic_v1` shim, adds the **`langgraph-checkpoint-sqlite`** and **`pydantic-settings`** packages the snippets assume, and centralizes the two checkpointer concerns in one helper.
```
