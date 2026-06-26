"""
Loader tests. Text and CSV go through real loaders; unsupported extensions raise;
a missing file surfaces FileNotFoundError. No model or network required.
"""
import pytest

from src.loaders.advanced_document_loader import MultiFormatLoader, RobustPDFLoader


def test_load_text(tmp_path):
    p = tmp_path / "note.txt"
    p.write_text("hello world from a plain text file")
    docs = MultiFormatLoader().load(str(p))
    assert docs and "hello world" in docs[0].page_content
    assert docs[0].metadata["loader"] == "text"


def test_load_markdown_as_text(tmp_path):
    p = tmp_path / "doc.md"
    p.write_text("# Title\n\nSome **markdown** body.")
    docs = MultiFormatLoader().load(str(p))
    assert docs and "markdown" in docs[0].page_content


def test_unsupported_format_raises(tmp_path):
    p = tmp_path / "data.xyz"
    p.write_text("x")
    with pytest.raises(ValueError):
        MultiFormatLoader().load(str(p))


def test_missing_pdf_raises():
    with pytest.raises(FileNotFoundError):
        RobustPDFLoader().load("/no/such/file.pdf")
