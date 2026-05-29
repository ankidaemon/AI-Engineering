import re
import pickle
import logging
from pathlib import Path
from rank_bm25 import BM25Okapi
from src.ingestion.chunker import Chunk

logger = logging.getLogger(__name__)


class BM25Index:
    """
    In-memory BM25 index persisted to disk between application restarts.

    BM25Okapi uses Robertson's formulation with default k1=1.5, b=0.75.
    For highly technical corpora where terms are very long and rare,
    reducing k1 to 0.9-1.2 reduces the impact of term frequency
    saturation and tends to improve precision.

    Stopword filtering is applied before indexing and querying to reduce
    noise from high-frequency function words that carry no semantic weight.
    """

    PERSIST_PATH = Path("./data/bm25_index.pkl")

    STOPWORDS = frozenset([
        "the", "a", "an", "and", "or", "but", "in", "on", "at",
        "to", "for", "of", "with", "by", "from", "as", "into",
        "is", "was", "are", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will",
        "that", "this", "it", "its", "they", "their", "we",
        "our", "you", "your", "he", "she", "his", "her"
    ])

    def __init__(self):
        self._index: BM25Okapi | None = None
        self._chunks: list[Chunk] = []
        self._load_from_disk()

    def tokenize(self, text: str) -> list[str]:
        text = text.lower()
        text = re.sub(r'[^a-z0-9\-\s]', ' ', text)
        return [
            t for t in text.split()
            if len(t) > 2 and t not in self.STOPWORDS
        ]

    def index_chunks(self, chunks: list[Chunk]):
        """
        Appends new chunks to the index and rebuilds. Rebuilding on every
        call is acceptable for offline ingestion; for online incremental
        indexing, consider a different data structure.
        """
        self._chunks.extend(chunks)
        tokenized = [self.tokenize(c.content) for c in self._chunks]
        self._index = BM25Okapi(tokenized)
        self._persist()
        logger.info(f"BM25: indexed {len(self._chunks)} total chunks")

    def query(self, query_text: str, top_k: int = 10) -> list[dict]:
        if not self._index or not self._chunks:
            return []

        tokens = self.tokenize(query_text)
        if not tokens:
            return []

        scores = self._index.get_scores(tokens)
        ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)

        return [
            {
                "chunk_id": self._chunks[i].chunk_id,
                "score":    float(scores[i]),
                "content":  self._chunks[i].content,
                "metadata": self._chunks[i].metadata
            }
            for i in ranked[:top_k]
            if scores[i] > 0
        ]

    def document_count(self) -> int:
        return len(self._chunks)

    def _persist(self):
        self.PERSIST_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(self.PERSIST_PATH, "wb") as f:
            pickle.dump({"index": self._index, "chunks": self._chunks}, f)
        logger.debug(f"BM25: persisted to {self.PERSIST_PATH}")

    def _load_from_disk(self):
        if self.PERSIST_PATH.exists():
            with open(self.PERSIST_PATH, "rb") as f:
                data = pickle.load(f)
            self._index = data["index"]
            self._chunks = data["chunks"]
            logger.info(f"BM25: loaded {len(self._chunks)} chunks from disk")
