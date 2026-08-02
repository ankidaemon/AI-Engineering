"""Content monitor deduplication and the FireCrawl loader, with fakes."""
import pytest
from langchain_core.documents import Document

from src.ingestion.firecrawl_loader import FireCrawlLoader, content_hash
from src.ingestion.content_monitor import ContentMonitor
from src.vectorstores.pgvector_store import make_vector_store


class FakeFirecrawl:
    """Returns canned pages keyed by URL, no network."""
    def __init__(self, pages):
        self._pages = pages

    def scrape_url(self, url, params=None):
        return {"markdown": self._pages[url], "metadata": {"title": f"Title of {url}"}}


def make_store():
    """The real store object, with the in memory backend, so the scoping the
    monitor relies on is exercised rather than stubbed away."""
    return make_vector_store("memory")


def test_loader_stamps_content_hash():
    client = FakeFirecrawl({"http://a": "some page text"})
    loader = FireCrawlLoader(client=client)
    doc = loader.scrape_page("http://a")
    assert doc.metadata["content_hash"] == content_hash("some page text")
    assert doc.metadata["title"] == "Title of http://a"


async def test_monitor_indexes_new_content():
    store = make_store()
    monitor = ContentMonitor(store, loader=None)
    docs = [Document(page_content="brand new report about markets", metadata={})]
    n = await monitor._index_new_content(docs, "acme")
    assert n >= 1
    assert store.for_customer("acme").similarity_search("report about markets", k=5)


async def test_monitor_skips_unchanged_pages():
    store = make_store()
    monitor = ContentMonitor(store, loader=None)
    doc = Document(page_content="identical text", metadata={"content_hash": content_hash("identical text")})

    first = await monitor._index_new_content([doc], "acme")
    second = await monitor._index_new_content([doc], "acme")   # same hash, seen
    assert first >= 1
    assert second == 0


async def test_dedup_is_per_customer():
    """A shared hash set would make a page one customer already indexed look
    unchanged to every other customer, so they would never receive it."""
    store = make_store()
    monitor = ContentMonitor(store, loader=None)
    doc = Document(page_content="a public filing everyone watches", metadata={})

    assert await monitor._index_new_content([doc], "acme") >= 1
    assert await monitor._index_new_content([doc], "globex") >= 1
    assert store.for_customer("globex").similarity_search("public filing", k=5)


async def test_poll_once_pulls_from_loader():
    store = make_store()
    client = FakeFirecrawl({"http://a": "page a content", "http://b": "page b content"})
    loader = FireCrawlLoader(client=client)
    monitor = ContentMonitor(store, loader)
    monitor.add_source("http://a", "acme")
    monitor.add_source("http://b", "acme")

    indexed = await monitor.poll_once()
    assert indexed >= 2


async def test_poll_once_keeps_each_customers_sources_apart():
    store = make_store()
    client = FakeFirecrawl({"http://a": "acme page content", "http://b": "globex page content"})
    monitor = ContentMonitor(store, FireCrawlLoader(client=client))
    monitor.add_source("http://a", "acme")
    monitor.add_source("http://b", "globex")

    await monitor.poll_once()

    acme = store.for_customer("acme").similarity_search("page content", k=10)
    assert acme and all("globex" not in d.page_content for d in acme)


def test_a_source_must_belong_to_a_customer():
    monitor = ContentMonitor(make_store(), loader=None)
    with pytest.raises(ValueError):
        monitor.add_source("http://a", "")
