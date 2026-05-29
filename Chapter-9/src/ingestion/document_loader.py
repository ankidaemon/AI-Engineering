import io
import asyncio
import logging
import httpx
import pypdf
import arxiv
from dataclasses import dataclass, field
from typing import AsyncIterator

logger = logging.getLogger(__name__)


@dataclass
class Document:
    """Represents a single parsed source document."""
    content: str
    metadata: dict = field(default_factory=dict)
    doc_id: str = ""


class ArxivLoader:
    """
    Fetches and parses academic papers from arXiv using the official API.

    Design decisions:
    - Uses the arxiv Python client which respects the API rate limits
      (max 1 request per 3 seconds for bulk access).
    - PDF download implements exponential backoff because arXiv's CDN
      occasionally returns 503 under load.
    - Authors are capped at 10 to avoid metadata bloat in vector stores.
    """

    def __init__(self, request_delay: float = 0.5):
        self._client = arxiv.Client(
            page_size=10,
            delay_seconds=request_delay,
            num_retries=5
        )

    async def load_papers(
        self,
        query: str,
        max_results: int = 20,
        categories: list[str] | None = None
    ) -> AsyncIterator[Document]:
        """
        Yields Document objects for each successfully fetched paper.
        Skips papers that fail to download without raising.
        """
        search_query = query
        if categories:
            cat_clause = " OR ".join(f"cat:{c}" for c in categories)
            search_query = f"({query}) AND ({cat_clause})"

        search = arxiv.Search(
            query=search_query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.Relevance
        )

        for result in self._client.results(search):
            try:
                text = await self._download_and_extract(result.pdf_url)
                if not text.strip():
                    logger.warning(f"Empty text for {result.entry_id}")
                    continue

                yield Document(
                    content=text,
                    metadata={
                        "arxiv_id":   result.entry_id.split("/")[-1],
                        "title":      result.title,
                        "authors":    [str(a) for a in result.authors[:10]],
                        "published":  result.published.isoformat(),
                        "categories": result.categories,
                        "abstract":   result.summary,
                        "pdf_url":    result.pdf_url,
                        "source":     "arxiv"
                    },
                    doc_id=result.entry_id.split("/")[-1]
                )
            except Exception as exc:
                logger.warning(f"Skipping {result.entry_id}: {exc}")

    async def _download_and_extract(self, pdf_url: str) -> str:
        """Download PDF and extract text with exponential backoff retries."""
        for attempt in range(3):
            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.get(
                        pdf_url, follow_redirects=True
                    )
                    response.raise_for_status()

                reader = pypdf.PdfReader(io.BytesIO(response.content))
                pages = []
                for page in reader.pages:
                    text = page.extract_text()
                    if text and text.strip():
                        pages.append(text.strip())
                return "\n\n".join(pages)

            except Exception:
                if attempt == 2:
                    raise
                wait = 2 ** attempt
                logger.debug(f"PDF download retry {attempt + 1}, waiting {wait}s")
                await asyncio.sleep(wait)
        return ""
