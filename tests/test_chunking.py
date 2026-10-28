import json
from pathlib import Path

import pytest

from policydrift.ingest.build import build_chunks
from policydrift.ingest.chunking import chunk_spans, paragraph_spans


def _texts(text: str, spans: list[tuple[int, int]]) -> list[str]:
    return [text[s:e] for s, e in spans]


def test_paragraph_spans_skip_blank_runs() -> None:
    text = "A one.\n\n\nB two.\n \nC three."
    assert _texts(text, paragraph_spans(text, 0, len(text))) == ["A one.", "B two.", "C three."]


def test_paragraphs_are_merged_up_to_the_limit_and_never_cut() -> None:
    text = "aaaa\n\nbbbb\n\ncccc"
    assert _texts(text, chunk_spans(text, 0, len(text), max_chars=10)) == ["aaaa\n\nbbbb", "cccc"]
    assert _texts(text, chunk_spans(text, 0, len(text), max_chars=3)) == ["aaaa", "bbbb", "cccc"]


def test_long_paragraph_splits_at_sentence_ends_including_danda() -> None:
    text = "पहला वाक्य है। दूसरा वाक्य है। तीसरा वाक्य है।"
    chunks = _texts(text, chunk_spans(text, 0, len(text), max_chars=20))
    assert chunks == ["पहला वाक्य है।", "दूसरा वाक्य है।", "तीसरा वाक्य है।"]


def test_table_cells_stay_together() -> None:
    text = "0-4 lakh rupees\n\nNil\n\n4-8 lakh rupees\n\n5 per cent"
    assert _texts(text, chunk_spans(text, 0, len(text), max_chars=800)) == [text]


def test_spans_respect_the_body_window() -> None:
    text = "HEADER\n\nbody one\n\nbody two\n\nFOOTER"
    start, end = text.index("body one"), text.index("body two") + len("body two")
    assert _texts(text, chunk_spans(text, start, end, max_chars=800)) == ["body one\n\nbody two"]


def test_non_positive_limit_is_rejected() -> None:
    with pytest.raises(ValueError):
        chunk_spans("x", 0, 1, max_chars=0)


def test_built_chunks_carry_version_metadata_and_valid_offsets(root: Path) -> None:
    chunks = list(build_chunks(root))
    assert chunks, "no chunks built"
    ids = [c.chunk_id for c in chunks]
    assert len(ids) == len(set(ids))
    assert {c.language for c in chunks} == {"en", "hi", "gu"}
    for c in chunks:
        assert c.text.strip()
        assert c.raw_end > c.raw_start
        raw = (root / "data" / "raw" / c.source_path).read_text(encoding="utf-8")
        assert c.raw_end <= len(raw)
        if c.effective_from and c.effective_to:
            assert c.effective_from <= c.effective_to
        assert "Release ID" not in c.text and "रिलीज़ आईडी" not in c.text


def test_build_is_deterministic(root: Path) -> None:
    first = [c.model_dump_json() for c in build_chunks(root)]
    second = [c.model_dump_json() for c in build_chunks(root)]
    assert first == second


def test_committed_chunks_file_is_up_to_date(root: Path) -> None:
    path = root / "data" / "processed" / "chunks.jsonl"
    committed = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    rebuilt = [json.loads(c.model_dump_json()) for c in build_chunks(root)]
    assert committed == rebuilt, "run `uv run policydrift ingest chunk` and commit the result"


def test_facts_that_changed_are_present_in_the_right_versions(root: Path) -> None:
    by_version: dict[tuple[str, str, str], str] = {}
    for c in build_chunks(root):
        key = (c.scheme, c.version, c.language)
        by_version[key] = by_version.get(key, "") + "\n" + c.text
    assert "up to 9 refills" in by_version[("pmuy-subsidy", "v3", "en")]
    assert "125 days" in by_version[("rural-employment-guarantee", "v2", "en")]
    assert "₹6 lakh up to ₹9 lakh" in by_version[("pmay-urban", "v2", "en")]
    assert "3-7 लाख रुपए" in by_version[("income-tax-new-regime", "fy2024-25", "hi")]
