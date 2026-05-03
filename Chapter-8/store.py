import chromadb
from chromadb.utils import embedding_functions
from typing import List, Dict, Optional

_client = chromadb.PersistentClient(path="./chroma_db")

_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)

_articles_col = _client.get_or_create_collection(
    name="articles",
    embedding_function=_ef,
    metadata={"hnsw:space": "cosine"},
)


def upsert_articles(articles: List[Dict]) -> int:
    if not articles:
        return 0

    ids, docs, metas = [], [], []
    for a in articles:
        text = f"{a['title']}. {a['summary']}"
        ids.append(a["id"])
        docs.append(text)
        metas.append({
            "title": a["title"][:500],
            "url": a["url"],
            "source": a["source"][:200],
            "published": str(a["published"])[:100],
            "topic_hint": a.get("topic_hint", "general"),
            "summary": a["summary"][:500],
        })

    _articles_col.upsert(ids=ids, documents=docs, metadatas=metas)
    return len(ids)


def query_articles(
    preference_text: str,
    n_results: int = 10,
    topic_filter: Optional[str] = None,
) -> List[Dict]:
    where = {"topic_hint": topic_filter} if topic_filter else None

    results = _articles_col.query(
        query_texts=[preference_text],
        n_results=min(n_results, _articles_col.count() or 1),
        where=where,
        include=["documents", "metadatas", "distances"],
    )

    articles = []
    if not results["ids"] or not results["ids"][0]:
        return articles

    for i, doc_id in enumerate(results["ids"][0]):
        meta = results["metadatas"][0][i]
        distance = results["distances"][0][i]
        articles.append({
            "id": doc_id,
            "title": meta["title"],
            "url": meta["url"],
            "source": meta["source"],
            "published": meta["published"],
            "summary": meta["summary"],
            "relevance_score": round(1 - distance, 3),
        })

    return articles


def article_count() -> int:
    return _articles_col.count()
