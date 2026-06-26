"""
Retrieval-strategy tests. These exercise the *guardrails* that fix the production
failures (Section VII) — the HyDE gate and the multi-query relevance filter —
using fake models/embeddings, so they run offline.
"""
from langchain_core.documents import Document

from src.retrieval.hyde import should_use_hyde
from src.retrieval.multi_query import filter_irrelevant_results


class _FakeResp:
    def __init__(self, content):
        self.content = content


class _FakeModel:
    def __init__(self, content):
        self._content = content

    def invoke(self, _messages):
        return _FakeResp(self._content)


class _FakeEmbeddings:
    """Two-dimensional embedding: 'good' text -> [1,0], everything else -> [0,1]."""
    def embed_query(self, text: str):
        return [1.0, 0.0] if "good" in text.lower() else [0.0, 1.0]


# ── HyDE gate (Failure 6) ─────────────────────────────────────────────

def test_should_use_hyde_for_descriptive_query():
    assert should_use_hyde("explain the payment terms", _FakeModel("RETRIEVE")) is True


def test_should_not_use_hyde_for_existence_query():
    assert should_use_hyde("does clause X exist?", _FakeModel("EXISTS")) is False


# ── multi-query relevance filter (Failure 3) ──────────────────────────

def test_filter_drops_off_topic_results():
    docs = [Document(page_content="good relevant match"),
            Document(page_content="bad off-topic match")]
    kept = filter_irrelevant_results(docs, "good", _FakeEmbeddings(), threshold=0.7)
    assert len(kept) == 1
    assert "good" in kept[0].page_content


def test_filter_keeps_all_when_threshold_low():
    docs = [Document(page_content="good one"), Document(page_content="bad one")]
    kept = filter_irrelevant_results(docs, "good", _FakeEmbeddings(), threshold=-1.0)
    assert len(kept) == 2
