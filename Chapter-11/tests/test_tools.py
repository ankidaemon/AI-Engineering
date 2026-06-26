"""
Tool tests. The deterministic tools run directly (no model). The model-backed
legal/technical tools are exercised only through their pure parsing helpers, so
the whole file runs offline.
"""
from src.tools.document_tools import word_count, extract_dates, calculate_readability
from src.tools.legal_specific_tools import _extract_json_obligations, _parse_bullets


# ── deterministic tools ───────────────────────────────────────────────

def test_word_count():
    result = word_count.invoke("The quick brown fox. It jumps over the lazy dog.")
    assert result["words"] >= 9
    assert result["sentences"] >= 2


def test_extract_dates_finds_multiple_formats():
    text = "Contract dated January 15, 2024. Expires 2025-12-31. Signed Q3 2024."
    dates = extract_dates.invoke(text)
    assert len(dates) >= 2
    assert any("2024" in d for d in dates)


def test_extract_dates_deduplicates():
    dates = extract_dates.invoke("2024-01-01 and again 2024-01-01")
    assert dates.count("2024-01-01") == 1


def test_readability_returns_metrics():
    text = (
        "The indemnification obligations herein shall survive termination of this "
        "agreement notwithstanding any provision to the contrary, subject to the "
        "limitations set forth in Section 12.3 thereof. "
    ) * 4
    result = calculate_readability.invoke(text)
    assert "grade_level" in result
    assert result["complexity"] in ("low", "medium", "high")


def test_readability_handles_empty():
    assert "error" in calculate_readability.invoke("")


# ── pure parsing helpers from the model-backed tools ──────────────────

def test_extract_json_obligations_valid():
    out = _extract_json_obligations(
        'Here you go: {"obligations": [{"party": "A", "action": "pay"}]} done')
    assert out["obligations"][0]["party"] == "A"


def test_extract_json_obligations_fallback():
    out = _extract_json_obligations("no json present here")
    assert out["obligations"][0]["raw"] == "no json present here"


def test_parse_bullets():
    assert _parse_bullets("- first item\n- second item") == ["first item", "second item"]


def test_parse_bullets_fallback_to_raw():
    assert _parse_bullets("just prose, no bullets") == ["just prose, no bullets"]
