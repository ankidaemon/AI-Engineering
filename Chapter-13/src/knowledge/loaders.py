"""
Loaders for the sources a bank actually has (§4.2).

FAQs live in a support system export, product terms and policy live in text
or markdown written by other teams, and fee schedules live in spreadsheets.
Each loader knows one format and produces the same clean output: LangChain
`Document` objects with a shared metadata shape. The metadata is where
banking gets specific — every chunk carries the product it concerns, the
document type, and an effective date, because a stale fee quoted with
confidence is Failure 1 in the chapter.

Shared metadata keys:
    doc_id          stable id for the whole source document (drives replace())
    source          human-readable origin, used for citation
    doc_type        "faq" | "fees" | "policy"
    product         which product the text concerns (may be "general")
    effective_date  ISO date the content took effect
    natural_unit    True when the document arrives pre-chunked (FAQ, fee row)
                    and must NOT be split further (§4.3)
"""
import csv
import json
from pathlib import Path

from langchain_core.documents import Document


def load_faq_json(path: str) -> list:
    """One FAQ entry = one Document. A question and its answer are a natural
    unit; splitting between them would separate the answer from the question
    it answers."""
    path = Path(path)
    entries = json.loads(path.read_text())
    docs = []
    for entry in entries:
        docs.append(Document(
            page_content=f"Q: {entry['question']}\nA: {entry['answer']}",
            metadata={
                "doc_id": path.stem,
                "source": f"{path.name} — {entry['question']}",
                "doc_type": "faq",
                "product": entry.get("product", "general"),
                "effective_date": entry.get("effective_date", ""),
                "natural_unit": True,
            },
        ))
    return docs


def load_fee_schedule_csv(path: str) -> list:
    """One fee row = one Document, rendered as a plain sentence so retrieval
    matches the way customers ask ("what is the late fee")."""
    path = Path(path)
    docs = []
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            sentence = (f"The {row['fee_name']} for the {row['product']} "
                        f"is {row['amount']}.")
            docs.append(Document(
                page_content=sentence,
                metadata={
                    "doc_id": path.stem,
                    "source": f"{path.name} — {row['fee_name']}",
                    "doc_type": "fees",
                    "product": row["product"],
                    "effective_date": row.get("effective_date", ""),
                    "natural_unit": True,
                },
            ))
    return docs


def load_policy_text(path: str, product: str = "general",
                     effective_date: str = "") -> list:
    """Policy and terms documents arrive as one long text and DO need
    splitting — that happens in ingest.py, on the clause boundaries the
    document already has, not here."""
    path = Path(path)
    return [Document(
        page_content=path.read_text(),
        metadata={
            "doc_id": path.stem,
            "source": path.name,
            "doc_type": "policy",
            "product": product,
            "effective_date": effective_date,
            "natural_unit": False,
        },
    )]


# Extension -> loader. load_any() is what the ingestion pipeline calls, so a
# new source format needs only a new loader and one line here.
_LOADERS = {
    ".json": load_faq_json,
    ".csv": load_fee_schedule_csv,
    ".md": load_policy_text,
    ".txt": load_policy_text,
}


def load_any(path: str) -> list:
    suffix = Path(path).suffix.lower()
    loader = _LOADERS.get(suffix)
    if loader is None:
        raise ValueError(f"No loader for {suffix} files: {path}")
    return loader(path)
