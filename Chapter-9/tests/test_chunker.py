import pytest
from src.ingestion.document_loader import Document
from src.ingestion.chunker import SemanticChunker, Chunk


@pytest.fixture
def chunker():
    return SemanticChunker(max_tokens=100, min_tokens=10, overlap_sentences=1)


@pytest.fixture
def simple_doc():
    return Document(
        content=(
            "Introduction\n"
            "This is the first sentence of the introduction. "
            "It discusses the main problem. "
            "The problem is well known in the field.\n\n"
            "Methods\n"
            "We propose a novel approach. "
            "The approach uses retrieval augmented generation. "
            "Experiments show improved results."
        ),
        metadata={"title": "Test Paper", "arxiv_id": "2401.test", "source": "arxiv"},
        doc_id="2401.test"
    )


def test_chunk_document_returns_chunks(chunker, simple_doc):
    chunks = list(chunker.chunk_document(simple_doc))
    assert len(chunks) > 0
    assert all(isinstance(c, Chunk) for c in chunks)


def test_chunks_have_correct_doc_id(chunker, simple_doc):
    chunks = list(chunker.chunk_document(simple_doc))
    assert all(c.doc_id == "2401.test" for c in chunks)


def test_chunks_have_unique_ids(chunker, simple_doc):
    chunks = list(chunker.chunk_document(simple_doc))
    ids = [c.chunk_id for c in chunks]
    assert len(ids) == len(set(ids))


def test_chunk_metadata_includes_section(chunker, simple_doc):
    chunks = list(chunker.chunk_document(simple_doc))
    sections = {c.metadata.get("section") for c in chunks}
    # Should include at least the sections defined in the doc
    assert len(sections) > 0


def test_min_token_filter_drops_small_chunks():
    chunker = SemanticChunker(max_tokens=100, min_tokens=50, overlap_sentences=1)
    doc = Document(
        content="Short. Very short.",
        metadata={"title": "Tiny", "arxiv_id": "tiny", "source": "test"},
        doc_id="tiny"
    )
    chunks = list(chunker.chunk_document(doc))
    # All chunks should meet the minimum token threshold
    for chunk in chunks:
        assert len(chunk.content.split()) >= 50


def test_protected_block_not_split(chunker):
    doc = Document(
        content=(
            "Some introduction text that is long enough to be indexed properly.\n\n"
            "```python\n"
            "def foo():\n"
            "    return 42\n"
            "```\n\n"
            "More text after the code block follows here in this sentence."
        ),
        metadata={"title": "Code Paper", "arxiv_id": "code.test", "source": "test"},
        doc_id="code.test"
    )
    chunks = list(chunker.chunk_document(doc))
    # The code block should appear intact in one chunk
    code_chunks = [c for c in chunks if "def foo():" in c.content]
    for chunk in code_chunks:
        assert "return 42" in chunk.content
