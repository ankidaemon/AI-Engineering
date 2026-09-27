"""The FAISS knowledge index: search, replace, persistence (§4.3, §4.5)."""
from langchain_core.documents import Document

from src.vectorstores.faiss_store import KnowledgeIndex


def _doc(text, **meta):
    return Document(page_content=text, metadata={"source": "test", **meta})


def test_search_finds_relevant_passage_with_metadata(tmp_path, embeddings):
    index = KnowledgeIndex(persist_dir=str(tmp_path / "faiss"), embeddings=embeddings)
    index.replace("fees", [
        _doc("The late payment fee for the travel card is 25.00.",
             product="travel-card", effective_date="2026-06-01"),
        _doc("A cheque book arrives within four working days.",
             product="general"),
    ])
    hits = index.search("late payment fee travel card", k=1)
    assert len(hits) == 1
    assert "25.00" in hits[0].text
    assert hits[0].metadata["product"] == "travel-card"
    assert 0.0 < hits[0].relevance <= 1.0


def test_replace_swaps_a_changed_document(tmp_path, embeddings):
    """The freshness mechanism (Failure 1): the old fee must be gone."""
    index = KnowledgeIndex(persist_dir=str(tmp_path / "faiss"), embeddings=embeddings)
    index.replace("fees", [_doc("The late payment fee is 25.00.")])
    index.replace("fees", [_doc("The late payment fee is 30.00.")])

    hits = index.search("late payment fee", k=5)
    texts = [h.text for h in hits]
    assert any("30.00" in t for t in texts)
    assert not any("25.00" in t for t in texts)
    assert index.document_count == 1


def test_replace_touches_only_its_own_document(tmp_path, embeddings):
    index = KnowledgeIndex(persist_dir=str(tmp_path / "faiss"), embeddings=embeddings)
    index.replace("fees", [_doc("The late payment fee is 25.00.")])
    index.replace("faq", [_doc("Q: How do I order cheques?\nA: Ask the assistant.")])
    index.replace("fees", [_doc("The late payment fee is 30.00.")])

    texts = [h.text for h in index.search("order cheques", k=5)]
    assert any("cheques" in t for t in texts)


def test_index_survives_a_restart(tmp_path, embeddings):
    persist = str(tmp_path / "faiss")
    KnowledgeIndex(persist_dir=persist, embeddings=embeddings).replace(
        "fees", [_doc("The annual fee for the travel card is 95.00.")])

    reopened = KnowledgeIndex(persist_dir=persist, embeddings=embeddings)
    hits = reopened.search("annual fee travel card", k=1)
    assert "95.00" in hits[0].text
    # replace still works after reload — chunk ids were persisted too
    reopened.replace("fees", [_doc("The annual fee for the travel card is 99.00.")])
    texts = [h.text for h in reopened.search("annual fee", k=5)]
    assert not any("95.00" in t for t in texts)


def test_empty_index_returns_nothing(tmp_path, embeddings):
    index = KnowledgeIndex(persist_dir=str(tmp_path / "faiss"), embeddings=embeddings)
    assert index.search("anything") == []
