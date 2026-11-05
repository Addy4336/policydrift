"""Human labelling sheet and agreement statistics for the scorer (matcher + judge).

The sheet hides the automatic labels so the human is not anchored by them. They are kept in a
separate key file and joined back on import.
"""

from __future__ import annotations

import csv
import json
import random
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from policydrift.bench.split import BenchItem
from policydrift.scoring.pipeline import ScoreRecord, describe_value

HUMAN_LABELS = ("current", "outdated", "other", "refusal")
COLUMNS = [
    "row_id",
    "language",
    "question",
    "old_value",
    "current_value",
    "answer",
    "human_label",
    "note",
]


def cohen_kappa(a: Sequence[str], b: Sequence[str]) -> float:
    """Cohen's kappa for two raters over the same items (1.0 = perfect, 0 = chance level)."""
    if len(a) != len(b) or not a:
        raise ValueError("need two equally long, non-empty label lists")
    n = len(a)
    observed = sum(x == y for x, y in zip(a, b, strict=True)) / n
    ca, cb = Counter(a), Counter(b)
    expected = sum(ca[k] * cb[k] for k in set(ca) | set(cb)) / (n * n)
    return 1.0 if expected == 1 else (observed - expected) / (1 - expected)


def pick_sample(
    scores: Sequence[ScoreRecord], size: int, judge_share: float, seed: int
) -> list[int]:
    """Indices of a sample that favours judge-decided answers and spreads over languages."""
    rng = random.Random(seed)
    usable = [i for i, s in enumerate(scores) if s.label not in {"missing"}]
    judged = [i for i in usable if scores[i].method in {"judge", "none"}]
    matched = [i for i in usable if scores[i].method == "matcher"]

    def spread(pool: list[int], k: int) -> list[int]:
        by_lang: dict[str, list[int]] = {}
        for i in pool:
            by_lang.setdefault(scores[i].language, []).append(i)
        for items in by_lang.values():
            rng.shuffle(items)
        picked: list[int] = []
        while len(picked) < k and any(by_lang.values()):
            for lang in sorted(by_lang):
                if by_lang[lang] and len(picked) < k:
                    picked.append(by_lang[lang].pop())
        return picked

    want_judged = min(len(judged), round(size * judge_share))
    chosen = spread(judged, want_judged)
    chosen += spread(matched, size - len(chosen))
    rng.shuffle(chosen)
    return chosen


def export_label_sheet(
    scores: Sequence[ScoreRecord],
    answers: Sequence[Mapping[str, Any]],
    items: Mapping[str, BenchItem],
    out: Path,
    *,
    size: int = 45,
    judge_share: float = 0.67,
    seed: int = 7,
) -> int:
    chosen = pick_sample(scores, size, judge_share, seed)
    key = []
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        for n, i in enumerate(chosen, start=1):
            s, a = scores[i], answers[i]
            item = items[s.item_id]
            writer.writerow(
                {
                    "row_id": n,
                    "language": s.language,
                    "question": item.questions[s.language],
                    "old_value": describe_value(item.kind, item.old.value),
                    "current_value": describe_value(item.kind, item.current.value),
                    "answer": a["answer"],
                    "human_label": "",
                    "note": "",
                }
            )
            key.append(
                {"row_id": n, "auto_label": s.label, "method": s.method, "item_id": s.item_id}
            )
    out.with_suffix(".key.json").write_text(
        json.dumps(key, indent=1) + "\n", encoding="utf-8", newline="\n"
    )
    return len(chosen)


STRATA_SHARE = {"outdated": 0.40, "other": 0.20, "refusal": 0.15, "current": 0.25}


def pick_stratified(
    pool: Sequence[tuple[str, ScoreRecord, Mapping[str, Any]]],
    size: int,
    seed: int,
    exclude: set[tuple[str, str, str]] | None = None,
) -> list[int]:
    """Indices into ``pool`` over-sampling rare outcomes, without duplicate answers.

    Answers are unique on (item, language, answer text) and a pair already in ``exclude`` (an
    earlier labelled sheet) is skipped. Quotas follow ``STRATA_SHARE`` by automatic label; a stratum
    that runs short hands its quota to the others. Languages are spread within each stratum.
    """
    rng = random.Random(seed)
    seen = set(exclude or ())
    by_label: dict[str, dict[str, list[int]]] = {}
    order = list(range(len(pool)))
    rng.shuffle(order)
    for i in order:
        _, rec, ans = pool[i]
        if rec.label not in STRATA_SHARE:
            continue
        key = (rec.item_id, rec.language, " ".join(str(ans["answer"]).split()))
        if key in seen:
            continue
        seen.add(key)
        by_label.setdefault(rec.label, {}).setdefault(rec.language, []).append(i)

    def take(label: str, k: int) -> list[int]:
        langs = by_label.get(label, {})
        out: list[int] = []
        while len(out) < k and any(langs.values()):
            for lang in sorted(langs):
                if langs[lang] and len(out) < k:
                    out.append(langs[lang].pop())
        return out

    chosen: list[int] = []
    for label, share in STRATA_SHARE.items():
        chosen += take(label, round(size * share))
    for label in STRATA_SHARE:  # hand the shortfall to whatever is left
        if len(chosen) >= size:
            break
        chosen += take(label, size - len(chosen))
    rng.shuffle(chosen)
    return chosen[:size]


def export_pooled_label_sheet(
    pool: Sequence[tuple[str, ScoreRecord, Mapping[str, Any]]],
    items: Mapping[str, BenchItem],
    out: Path,
    *,
    size: int = 60,
    seed: int = 11,
    exclude: set[tuple[str, str, str]] | None = None,
) -> int:
    """Labelling sheet over several runs, stratified by automatic label (labels hidden)."""
    chosen = pick_stratified(pool, size, seed, exclude)
    out.parent.mkdir(parents=True, exist_ok=True)
    key = []
    with out.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        for n, i in enumerate(chosen, start=1):
            run, rec, ans = pool[i]
            item = items[rec.item_id]
            writer.writerow(
                {
                    "row_id": n,
                    "language": rec.language,
                    "question": item.questions[rec.language],
                    "old_value": describe_value(item.kind, item.old.value),
                    "current_value": describe_value(item.kind, item.current.value),
                    "answer": ans["answer"],
                    "human_label": "",
                    "note": "",
                }
            )
            key.append(
                {
                    "row_id": n,
                    "auto_label": rec.label,
                    "method": rec.method,
                    "item_id": rec.item_id,
                    "run": run,
                    "model": rec.model,
                    "condition": rec.condition,
                }
            )
    out.with_suffix(".key.json").write_text(
        json.dumps(key, indent=1) + "\n", encoding="utf-8", newline="\n"
    )
    return len(chosen)


def read_human_labels(sheet: Path) -> dict[int, str]:
    labels: dict[int, str] = {}
    with sheet.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            value = (row.get("human_label") or "").strip().lower()
            if not value:
                continue
            if value not in HUMAN_LABELS:
                raise ValueError(f"row {row['row_id']}: label {value!r} not in {HUMAN_LABELS}")
            labels[int(row["row_id"])] = value
    return labels


def agreement_report(sheet: Path) -> dict[str, Any]:
    """Cohen's kappa of the automatic labels against the human labels, by deciding method."""
    key = json.loads(sheet.with_suffix(".key.json").read_text(encoding="utf-8"))
    human = read_human_labels(sheet)
    rows = [(k, human[k["row_id"]]) for k in key if k["row_id"] in human]
    report: dict[str, Any] = {"labelled": len(rows), "of": len(key)}
    for name, subset in (
        ("all", rows),
        ("judge", [r for r in rows if r[0]["method"] == "judge"]),
        ("matcher", [r for r in rows if r[0]["method"] == "matcher"]),
    ):
        if not subset:
            report[name] = None
            continue
        auto = [r[0]["auto_label"] for r in subset]
        hum = [r[1] for r in subset]
        report[name] = {
            "n": len(subset),
            "accuracy": round(sum(a == h for a, h in zip(auto, hum, strict=True)) / len(subset), 3),
            "kappa": round(cohen_kappa(auto, hum), 3),
        }
    report["disagreements"] = [
        {"row_id": k["row_id"], "auto": k["auto_label"], "human": h, "method": k["method"]}
        for k, h in rows
        if k["auto_label"] != h
    ]
    return report
