"""
The ingestion pipeline: load, split, embed, index (§4.2, §4.3, §4.5).

Splitting respects the structure the documents already have. FAQ entries and
fee rows arrive as natural units and pass through untouched. Policy and terms
text is split with separators ordered to prefer paragraph and clause
boundaries over blind cuts, so a retrieved chunk reads as a coherent passage.

Freshness (§4.5) is the other job here: `reindex(doc_id)` re-loads one
changed document and swaps its chunks in the index via `replace`, rather
than rebuilding everything. The Celery tasks in `src/workers/tasks.py` call
this from a background worker so no customer ever waits on it.
"""
from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter


def make_splitter() -> RecursiveCharacterTextSplitter:
    return RecursiveCharacterTextSplitter(
        chunk_size=600, chunk_overlap=80,
        separators=["\n\n", "\n", ". ", " ", ""],   # prefer structural breaks
        keep_separator=True,
    )


def split_documents(docs: list, splitter=None) -> list:
    """Natural units (FAQs, fee rows) pass through; long documents split."""
    splitter = splitter or make_splitter()
    chunks = []
    for doc in docs:
        if doc.metadata.get("natural_unit"):
            chunks.append(doc)
        else:
            chunks.extend(splitter.split_documents([doc]))
    return chunks


class IngestionPipeline:
    """Ties loading, splitting, and indexing together around one index.

    Everything is injectable: the index carries its own (injectable)
    embeddings, and `loader` defaults to load_any but tests can hand in a
    fake. `documents_dir` is where source files live, named `<doc_id>.<ext>`.
    """

    def __init__(self, index, documents_dir: str = None, loader=None, splitter=None):
        from src.knowledge.loaders import load_any
        from src.config import settings
        self.index = index
        self._documents_dir = Path(documents_dir or settings.documents_dir)
        self._loader = loader or load_any
        self._splitter = splitter or make_splitter()

    def load_document(self, doc_id: str) -> list:
        """Find the source file for doc_id and load it into Documents."""
        matches = sorted(self._documents_dir.glob(f"{doc_id}.*"))
        if not matches:
            raise FileNotFoundError(f"No source file for doc_id={doc_id!r} "
                                    f"in {self._documents_dir}")
        return self._loader(str(matches[0]))

    def split_and_embed(self, docs: list) -> list:
        """Split into chunks. The embedding itself happens as the chunks
        enter the index (the store owns the embedder); the name reflects the
        conceptual step the chapter describes."""
        return split_documents(docs, self._splitter)

    def reindex(self, doc_id: str) -> dict:
        """Re-load one changed document and swap its chunks in the index."""
        doc = self.load_document(doc_id)
        chunks = self.split_and_embed(doc)
        self.index.replace(doc_id, chunks)
        return {"doc_id": doc_id, "chunks": len(chunks)}
