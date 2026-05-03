# AI-Powered Content Curator

A personalized article feed that learns your interests, finds relevant content from the web, and rewrites it in your preferred tone and reading level — powered by ChromaDB, Hugging Face, and OpenAI.

---

## Table of Contents

1. [What is this project?](#1-what-is-this-project)
2. [Why is it built this way?](#2-why-is-it-built-this-way)
3. [How does it all connect?](#3-how-does-it-all-connect)
4. [Baby steps to build and run it](#4-baby-steps-to-build-and-run-it)
5. [Using the app](#5-using-the-app)
6. [What happens under the hood](#6-what-happens-under-the-hood)
7. [Common issues and fixes](#7-common-issues-and-fixes)
8. [Extend it further](#8-extend-it-further)

---

## 1. What is this project?

Imagine having a personal reading assistant that:

- Knows you like AI, climate, and startups
- Goes out every morning and reads hundreds of articles
- Picks only the ones relevant to you
- Rewrites them in plain English (or expert-level, your choice)
- Presents them in a clean web page

That is exactly what this app does — automatically, using AI.

### What you will see when you open it

A dark-themed web page with two sections:

**Left panel (your profile)**
- Enter your name
- Type in your interests (e.g. "machine learning", "space", "finance")
- Choose reading level: Beginner / Intermediate / Expert
- Choose tone: Casual / Formal / Analytical
- Two buttons: one to fetch articles, one to generate your feed

**Right panel (your feed)**
- A personalized greeting written by AI
- Article cards, each showing:
  - Source name and relevance score
  - Title (clickable link to original)
  - AI-generated summary tailored to your interests and level
  - Thumbs up / thumbs down feedback buttons

---

## 2. Why is it built this way?

Every technology choice was made for a specific reason. Understanding the *why* helps you make your own choices in future projects.

### Why Python?

Both Hugging Face and OpenAI are Python-first libraries. The best documentation, most community examples, and the fewest setup headaches are all in Python. For AI projects, Python is the default choice.

### Why FastAPI (not Flask, not Django)?

| Framework | Good for | Not ideal for |
|-----------|----------|---------------|
| Flask | Simple scripts, tiny APIs | Heavy async workloads |
| Django | Full websites with auth, admin | Lightweight microservices |
| **FastAPI** | **AI APIs, async calls, auto docs** | **Nothing in our case** |

FastAPI automatically generates interactive API docs at `/docs`, handles async requests natively (important when waiting for OpenAI responses), and validates request/response shapes automatically via Pydantic.

### Why ChromaDB?

Regular databases store text as text. Searching them means keyword matching — "machine learning" won't find an article titled "neural networks revolutionize drug discovery."

ChromaDB is a **vector database**. It stores text as numbers (called embeddings) that represent *meaning*. So "machine learning" and "neural networks" are numerically close. When you ask for articles matching your interests, ChromaDB returns articles that are *semantically similar* — even if they share no exact words.

### Why Hugging Face for embeddings (not OpenAI)?

You could use OpenAI's embedding API, but:
- It costs money per token
- You might embed hundreds of articles at once
- Hugging Face's `all-MiniLM-L6-v2` model runs **locally on your machine**, is **free**, and is fast enough for this workload
- It produces high-quality embeddings that ChromaDB can use directly

**Rule of thumb:** use local/free models for bulk processing (many articles), paid models for user-facing generation (one response at a time).

### Why OpenAI for summarization?

Summarizing and rewriting text to match a person's tone, level, and interests requires a high-quality language model. GPT-4o-mini is:
- Cheaper than GPT-4o (about 15× less)
- Better than older models at following nuanced instructions
- Fast enough for real-time responses

We only call it for the final 6–8 articles the user actually sees — not for the hundreds we filtered out. This keeps costs very low.

### Why RSS feeds?

RSS (Really Simple Syndication) is a standard format that most news sites and blogs support. It gives us a structured list of recent articles — title, summary, link, date — without needing to scrape websites or pay for a news API. It is free, reliable, and works instantly.

### Why plain HTML (not React)?

React adds build tools (webpack, npm, node_modules) and complexity that is unnecessary here. Our UI has one page with no complex state beyond a list of articles. Plain HTML + vanilla JavaScript is:
- Easier to read and understand
- Zero dependencies
- Instantly runnable (just open in a browser or serve as a static file)

---

## 3. How does it all connect?

Here is the full data flow, step by step:

```
Your browser (index.html)
        │
        │  HTTP requests (fetch, GET, POST)
        ▼
  FastAPI server (main.py)
        │
        ├──► fetcher.py ──────► RSS feeds on the internet
        │         │                     │
        │         │ returns articles     │
        │         ▼                     │
        ├──► store.py ────────► HuggingFace model (local)
        │         │               embeds text → numbers
        │         ▼
        │     ChromaDB (local disk: ./chroma_db/)
        │         stores & retrieves articles by meaning
        │
        └──► personalizer.py ──► OpenAI API (cloud)
                    │               generates summaries
                    ▼
              JSON response
                    │
                    ▼
           Your browser renders the feed
```

### File responsibilities

| File | What it does |
|------|-------------|
| `main.py` | The central hub. Defines all API routes, receives requests from the browser, calls the other modules, returns results |
| `fetcher.py` | Reads RSS feeds from ~10 news sources. Parses each entry into a clean dictionary with title, summary, URL, source |
| `store.py` | Wraps ChromaDB. Saves articles as vectors, queries them by semantic similarity to your interests |
| `personalizer.py` | Calls OpenAI to rewrite each article summary to match your tone and reading level |
| `static/index.html` | The entire frontend — HTML structure, CSS styling, and JavaScript logic in one file |

---

## 4. Baby steps to build and run it

Follow these steps exactly, in order. Do not skip any.

---

### Step 1 — Check your Python version

Open a terminal (Terminal on Mac, Command Prompt or PowerShell on Windows).

```bash
python --version
```

You need Python 3.9 or higher. If you see `Python 3.9.x`, `3.10.x`, `3.11.x`, or `3.12.x` you are fine.

If Python is not installed, download it from [python.org](https://python.org).

---

### Step 2 — Get an OpenAI API key

1. Go to [platform.openai.com](https://platform.openai.com)
2. Sign up or log in
3. Click your profile (top right) → **API keys** → **Create new secret key**
4. Copy the key — it starts with `sk-`
5. Add a small amount of credit (even $5 is enough for many hours of use with gpt-4o-mini)

Keep this key private. Never share it or commit it to Git.

---

### Step 3 — Download the project files

If you are using git:

```bash
git clone <your-repo-url>
cd Chapter-8
```

Or just copy the project folder to your computer and navigate into it:

```bash
cd path/to/Chapter-8
```

Verify the files are there:

```bash
ls
# Should show: main.py  fetcher.py  store.py  personalizer.py  requirements.txt  static/
```

---

### Step 4 — Create a virtual environment

A virtual environment is an isolated box for Python packages. It prevents conflicts with other projects on your computer.

```bash
# Create the environment
python -m venv venv

# Activate it — Mac/Linux:
source venv/bin/activate

# Activate it — Windows:
venv\Scripts\activate
```

Your terminal prompt should now start with `(venv)`. This means the environment is active.

> Every time you open a new terminal to work on this project, you must activate the venv again.

---

### Step 5 — Install dependencies

```bash
pip install -r requirements.txt
```

This installs:
- `fastapi` + `uvicorn` — web server
- `chromadb` — vector database
- `sentence-transformers` — Hugging Face embedding model
- `feedparser` — RSS reader
- `openai` — OpenAI SDK
- `python-dotenv` — reads your `.env` file

> The first install takes a few minutes because it downloads the `all-MiniLM-L6-v2` model (~90 MB).

---

### Step 6 — Add your API key

```bash
# Mac/Linux:
cp .env.example .env

# Windows:
copy .env.example .env
```

Now open `.env` in any text editor and replace the placeholder:

```
OPENAI_API_KEY=sk-your-actual-key-here
```

Save the file.

---

### Step 7 — Start the server

```bash
uvicorn main:app --reload
```

You should see output like:

```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Application startup complete.
```

The `--reload` flag means the server automatically restarts when you edit a Python file. Useful during development.

---

### Step 8 — Open the app

Open your browser and go to:

```
http://localhost:8000
```

You should see the dark-themed Content Curator interface.

---

### Step 9 — Use the app

1. Type your name in the **Your name** field
2. In the **Interests** field, type a topic (e.g. `artificial intelligence`) and press **Enter**. Add 2–3 more topics.
3. Choose your reading level and tone
4. Click **Fetch & Index Articles** — wait 10–30 seconds while it downloads articles and builds the vector index
5. Click **Generate My Feed** — wait 20–40 seconds while OpenAI personalizes each article
6. Your feed appears on the right

---

### Step 10 — Explore the auto-generated API docs

FastAPI gives you free interactive documentation. While the server is running, visit:

```
http://localhost:8000/docs
```

You can test every API endpoint directly from the browser. This is useful for debugging and understanding what each route does.

---

## 5. Using the app

### The interests chip input

- Type a topic and press **Enter** to add it as a chip
- Press **Backspace** on an empty field to remove the last chip
- Add as many topics as you want

### Fetch vs Generate

These are separate steps by design:

- **Fetch & Index** only needs to run once (or when you want fresh articles). It downloads articles and stores them in ChromaDB on your disk — they persist across server restarts.
- **Generate My Feed** can be run any time. It queries the stored articles and personalizes them for your current preferences.

### Feedback buttons

The 👍 and 👎 buttons record your reaction. The backend stores liked/disliked article IDs per user. In a more advanced version, these would feed back into the preference model to improve future recommendations.

---

## 6. What happens under the hood

### When you click "Fetch & Index Articles"

```
Browser → POST /fetch
           │
           ├─ fetcher.py reads RSS feeds matching your topics
           │   (e.g. techcrunch.com, arxiv.org/rss/cs.AI, bbci.co.uk)
           │
           ├─ Each article becomes: { title, summary, url, source, date }
           │
           └─ store.py sends each article to HuggingFace model
               "all-MiniLM-L6-v2" converts title+summary → 384 numbers
               ChromaDB stores those numbers + metadata on disk
```

### When you click "Generate My Feed"

```
Browser → GET /feed/{user_id}
           │
           ├─ Your interests become one string:
           │   "Articles about AI, climate for an intermediate reader."
           │
           ├─ HuggingFace converts that string → 384 numbers
           │
           ├─ ChromaDB finds the articles whose numbers are closest
           │   (cosine similarity — direction of vectors, not magnitude)
           │
           ├─ Top 12 candidates → take top 6 (your max_articles setting)
           │
           ├─ For each of those 6 articles, OpenAI receives:
           │   "Summarize this article for a reader interested in X.
           │    Use casual tone. Intermediate level."
           │
           └─ Returns personalized summaries → browser renders cards
```

### What cosine similarity means (simply)

Think of each article as an arrow pointing in a direction in space. "AI research" and "machine learning breakthrough" point in nearly the same direction. "Football match results" points in a completely different direction.

ChromaDB measures the angle between your interest arrow and each article arrow. Small angle = similar meaning = high relevance score.

---

## 7. Common issues and fixes

### "No articles fetched"

Some RSS feeds block automated requests or are temporarily down. The fetcher silently skips failed feeds. If you get 0 articles, try again — or check your internet connection.

### "No articles in store. Call /fetch first"

You clicked Generate before Fetch. Click **Fetch & Index Articles** first.

### Server crashes on startup with ImportError

The virtual environment is not active, or a package failed to install. Run:

```bash
source venv/bin/activate   # Mac/Linux
pip install -r requirements.txt
```

### OpenAI error: "Invalid API key"

Check your `.env` file. Make sure there are no spaces around the `=` sign:

```
OPENAI_API_KEY=sk-abc123   ← correct
OPENAI_API_KEY = sk-abc123 ← wrong
```

### ChromaDB error on first run

Delete the `chroma_db/` folder and restart the server. It recreates itself cleanly.

```bash
rm -rf chroma_db/
uvicorn main:app --reload
```

### Port 8000 already in use

Another process is using port 8000. Run on a different port:

```bash
uvicorn main:app --reload --port 8001
# then open http://localhost:8001
```

---

## 8. Extend it further

Once the basics work, here are natural next steps:

### Easy
- **Add more RSS feeds** — edit the `RSS_FEEDS` dict in `fetcher.py`
- **Change the summary length** — edit `max_tokens=200` in `personalizer.py`
- **Add a dark/light mode toggle** — pure CSS/JS change in `index.html`

### Intermediate
- **Persist user profiles** — replace the in-memory `_users` dict in `main.py` with SQLite using the `sqlite3` standard library
- **Schedule automatic fetching** — use `APScheduler` to run `fetch_articles()` every morning automatically
- **Add article deduplication** — hash article titles to avoid showing the same article twice

### Advanced
- **Use the feedback loop** — weight liked articles' topics higher in the ChromaDB query
- **Fine-tune the embedding model** — train `all-MiniLM-L6-v2` on your own liked/disliked article pairs using Hugging Face `sentence-transformers` training utilities
- **Add streaming** — use OpenAI's streaming API so summaries appear word-by-word instead of all at once

---

## Quick reference

| Action | Command |
|--------|---------|
| Activate venv (Mac) | `source venv/bin/activate` |
| Activate venv (Windows) | `venv\Scripts\activate` |
| Start server | `uvicorn main:app --reload` |
| View API docs | `http://localhost:8000/docs` |
| View app | `http://localhost:8000` |
| Reset article store | `rm -rf chroma_db/` |
| Stop server | `Ctrl + C` |
