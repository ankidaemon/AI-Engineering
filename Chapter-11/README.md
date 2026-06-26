# Dynamic Document Reader

An adaptive, agent-based system for ingesting and analyzing complex legal and
technical documents, built with **LangChain** and **LangGraph** and running
entirely on open models via **Ollama** (Llama 3.1). It is the hands-on project for
**Chapter 11 — Advanced LangChain and LangGraph Techniques: Custom Agents,
Advanced Retrieval, Multi-Agent Systems, and Production Patterns**.

This README is self-contained: everything you need to set up, run, understand, and
extend the project lives here and in the code comments. The book chapter explains
the *why* in plain language; this repository is the runnable *how*.

> **Relationship to Chapter 10.** Chapter 10's project followed a *fixed* workflow
> you designed in advance (orchestration). This project lets the model *decide its
> own path* — which tool to call, in what order, when it is done (agency). If you
> have not read Chapter 10's `AI Workflow Designer`, start there; this builds on it.

---

## What This Project Is

You upload a document. The system:

1. **Ingests** it — loads (PDF / DOCX / HTML / TXT / CSV) with a fallback loader,
   classifies its type, splits it into overlapping chunks, and indexes it in FAISS.
2. **Routes** it to the right strategy — a ReAct *agent* with a domain toolkit for
   legal and technical documents; a cheaper direct-LLM path for financial/general.
3. **Analyzes** it — the agent reasons and calls tools (search, extract, compare)
   in whatever order this document needs, optionally critiquing and revising its
   own output (Reflection) for high-stakes work.
4. **Answers queries** — semantic search across everything indexed, with advanced
   retrieval (multi-query + contextual compression) layered in.

The point is not document analysis for its own sake. It is to show, in one working
system, the boundary between **orchestration** and **agency**, and the engineering
discipline — hard caps, discriminating tool descriptions, robust loading,
guarded retrieval — that turns a clever demo into something that survives
production.

---

## What You'll Build & Learn (End-to-End)

| Concept (chapter section) | Where it lives |
|---------------------------|----------------|
| ReAct agent: reason+act loop with a hard tool-call cap (§I) | `src/agents/react_agent.py` |
| Reflection agent: generate → critique → revise (§1.4) | `src/agents/reflection_agent.py` |
| Plan-and-execute agent + plan validation (§1.5) | `src/agents/plan_execute_agent.py` |
| Tools via `@tool`; structured tools via Pydantic schema (§II) | `src/tools/` |
| Toolkits: bundling related tools (§2.3) | `src/tools/document_toolkit.py` |
| Robust loading: pypdf → pdfminer → OCR fallback (§III) | `src/loaders/advanced_document_loader.py` |
| FAISS local vector store (§4.1) | `src/vectorstores/faiss_store.py` |
| Thread-safe FAISS writes (Failure 2) | `src/vectorstores/concurrent_faiss.py` |
| Chroma local vector database + collections (§4.2) | `src/vectorstores/chroma_store.py` |
| Four retrieval strategies (§4.3) | `src/retrieval/` |
| Supervisor multi-agent system + hard iteration cap (§V) | `src/agents/supervisor_agent.py` |
| Parallel specialist execution (§5.2) | `src/agents/parallel_agents.py` |
| Ingestion pipeline (§6.4) and analysis orchestrator (§6.5) | `src/pipeline/` |
| FastAPI serving (§6.6) | `src/api.py` |

---

## Architecture

```
                          POST /documents/upload
                                   │
                                   ▼
            ┌─────────────────────────────────────────────┐
            │            Ingestion pipeline                │
            │   load (fallback) → classify → chunk →       │
            │   stamp metadata → index into FAISS          │
            └─────────────────────────────────────────────┘
                                   │
                          POST /documents/analyze
                                   │
                                   ▼
            ┌─────────────────────────────────────────────┐
            │          Analysis orchestrator               │
            │   picks strategy by document type:           │
            │                                              │
            │   legal / technical ──► ReAct agent          │
            │        (+ optional Reflection)               │
            │            │  tools: search, extract,        │
            │            │  cross-reference, liability…     │
            │            ▼                                  │
            │   financial / general ──► direct LLM         │
            └─────────────────────────────────────────────┘
                                   │
        retrieval stack (shared by the agents' search tool):
        FAISS retriever → multi-query → contextual compression
```

**Orchestration vs. agency here:** the ingestion pipeline is fixed orchestration
(the steps never change). The analysis is agency — inside a ReAct loop the model
chooses which tools to call and when to stop, bounded by a hard cap.

---

## Project Structure

```
Chapter-11/
├── src/
│   ├── config.py                  # pydantic-settings configuration (incl. safety caps)
│   ├── models.py                  # get_fast_model / get_quality_model / get_embeddings
│   ├── state.py                   # TypedDict state shapes for each agent
│   ├── agents/
│   │   ├── react_agent.py         # ReAct loop + hard cap (_react_route)
│   │   ├── reflection_agent.py    # generate → critique → revise (_reflection_route)
│   │   ├── plan_execute_agent.py  # plan → execute → synthesize + validate_plan
│   │   ├── supervisor_agent.py    # supervisor + specialists (_supervisor_route)
│   │   └── parallel_agents.py     # RunnableParallel specialist fan-out
│   ├── tools/
│   │   ├── document_tools.py      # deterministic: word_count, extract_dates, readability
│   │   ├── retrieval_tools.py     # DocumentSearchTool, CrossReferenceTool (Pydantic schemas)
│   │   ├── legal_specific_tools.py# obligations / unusual clauses / liability (+ pure parsers)
│   │   ├── technical_tools.py     # API specs / dependencies / security / complexity
│   │   └── document_toolkit.py    # Legal & Technical toolkits
│   ├── loaders/
│   │   └── advanced_document_loader.py  # RobustPDFLoader + MultiFormatLoader
│   ├── vectorstores/
│   │   ├── faiss_store.py         # FAISS wrapper (injectable embeddings)
│   │   ├── concurrent_faiss.py    # thread-safe write wrapper (Failure 2)
│   │   └── chroma_store.py        # local persistent DB + collections (Section 4.2)
│   ├── retrieval/
│   │   ├── multi_query.py         # multi-query + filter_irrelevant_results (Failure 3)
│   │   ├── self_querying.py       # natural language → metadata filter
│   │   ├── contextual_compression.py  # + ReferencePreservingCompressor (Failure 4)
│   │   └── hyde.py                # HyDE + should_use_hyde gate (Failure 6)
│   ├── pipeline/
│   │   ├── document_processor.py  # ingestion pipeline
│   │   └── analysis_orchestrator.py  # strategy selection + retrieval stack
│   └── api.py                     # FastAPI interface
├── tests/                         # run OFFLINE — no model server needed
│   ├── test_tools.py
│   ├── test_loaders.py
│   ├── test_agents.py             # the hard-cap routing logic
│   ├── test_retrieval.py          # HyDE gate + multi-query filter
│   └── test_faiss.py              # FAISS with deterministic fake embeddings
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── .env.example
```

---

## Setup

### 1. Python environment

```bash
cd Chapter-11
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Ollama + models

```bash
ollama serve                      # start the model server
ollama pull llama3.1:8b           # fast model (required)
ollama pull nomic-embed-text      # embedding model (required, 768-dim)
ollama pull llama3.1:70b          # quality model (needs a capable GPU/host)
```

> **No 70B-class hardware?** Point the quality tier at the 8B model: set
> `QUALITY_MODEL=llama3.1:8b` in `.env`. Analysis quality drops, but every agent,
> tool, and endpoint still runs.

### 3. Configuration (optional)

```bash
cp .env.example .env              # every value already has a default
```

---

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `FAST_MODEL` | `llama3.1:8b` | Classification, tool selection, query expansion |
| `QUALITY_MODEL` | `llama3.1:70b` | Analysis, synthesis, reflection |
| `EMBEDDING_MODEL` | `nomic-embed-text` | Embeddings for FAISS / Chroma / HyDE |
| `FAISS_PERSIST_DIR` | `./data/faiss_index` | Where the FAISS index is stored |
| `FAISS_INDEX_TYPE` | `Flat` | `Flat` (dev) → `IVFFlat` / `HNSW` at scale |
| `USE_CHROMA` | `false` | Use the local Chroma database instead of FAISS |
| `CHROMA_PERSIST_DIR` | `./data/chroma` | Where the Chroma database is stored |
| `CHROMA_COLLECTION` | `documents` | Default Chroma collection name |
| `RETRIEVAL_K` | `8` | Passages retrieved per search |
| `USE_MULTI_QUERY` | `true` | Expand queries into equivalent rephrasings |
| `USE_HYDE` | `false` | HyDE retrieval (disable for existence queries) |
| `MAX_TOOL_CALLS` | `12` | **Per-agent hard cap** (Failure 1) |
| `MAX_AGENT_ITER` | `8` | **Supervisor hard cap** |
| `MAX_REFLECTION_ITER` | `2` | Reflection generate/critique rounds |
| `MAX_PDF_PAGES` | `300` | Page safety limit for PDF loading |
| `UPLOAD_DIR` | `./data/uploads` | Where uploaded files are saved |

---

## Running

```bash
uvicorn src.api:app --host 0.0.0.0 --port 8090 --reload
```

**1 — Upload a document:**
```bash
curl -X POST http://localhost:8090/documents/upload \
  -F "file=@./sample_contract.pdf" \
  -F "doc_type=legal"
# → returns a doc_id
```

**2 — Analyze it (with self-critique):**
```bash
curl -X POST http://localhost:8090/documents/analyze \
  -H "Content-Type: application/json" \
  -d '{"doc_id": "DOC-ID-FROM-UPLOAD", "use_reflection": true}' | python -m json.tool
```

**3 — Search across indexed documents:**
```bash
curl -X POST http://localhost:8090/documents/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What are the indemnification obligations?", "doc_type": "legal", "k": 5}' \
  | python -m json.tool
```

### Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/documents/upload` | Ingest a file; returns `doc_id`, type, chunk count |
| `POST` | `/documents/analyze` | Run agent analysis on a stored document |
| `POST` | `/documents/query` | Semantic search across the index |
| `GET`  | `/index/stats` | Vector count + index location |
| `GET`  | `/health` | Liveness + a real Ollama reachability check |

### Docker

```bash
docker compose up -d ollama
docker compose exec ollama ollama pull llama3.1:8b
docker compose exec ollama ollama pull nomic-embed-text
docker compose up app             # serves on http://localhost:8090
```

---

## Testing

```bash
pytest -q
```

The tests run **offline** — no Ollama, no network. This is deliberate, and it is
the payoff of how the code is structured:

- **Deterministic tools** (word count, date extraction, readability) are tested
  directly.
- **Loaders** are tested on text/markdown files and for correct error handling.
- **Agent safety logic** — the hard caps that guarantee termination — is factored
  into pure functions (`_react_route`, `_reflection_route`, `_supervisor_route`)
  and tested with hand-built states and fake messages.
- **Retrieval guardrails** (the HyDE existence-query gate, the multi-query
  relevance filter) are tested with fake models/embeddings.
- **FAISS** is tested with deterministic *fake embeddings* injected into the store,
  so it needs only `faiss-cpu`, not a running embedding model.

> The model-backed tools and the full agent loops require Ollama and are intended
> to be exercised by running the service, not by the unit tests.

---

## Design Notes & Production Lessons

These mirror Chapter 11, Section VII (How These Systems Fail in Production) and are
baked into the code:

- **Hard caps on every loop (Failure 1).** `_react_route` checks the tool-call
  counter *before* honoring a tool call; the supervisor caps delegation rounds;
  reflection caps revisions. The model never gets a vote on whether to stop.
- **Discriminating tool descriptions (Failure 1, tools).** `DocumentSearchTool`
  states explicitly that it searches *the user's* documents and when *not* to use
  it — descriptions must be mutually exclusive, not merely accurate.
- **Serialized FAISS writes (Failure 2).** `ThreadSafeFAISSStore` puts a lock
  around writes (reads stay unlocked) to prevent the silent data loss of two
  concurrent `save_local` calls.
- **Constrained query expansion (Failure 3).** The multi-query prompt demands
  *equivalent rephrasings*, and `filter_irrelevant_results` drops any expansion
  result that drifts from the original query.
- **Reference-preserving compression (Failure 4).** `ReferencePreservingCompressor`
  always keeps exceptions, definitions, and cross-references that naive compression
  would discard.
- **Plan validation (Failure 5).** `validate_plan` checks a plan for internal
  contradictions before any expensive step runs.
- **HyDE gating (Failure 6).** `should_use_hyde` restricts HyDE to
  descriptive/content queries and disables it for existence/comparison queries,
  where a confident-but-wrong hypothesis biases search toward false positives.
- **Fail-soft tools.** Every tool catches its own errors and returns a safe value
  rather than raising — a tool that crashes takes the whole agent down.

### A note on the stack

The book's snippets are trimmed for readability; this repository is the full,
runnable implementation. It uses **native Pydantic v2** (`from pydantic import
BaseModel`) rather than the deprecated `langchain_core.pydantic_v1` shim, uses
**timezone-aware timestamps** (`datetime.now(timezone.utc)`), and makes a few
interfaces injectable (notably the FAISS and Chroma embeddings) so the test suite
can run without a model server. Optional dependencies — pdfminer, OCR — are
imported lazily, so the core installs and runs without them.
