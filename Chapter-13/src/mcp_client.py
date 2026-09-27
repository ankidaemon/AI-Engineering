"""
The other direction: consuming somebody else's MCP server (§1.5, §8.10).

`src/mcp_server.py` publishes the bank's tools so other assistants can use
them. This module is the mirror image. It connects out to a server somebody
else wrote, asks what it offers, and calls one of its tools.

Nothing here mentions FireCrawl by name until the very last function. That is
the whole argument of §1.1 made concrete: `describe` and `call_tool` work
against any MCP server, so pointing them at a document store or a payments
service tomorrow is a change of address, not a change of code. Compare it with
Chapter 12, which reached the same FireCrawl capability through a vendor SDK
and a bespoke loader written against that SDK's shape. Both work. Only one of
them is still correct when the vendor changes.

Two things worth noticing while reading:

Transport is a detail. The bank's own server runs over stdio because it is
launched as a child process. FireCrawl's runs over HTTP because it belongs to
somebody else and lives on the internet (§1.4). The session code below is the
same either way; only `connect` differs.

Everything that can be a plain function is one. The transport is injected as
`call`, so the ingestion path is tested with no network at all, the same way
the rest of this repository is.
"""
import asyncio
import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass, field

from langchain_core.documents import Document

logger = logging.getLogger(__name__)


@dataclass
class RemoteServer:
    """Where a server lives and how to prove who you are. A stdio server
    would carry a command instead of a url; the session code is unchanged."""
    url: str
    headers: dict = field(default_factory=dict)

    @classmethod
    def firecrawl(cls, api_key: str = "", url: str = ""):
        from src.config import settings
        api_key = api_key or settings.firecrawl_api_key
        if not api_key:
            raise RuntimeError(
                "FIRECRAWL_API_KEY is not set. The bank's own MCP server needs "
                "no key because it runs as a child process; a server on the "
                "internet needs one.")
        return cls(url=url or settings.firecrawl_mcp_url,
                   headers={"Authorization": f"Bearer {api_key}"})


@asynccontextmanager
async def connect(server: RemoteServer):
    """Open a session: connect, handshake, agree a protocol version (§1.3)."""
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client

    async with streamablehttp_client(server.url, headers=server.headers) as (
            read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session


def text_from(result) -> str:
    """A tool returns a list of content blocks, not a string. Text blocks are
    what a model can read, so they are what we keep."""
    blocks = getattr(result, "content", result) or []
    return "".join(getattr(block, "text", "") for block in blocks)


async def describe_async(server: RemoteServer) -> list:
    """The discovery step, the one a host runs at startup. Returns the pairs
    that a model would later read when choosing."""
    async with connect(server) as session:
        listed = await session.list_tools()
        return [(tool.name, (tool.description or "").strip())
                for tool in listed.tools]


async def call_tool_async(server: RemoteServer, name: str,
                          arguments: dict) -> str:
    async with connect(server) as session:
        logger.info("calling %s on %s", name, server.url)
        return text_from(await session.call_tool(name, arguments))


def describe(server: RemoteServer) -> list:
    """Sync wrapper. Everything that calls this, a Celery worker or a script,
    is ordinary sync code."""
    return asyncio.run(describe_async(server))


def call_tool(server: RemoteServer, name: str, arguments: dict) -> str:
    return asyncio.run(call_tool_async(server, name, arguments))


# ── Using it for something the bank actually needs ───────────────────

def web_document(url: str, doc_id: str, markdown: str, product: str = "general",
                 effective_date: str = "") -> Document:
    """Give a scraped page the same metadata shape every other source in
    §4.2 carries, so the rest of the pipeline cannot tell the difference.
    `natural_unit` is False because a web page is long prose that still needs
    splitting on its own boundaries."""
    return Document(page_content=markdown, metadata={
        "doc_id": doc_id,
        "source": url,
        "doc_type": "policy",
        "product": product,
        "effective_date": effective_date,
        "natural_unit": False,
    })


def fetch_page(url: str, doc_id: str, product: str = "general",
               effective_date: str = "", call=None, server=None) -> list:
    """Scrape one page through whichever MCP server offers scraping.

    `call` is the seam. In production it is the real protocol call; in tests
    it is a function returning canned markdown, which is why the ingestion
    test needs no network and no key.
    """
    call = call or call_tool
    server = server or RemoteServer.firecrawl()
    markdown = call(server, "firecrawl_scrape",
                    {"url": url, "formats": ["markdown"], "onlyMainContent": True})
    if not markdown.strip():
        raise RuntimeError(f"the scrape of {url} came back empty")
    return [web_document(url, doc_id, markdown, product, effective_date)]


def _demo() -> None:
    """`python -m src.mcp_client` prints what FireCrawl offers and scrapes one
    page, which is the whole consuming direction in twenty lines."""
    server = RemoteServer.firecrawl()
    tools = describe(server)
    print(f"{len(tools)} tools offered by {server.url}\n")
    for name, description in tools[:8]:
        print(f"  {name:34} {description.splitlines()[0][:70]}")
    print("\nscraping one page through the protocol ...")
    docs = fetch_page("https://www.rbi.org.in/", doc_id="rbi-home")
    print(f"  {len(docs[0].page_content)} characters, "
          f"metadata {docs[0].metadata}")


if __name__ == "__main__":
    _demo()
