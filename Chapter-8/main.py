import os
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import json

from fetcher import fetch_articles
from store import upsert_articles, query_articles, article_count
from personalizer import personalize_articles, generate_feed_intro

app = FastAPI(title="Content Curator API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory user profile store (keyed by user_id)
_users: dict = {}


# ---------- Models ----------

class UserPreferences(BaseModel):
    user_id: str
    name: str
    interests: List[str]
    reading_level: str = "intermediate"   # beginner | intermediate | expert
    tone: str = "casual"                  # formal | casual | analytical
    max_articles: int = 8


class FetchRequest(BaseModel):
    topics: Optional[List[str]] = None
    max_per_feed: int = 5


class FeedbackRequest(BaseModel):
    user_id: str
    article_id: str
    liked: bool


# ---------- Routes ----------

@app.post("/preferences")
def save_preferences(prefs: UserPreferences):
    _users[prefs.user_id] = prefs.model_dump()
    return {"status": "saved", "user_id": prefs.user_id}


@app.get("/preferences/{user_id}")
def get_preferences(user_id: str):
    if user_id not in _users:
        raise HTTPException(status_code=404, detail="User not found")
    return _users[user_id]


@app.post("/fetch")
def fetch_and_index(req: FetchRequest):
    topics = req.topics or ["technology", "ai", "science", "business", "health", "world"]
    articles = fetch_articles(topics, max_per_feed=req.max_per_feed)
    if not articles:
        return {"indexed": 0, "message": "No articles fetched. Check your internet connection."}
    indexed = upsert_articles(articles)
    return {"indexed": indexed, "total_in_store": article_count()}


@app.get("/feed/{user_id}")
def get_feed(user_id: str):
    if user_id not in _users:
        raise HTTPException(status_code=404, detail="User not found. Set preferences first.")

    prefs = _users[user_id]
    interests = prefs["interests"]
    preference_text = f"Articles about {', '.join(interests)} for a {prefs['reading_level']} reader."

    if article_count() == 0:
        raise HTTPException(status_code=404, detail="No articles in store. Call /fetch first.")

    candidates = query_articles(preference_text, n_results=prefs["max_articles"] * 2)
    top = candidates[: prefs["max_articles"]]

    personalized = personalize_articles(
        top,
        user_interests=interests,
        reading_level=prefs["reading_level"],
        tone=prefs["tone"],
    )

    intro = generate_feed_intro(prefs["name"], interests, len(personalized))

    return {
        "intro": intro,
        "user": {"name": prefs["name"], "interests": interests},
        "articles": personalized,
    }


@app.post("/feedback")
def record_feedback(req: FeedbackRequest):
    if req.user_id not in _users:
        raise HTTPException(status_code=404, detail="User not found")
    user = _users[req.user_id]
    # Simple preference reinforcement: append liked article topics to interests
    if req.liked:
        user.setdefault("liked_ids", []).append(req.article_id)
    else:
        user.setdefault("disliked_ids", []).append(req.article_id)
    return {"status": "recorded"}


@app.get("/stats")
def stats():
    return {"articles_in_store": article_count(), "users": len(_users)}


# Serve frontend
app.mount("/", StaticFiles(directory="static", html=True), name="static")
