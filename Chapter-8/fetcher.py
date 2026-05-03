import feedparser
import httpx
from datetime import datetime
from typing import List, Dict

RSS_FEEDS = {
    "technology": [
        "https://techcrunch.com/feed/",
        "https://www.wired.com/feed/rss",
        "https://hnrss.org/frontpage",
    ],
    "ai": [
        "http://arxiv.org/rss/cs.AI",
        "https://blogs.microsoft.com/ai/feed/",
    ],
    "science": [
        "https://www.sciencedaily.com/rss/all.xml",
        "https://feeds.nature.com/nature/rss/current",
    ],
    "business": [
        "https://feeds.bloomberg.com/markets/news.rss",
        "https://www.ft.com/?format=rss",
    ],
    "health": [
        "https://rss.medicalnewstoday.com/featurednews.xml",
        "https://feeds.webmd.com/rss/rss.aspx?RSSSource=RSS_PUBLIC",
    ],
    "world": [
        "http://feeds.bbci.co.uk/news/world/rss.xml",
        "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
    ],
}


def fetch_articles(topics: List[str], max_per_feed: int = 5) -> List[Dict]:
    articles = []
    seen_urls = set()

    feeds_to_fetch = []
    for topic in topics:
        topic_lower = topic.lower()
        for key, urls in RSS_FEEDS.items():
            if key in topic_lower or topic_lower in key:
                feeds_to_fetch.extend(urls)

    if not feeds_to_fetch:
        for urls in RSS_FEEDS.values():
            feeds_to_fetch.extend(urls)

    for feed_url in set(feeds_to_fetch):
        try:
            parsed = feedparser.parse(feed_url)
            for entry in parsed.entries[:max_per_feed]:
                url = entry.get("link", "")
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)

                summary = entry.get("summary", "") or entry.get("description", "")
                # strip basic html tags from summary
                import re
                summary = re.sub(r"<[^>]+>", " ", summary).strip()

                published = entry.get("published", str(datetime.now()))

                articles.append({
                    "id": url,
                    "title": entry.get("title", "Untitled"),
                    "url": url,
                    "summary": summary[:1000],
                    "source": parsed.feed.get("title", feed_url),
                    "published": published,
                    "topic_hint": _topic_for_feed(feed_url),
                })
        except Exception:
            continue

    return articles


def _topic_for_feed(url: str) -> str:
    for topic, urls in RSS_FEEDS.items():
        if url in urls:
            return topic
    return "general"
