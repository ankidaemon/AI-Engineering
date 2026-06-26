"""
General-purpose, deterministic document tools (Chapter 11, Section 2.1).

Every tool here is plain Python — no model call. That makes them fast, free, and
perfectly reliable. The docstring on each `@tool` is what the agent reads to
decide whether and when to call it, so the docstrings are written for the model.
"""
import re

from langchain_core.tools import tool


@tool
def word_count(text: str) -> dict:
    """
    Counts words, sentences, and paragraphs in a text.
    Use this when you need to understand the length and structure of a document.
    """
    words      = len(text.split())
    sentences  = len([s for s in text.split(".") if s.strip()])
    paragraphs = len([p for p in text.split("\n\n") if p.strip()])
    return {
        "words":               words,
        "sentences":           sentences,
        "paragraphs":          paragraphs,
        "avg_sentence_length": round(words / max(sentences, 1), 1),
    }


@tool
def extract_dates(text: str) -> list[str]:
    """
    Extracts all date references from a document.
    Returns a list of date strings found (e.g., "January 15, 2024", "2024-01-15").
    Use this to identify timeline-critical information in contracts or reports.
    """
    patterns = [
        r"\b\d{4}-\d{2}-\d{2}\b",                                            # 2024-01-15
        r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4}\b",
        r"\b\d{1,2}/\d{1,2}/\d{2,4}\b",                                     # 01/15/2024
        r"\b(?:Q[1-4])\s+\d{4}\b",                                          # Q1 2024
    ]
    dates: list[str] = []
    for pattern in patterns:
        dates.extend(re.findall(pattern, text, re.IGNORECASE))
    return sorted(set(dates))   # deduplicate, stable order


@tool
def calculate_readability(text: str) -> dict:
    """
    Computes readability metrics for a document.
    Returns the Flesch reading-ease score and Flesch-Kincaid grade level.
    Use this to assess how complex a document is to read.
    """
    words     = text.split()
    sentences = [s.strip() for s in re.split(r"[.!?]", text) if s.strip()]
    if not sentences or not words:
        return {"error": "Text too short to assess"}

    syllables               = sum(_count_syllables(w) for w in words)
    avg_sentence_length     = len(words) / len(sentences)
    avg_syllables_per_word  = syllables / len(words)

    reading_ease = 206.835 - 1.015 * avg_sentence_length - 84.6 * avg_syllables_per_word
    grade_level  = 0.39 * avg_sentence_length + 11.8 * avg_syllables_per_word - 15.59

    return {
        "reading_ease":   round(reading_ease, 1),
        "grade_level":    round(grade_level, 1),
        "complexity":     "high" if grade_level > 14 else
                          "medium" if grade_level > 10 else "low",
        "word_count":     len(words),
        "sentence_count": len(sentences),
    }


def _count_syllables(word: str) -> int:
    """A simple English syllable-count heuristic (good enough for readability)."""
    word = word.lower().strip(".,!?;:\"'()")
    vowels = "aeiouy"
    count, prev_vowel = 0, False
    for char in word:
        is_vowel = char in vowels
        if is_vowel and not prev_vowel:
            count += 1
        prev_vowel = is_vowel
    if word.endswith("e") and count > 1:
        count -= 1
    return max(1, count)
