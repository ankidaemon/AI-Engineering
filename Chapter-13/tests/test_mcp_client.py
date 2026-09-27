"""Consuming somebody else's MCP server, offline (§1.5, §8.10).

The transport is the one part that cannot be tested without a network, so it
is the one part that is injected. Everything else, turning content blocks into
text and a scrape into a Document the pipeline accepts, is plain logic and is
tested directly.
"""
import pytest

from src.mcp_client import (
    RemoteServer, fetch_page, text_from, web_document,
)
from src.workers.tasks import ingest_web_page_impl


class _Block:
    def __init__(self, text):
        self.text = text


class _Result:
    def __init__(self, *texts):
        self.content = [_Block(t) for t in texts]


# ── Reading what a tool returned ─────────────────────────────────────

def test_text_blocks_are_joined_in_order():
    assert text_from(_Result("first ", "second")) == "first second"


def test_non_text_blocks_are_dropped_rather_than_crashing():
    """An image or an embedded resource is not something a text pipeline can
    use, and it must not take the ingestion down."""
    result = _Result("kept")
    result.content.append(object())
    assert text_from(result) == "kept"


@pytest.mark.parametrize("empty", [_Result(), None])
def test_an_empty_result_is_an_empty_string(empty):
    assert text_from(empty) == ""


# ── A scraped page joins the pipeline like any other source ──────────

def test_a_scraped_page_carries_the_same_metadata_as_a_file():
    doc = web_document("https://bank.example/fees", "public-fees",
                       "# Fees\n\nThe late fee is 500.",
                       product="travel-card", effective_date="2026-04-01")
    assert doc.metadata["doc_id"] == "public-fees"
    assert doc.metadata["source"] == "https://bank.example/fees"
    assert doc.metadata["product"] == "travel-card"
    assert doc.metadata["effective_date"] == "2026-04-01"
    # long prose, so it must still be split on its own boundaries (§4.3)
    assert doc.metadata["natural_unit"] is False


def test_fetch_page_asks_the_server_for_markdown():
    seen = {}

    def fake_call(server, name, arguments):
        seen["server"], seen["name"], seen["args"] = server, name, arguments
        return "# Fee schedule\n\nThe late fee is 500."

    server = RemoteServer(url="https://mcp.example/v2/mcp")
    docs = fetch_page("https://bank.example/fees", "public-fees",
                      call=fake_call, server=server)

    assert seen["name"] == "firecrawl_scrape"
    assert seen["args"]["url"] == "https://bank.example/fees"
    assert "markdown" in seen["args"]["formats"]
    assert len(docs) == 1 and "late fee" in docs[0].page_content


def test_an_empty_scrape_fails_loudly_instead_of_indexing_nothing():
    """Silently replacing a document's chunks with nothing would delete the
    bank's published fees from the index and leave no trace."""
    with pytest.raises(RuntimeError):
        fetch_page("https://bank.example/fees", "public-fees",
                   call=lambda *a, **k: "   ",
                   server=RemoteServer(url="https://mcp.example/v2/mcp"))


def test_the_key_is_sent_as_a_bearer_header():
    server = RemoteServer.firecrawl(api_key="fc-test")
    assert server.headers["Authorization"] == "Bearer fc-test"


def test_a_missing_key_is_refused_before_any_connection(monkeypatch):
    """Explicitly unset, so the test says the same thing on a machine that
    happens to have a real key in its .env."""
    from src.config import settings
    monkeypatch.setattr(settings, "firecrawl_api_key", "")
    with pytest.raises(RuntimeError):
        RemoteServer.firecrawl(url="https://mcp.example/v2/mcp")


# ── The background task ──────────────────────────────────────────────

class _FakeIndex:
    def __init__(self):
        self.replaced = {}

    def replace(self, doc_id, chunks):
        self.replaced[doc_id] = chunks


class _FakePipeline:
    def __init__(self):
        self.index = _FakeIndex()

    def split_and_embed(self, docs):
        return docs            # splitting is tested in test_loaders_ingest


def test_a_web_page_is_indexed_by_the_same_replace_a_file_uses():
    """One document swapped in place (§4.5), whether its text came from disk
    or from a protocol call. That is the point of the shared metadata shape."""
    pipeline = _FakePipeline()

    result = ingest_web_page_impl(
        "https://bank.example/fees", "public-fees", pipeline,
        fetch=lambda url, doc_id: [web_document(url, doc_id, "some fees")])

    assert result == {"doc_id": "public-fees",
                      "url": "https://bank.example/fees", "chunks": 1}
    assert "public-fees" in pipeline.index.replaced
