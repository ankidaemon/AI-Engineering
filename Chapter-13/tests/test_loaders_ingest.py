"""Loaders and the ingestion pipeline (§4.2, §4.3)."""
import json

import pytest

from src.knowledge.ingest import IngestionPipeline, split_documents
from src.knowledge.loaders import (load_any, load_faq_json,
                                   load_fee_schedule_csv, load_policy_text)


@pytest.fixture
def faq_file(tmp_path):
    path = tmp_path / "card-faq.json"
    path.write_text(json.dumps([
        {"question": "What is the late fee?",
         "answer": "The late fee is 25.00.",
         "product": "cashback-card", "effective_date": "2026-06-01"},
        {"question": "How do I close my account?",
         "answer": "Visit any branch with identification."},
    ]))
    return str(path)


def test_faq_entries_become_natural_units(faq_file):
    docs = load_faq_json(faq_file)
    assert len(docs) == 2
    first = docs[0]
    assert "Q: What is the late fee?" in first.page_content
    assert first.metadata["doc_type"] == "faq"
    assert first.metadata["product"] == "cashback-card"
    assert first.metadata["effective_date"] == "2026-06-01"
    assert first.metadata["natural_unit"] is True
    assert first.metadata["doc_id"] == "card-faq"


def test_fee_rows_become_sentences(tmp_path):
    path = tmp_path / "fees.csv"
    path.write_text("fee_name,product,amount,effective_date\n"
                    "late payment fee,travel-card,25.00,2026-06-01\n")
    docs = load_fee_schedule_csv(str(path))
    assert len(docs) == 1
    assert docs[0].page_content == "The late payment fee for the travel-card is 25.00."
    assert docs[0].metadata["doc_type"] == "fees"
    assert docs[0].metadata["natural_unit"] is True


def test_policy_text_is_one_document_awaiting_split(tmp_path):
    path = tmp_path / "terms.md"
    path.write_text("Some terms.\n\nMore terms.")
    docs = load_policy_text(str(path), product="travel-card",
                            effective_date="2026-04-01")
    assert len(docs) == 1
    assert docs[0].metadata["natural_unit"] is False
    assert docs[0].metadata["product"] == "travel-card"


def test_load_any_dispatches_on_extension(faq_file):
    assert load_any(faq_file)[0].metadata["doc_type"] == "faq"
    with pytest.raises(ValueError):
        load_any("statement.xlsx")


def test_natural_units_are_never_split(faq_file):
    docs = load_faq_json(faq_file)
    assert split_documents(docs) == docs


def test_long_policy_splits_and_keeps_metadata(tmp_path):
    paragraphs = "\n\n".join(f"Clause {i}. " + ("Words in the clause. " * 20)
                             for i in range(6))
    path = tmp_path / "terms.md"
    path.write_text(paragraphs)
    chunks = split_documents(load_policy_text(str(path)))
    assert len(chunks) > 1
    assert all(len(c.page_content) <= 700 for c in chunks)
    assert all(c.metadata["doc_id"] == "terms" for c in chunks)


def test_pipeline_finds_source_by_doc_id(tmp_path, faq_file):
    class RecordingIndex:
        def replace(self, doc_id, chunks):
            self.replaced = (doc_id, len(chunks))

    index = RecordingIndex()
    pipeline = IngestionPipeline(index, documents_dir=str(tmp_path))
    result = pipeline.reindex("card-faq")
    assert result == {"doc_id": "card-faq", "chunks": 2}
    assert index.replaced == ("card-faq", 2)

    with pytest.raises(FileNotFoundError):
        pipeline.load_document("no-such-doc")
