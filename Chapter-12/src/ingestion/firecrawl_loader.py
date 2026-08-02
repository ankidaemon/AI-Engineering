"""
FireCrawl loader.

FireCrawl is a web crawling API that handles the hard parts of reading a modern
web page: running JavaScript, getting past bot checks, and returning clean text
instead of raw HTML. This wrapper turns a scrape into a LangChain `Document` and
stamps a content hash on it, which the content monitor uses to skip pages that
have not changed since last time.

The FireCrawl client is injected, so tests use a fake and never hit the network.
"""
import hashlib
import logging
from dataclasses import dataclass
from langchain_core.documents import Document

logger = logging.getLogger(__name__)


def content_hash(text: str) -> str:
    """Stable hash of page text, used to detect real changes."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass
class CrawlConfig:
    only_main_content: bool = True
    max_pages: int = 10


class FireCrawlLoader:
    def __init__(self, api_key: str = "", client=None):
        self._client = client
        self._api_key = api_key

    def _get_client(self):
        if self._client is not None:
            return self._client
        from firecrawl import FirecrawlApp
        from src.config import settings
        self._client = FirecrawlApp(api_key=self._api_key or settings.firecrawl_api_key)
        return self._client

    def scrape_page(self, url: str) -> Document:
        """Scrape one URL into a Document with a content hash in its metadata."""
        client = self._get_client()
        result = client.scrape_url(url, params={"formats": ["markdown"]})
        text = result.get("markdown", "") if isinstance(result, dict) else str(result)
        meta = result.get("metadata", {}) if isinstance(result, dict) else {}
        return Document(
            page_content=text,
            metadata={
                "source": url,
                "title": meta.get("title", url),
                "content_hash": content_hash(text),
            },
        )
