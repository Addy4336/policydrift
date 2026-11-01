import csv
import hashlib
import json
import shutil
from collections.abc import Sequence
from pathlib import Path

import httpx
import numpy as np
import pytest

from policydrift.bench.split import FrozenSplitError, TestSplitLocked, load_items
from policydrift.experiments.config import ExperimentConfig, load_config
from policydrift.experiments.prompts import build_prompt
from policydrift.experiments.runner import (
    plan,
    planned_conditions,
    run_experiment,
    select_context,
    select_items,
)
from policydrift.ingest.registry import load_registry
from policydrift.llm import LLMClient, ResponseCache
from policydrift.retrieval.embed import EmbeddingCache, EmbedModel, Matrix
from policydrift.retrieval.search import Retriever, load_chunks
from policydrift.scoring.agreement import (
    agreement_report,
    export_label_sheet,
    pick_sample,
)
from policydrift.scoring.pipeline import load_answers, score_run, summarise

FAKE = EmbedModel("fake", "fake")


class HashEmbedder:
    """Cheap bag-of-words embedder so retrieval tests need no model download."""

    model = FAKE

    def encode(self, texts: Sequence[str]) -> Matrix:
        out = np.zeros((len(texts), 128), dtype=np.float32)
        for i, text in enumerate(texts):
            for token in text.lower().split():
                h = int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16)
                out[i, h % 128] += 1.0
            norm = np.linalg.norm(out[i])
            out[i] /= norm or 1.0
        return out


@pytest.fixture
def retriever(root: Path, tmp_path: Path) -> Retriever:
    chunks = load_chunks(root / "data" / "processed" / "chunks.jsonl")
    registry = load_registry(root / "data" / "schemes.yaml")
    cache = EmbeddingCache(tmp_path / "emb", FAKE)
    return Retriever(chunks, HashEmbedder(), cache, registry)


def _cfg(**changes: object) -> ExperimentConfig:
    base = ExperimentConfig(
        name="t",
        models=["groq-gpt-oss-20b"],
        conditions=["R0", "R1", "R2", "R3", "R4", "X"],
        item_limit=3,
    )
    return base.model_copy(update=changes)


def test_shipped_configs_load(root: Path) -> None:
    for path in (root / "configs" / "experiments").glob("*.yaml"):
        assert load_config(path).split == "dev"  # tuning configs never point at the test split


def test_x_condition_is_skipped_for_english() -> None:
    cfg = _cfg()
    assert "X" not in planned_conditions(cfg, "en")
    assert "X" in planned_conditions(cfg, "hi")


def test_conditions_retrieve_the_right_versions(root: Path, retriever: Retriever) -> None:
    items = select_items(_cfg(), root, final=False)
    item = next(i for i in items if i.current.version != i.old.version)
    cfg = _cfg()
    cur, old = item.current.version, item.old.version
    assert select_context(retriever, item, "en", "R0", cfg, 0).chunks == []
    r2 = select_context(retriever, item, "en", "R2", cfg, 0)
    assert r2.chunks and {c.version for c in r2.chunks} == {cur}
    r3 = select_context(retriever, item, "en", "R3", cfg, 0)
    assert {c.version for c in r3.chunks} == {cur, old}
    assert r3.chunks[0].version == cur  # position 0 is counterbalanced to current-first
    r3b = select_context(retriever, item, "en", "R3", cfg, 1)
    assert r3b.chunks[0].version == old
    x = select_context(retriever, item, "hi", "X", cfg, 0)
    assert x.doc_language == "en" and {c.language for c in x.chunks} == {"en"}
    r1 = select_context(retriever, item, "en", "R1", cfg, 0)
    assert len(r1.chunks) <= cfg.k


def test_prompt_shows_dates_only_when_asked(root: Path, retriever: Retriever) -> None:
    item = select_items(_cfg(), root, final=False)[0]
    ctx = select_context(retriever, item, "en", "R3", _cfg(), 0)
    assert "in force from" in build_prompt("Q?", ctx.chunks, show_dates=True)
    assert "in force from" not in build_prompt("Q?", ctx.chunks, show_dates=False)
    assert build_prompt("Q?", [], show_dates=True) == "Question: Q?"


def test_test_split_needs_the_final_flag(root: Path) -> None:
    cfg = _cfg(split="test")
    with pytest.raises(TestSplitLocked, match="--final"):
        select_items(cfg, root, final=False)
    with pytest.raises((FrozenSplitError, TestSplitLocked)):
        load_items(root, "test")


def _sandbox(root: Path, tmp_path: Path) -> Path:
    box = tmp_path / "box"
    for rel in ("configs/models.yaml", "data/benchmark/dev/items.jsonl"):
        dest = box / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(root / rel, dest)
    return box


def _client(tmp_path: Path, answer: str) -> LLMClient:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "model": "m-1",
                "choices": [{"message": {"content": answer}}],
                "usage": {"prompt_tokens": 5, "completion_tokens": 2},
            },
        )

    return LLMClient(
        ResponseCache(tmp_path / "c.sqlite"),
        {"groq": "k", "gemini": "k"},
        {"groq": 1000, "gemini": 1000},
        http=httpx.Client(transport=httpx.MockTransport(handler)),
        sleep=lambda _s: None,
    )


def test_run_logs_raw_answers_and_scores_them(
    root: Path, tmp_path: Path, retriever: Retriever
) -> None:
    box = _sandbox(root, tmp_path)
    cfg = _cfg(conditions=["R0", "R3"], languages=["en", "hi"])
    client = _client(tmp_path, "It is Rs 1,00,000.")
    dry = run_experiment(cfg, box, client, retriever, dry_run=True)
    assert dry["planned_calls"] == 3 * 2 * 2 and dry["uncached_calls"] == dry["planned_calls"]
    assert not (box / "runs").exists()

    summary = run_experiment(cfg, box, client, retriever)
    run_dir = box / "runs" / summary["run_id"]
    meta = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    assert meta["config"]["name"] == "t" and meta["git"]["commit"]
    assert meta["models"]["groq-gpt-oss-20b"]["versions_seen"] == ["m-1"]
    answers = load_answers(run_dir)
    assert len(answers) == summary["planned_calls"] == 12
    first = answers[0]
    assert first["prompt"] and first["answer"] == "It is Rs 1,00,000."
    assert first["input_tokens"] == 5 and first["status"] == "ok"
    r3 = next(a for a in answers if a["condition"] == "R3")
    assert r3["chunk_ids"] and r3["context_has_old"] is not None

    # a second identical run is served entirely from the cache
    again = run_experiment(cfg, box, client, retriever, dry_run=True)
    assert again["uncached_calls"] == 0

    items = {i.item_id: i for i in load_items(box, "dev")}
    scores = score_run(answers, items)
    assert {s.method for s in scores} <= {"matcher", "none"}
    rows = summarise(scores)
    assert sum(r["n"] for r in rows) == 12


def test_plan_orders_models_items_languages_conditions(root: Path) -> None:
    cfg = _cfg(models=["a", "b"], item_limit=2, languages=["en", "gu"], conditions=["R2", "X"])
    items = select_items(cfg, root, final=False)
    steps = list(plan(cfg, items))
    assert len(steps) == 2 * 2 * (1 + 2)  # per item: en has R2 only; gu has R2 and X
    assert [s[0] for s in steps[:6]] == ["a"] * 6


def test_label_sheet_hides_automatic_labels_and_reports_kappa(
    root: Path, tmp_path: Path, retriever: Retriever
) -> None:
    box = _sandbox(root, tmp_path)
    cfg = _cfg(conditions=["R3"], languages=["en", "hi", "gu"], item_limit=4)
    summary = run_experiment(cfg, box, _client(tmp_path, "The figure is 1,25,000."), retriever)
    answers = load_answers(box / "runs" / summary["run_id"])
    items = {i.item_id: i for i in load_items(box, "dev")}
    scores = score_run(answers, items)
    assert len(pick_sample(scores, 5, 0.5, seed=1)) == 5

    sheet = tmp_path / "sheet.csv"
    n = export_label_sheet(scores, answers, items, sheet, size=6)
    text = sheet.read_text(encoding="utf-8-sig")
    assert n == 6 and "auto_label" not in text and "method" not in text

    key = json.loads(sheet.with_suffix(".key.json").read_text(encoding="utf-8"))
    # label every row the way the automatic scorer did: perfect agreement
    with sheet.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    for row, k in zip(rows, key, strict=True):
        row["human_label"] = k["auto_label"]
    with sheet.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    report = agreement_report(sheet)
    assert report["labelled"] == 6 and report["all"]["accuracy"] == 1.0
    assert report["disagreements"] == []
