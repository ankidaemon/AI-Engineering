import re
from dataclasses import dataclass
from typing import Iterator
from src.ingestion.document_loader import Document


@dataclass
class Chunk:
    content: str
    metadata: dict
    chunk_id: str
    doc_id: str
    chunk_index: int


# Matches standard academic paper section headers.
# Placed at module level so it is compiled once.
SECTION_HEADER_RE = re.compile(
    r'^(?:Abstract|Introduction|Related Work|Background|Preliminaries|'
    r'Problem Formulation|Methodology|Methods?|Approach|Architecture|'
    r'Experimental(?: Setup)?|Experiments?|Results?|Evaluation|'
    r'Discussion|Analysis|Ablation|Conclusion|Future Work|'
    r'Acknowledgem(?:ent|ent)s?|References|Appendix(?:\s+\w+)?)\s*$',
    re.MULTILINE | re.IGNORECASE
)

# Patterns indicating content that must never be split mid-block
PROTECTED_BLOCK_RE = re.compile(
    r'```[\s\S]*?```'            # fenced code blocks
    r'|\$\$[\s\S]*?\$\$'         # display math
    r'|\|(?:[^|\n]*\|){2,}',     # markdown tables (2+ columns)
    re.MULTILINE
)


class SemanticChunker:
    """
    Splits documents into semantically coherent chunks by respecting:
    - Academic paper section boundaries
    - Paragraph breaks
    - Sentence boundaries
    - Protected blocks (code, math, tables) that must stay intact

    Maintains sentence-level overlap between consecutive chunks so that
    cross-boundary context is not lost during retrieval.
    """

    def __init__(
        self,
        max_tokens: int = 512,
        min_tokens: int = 100,
        overlap_sentences: int = 2
    ):
        self.max_tokens = max_tokens
        self.min_tokens = min_tokens
        self.overlap_sentences = overlap_sentences

    def chunk_document(self, document: Document) -> Iterator[Chunk]:
        sections = self._split_by_sections(document.content)
        chunk_index = 0

        for section_name, section_text in sections:
            # Separate out any protected blocks before splitting
            units = self._split_with_protected_blocks(section_text)
            sentence_buffer: list[str] = []
            token_count = 0

            for unit, is_protected in units:
                unit_tokens = len(unit.split())

                # Protected blocks always emit as their own chunk
                if is_protected:
                    if sentence_buffer:
                        text = " ".join(sentence_buffer)
                        if len(text.split()) >= self.min_tokens:
                            yield self._make_chunk(
                                text, document, section_name, chunk_index
                            )
                            chunk_index += 1
                        sentence_buffer = sentence_buffer[-self.overlap_sentences:]
                        token_count = sum(len(s.split()) for s in sentence_buffer)

                    if unit_tokens >= self.min_tokens:
                        yield self._make_chunk(
                            unit, document, section_name, chunk_index
                        )
                        chunk_index += 1
                    continue

                # Regular text: split into sentences and buffer
                sentences = self._split_sentences(unit)
                for sentence in sentences:
                    s_tokens = len(sentence.split())

                    if (token_count + s_tokens > self.max_tokens
                            and sentence_buffer):
                        text = " ".join(sentence_buffer)
                        if len(text.split()) >= self.min_tokens:
                            yield self._make_chunk(
                                text, document, section_name, chunk_index
                            )
                            chunk_index += 1

                        # Carry forward overlap sentences
                        sentence_buffer = sentence_buffer[-self.overlap_sentences:]
                        token_count = sum(len(s.split()) for s in sentence_buffer)

                    sentence_buffer.append(sentence)
                    token_count += s_tokens

            # Emit any remaining text in this section
            if sentence_buffer:
                text = " ".join(sentence_buffer)
                if len(text.split()) >= self.min_tokens:
                    yield self._make_chunk(
                        text, document, section_name, chunk_index
                    )
                    chunk_index += 1

    def _make_chunk(
        self, text: str, doc: Document, section: str, idx: int
    ) -> Chunk:
        return Chunk(
            content=text.strip(),
            metadata={**doc.metadata, "section": section, "chunk_index": idx},
            chunk_id=f"{doc.doc_id}_chunk_{idx}",
            doc_id=doc.doc_id,
            chunk_index=idx
        )

    def _split_by_sections(self, text: str) -> list[tuple[str, str]]:
        parts = SECTION_HEADER_RE.split(text)
        headers = SECTION_HEADER_RE.findall(text)
        if not headers:
            return [("body", text)]
        result = [("preamble", parts[0])]
        for header, content in zip(headers, parts[1:]):
            result.append((header.strip(), content))
        return result

    def _split_with_protected_blocks(
        self, text: str
    ) -> list[tuple[str, bool]]:
        """
        Returns a list of (unit_text, is_protected) tuples.
        Protected blocks (code, math, tables) are flagged to prevent splitting.
        """
        result = []
        last_end = 0
        for match in PROTECTED_BLOCK_RE.finditer(text):
            before = text[last_end:match.start()]
            if before.strip():
                result.append((before, False))
            result.append((match.group(), True))
            last_end = match.end()
        remaining = text[last_end:]
        if remaining.strip():
            result.append((remaining, False))
        return result

    def _split_sentences(self, text: str) -> list[str]:
        # Split on sentence-terminal punctuation followed by whitespace
        # and an uppercase letter or quote — handles abbreviations better
        # than a simple period split.
        raw = re.split(r'(?<=[.!?])\s+(?=[A-Z"\'(\[])', text)
        return [s.strip() for s in raw if s.strip()]
