"""Load scored runs into flat rows. A run directory needs answers.jsonl, scores.jsonl, run.json."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class Row:
    run: str
    model: str
    language: str
    condition: str
    mitigation: str
    item_id: str
    fact_id: str
    label: str
    calls: int
    tokens: int
    latency_s: float | None
    cached: bool | None
    has_current: bool | None

    @property
    def key(self) -> tuple[str, str, str]:
        return (self.model, self.item_id, self.language)

    @property
    def answered(self) -> bool:
        return self.label not in {"missing", "unresolved"}


def load_manifest(path: Path) -> tuple[str, list[Path]]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return str(data["split"]), [Path(p) for p in data["runs"]]


def load_run(run_dir: Path) -> list[Row]:
    meta_path = run_dir / "run.json"
    if meta_path.exists():
        meta: dict[str, Any] = json.loads(meta_path.read_text(encoding="utf-8"))
    else:  # a dev run that was stopped before it wrote run.json: use the config it started from
        cfg_path = Path("configs/experiments") / f"{run_dir.name.rsplit('-', 1)[0]}.yaml"
        meta = {"config": yaml.safe_load(cfg_path.read_text(encoding="utf-8"))}
        if meta["config"].get("split") != "dev":
            raise ValueError(f"{run_dir} has no run.json and is not a dev run")
    mitigation = str(meta["config"].get("mitigation", "none"))

    def lines(name: str) -> list[dict[str, Any]]:
        with (run_dir / name).open(encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]

    rows = []
    for a, s in zip(lines("answers.jsonl"), lines("scores.jsonl"), strict=True):
        if (a["item_id"], a["language"], a["model"], a["condition"]) != (
            s["item_id"],
            s["language"],
            s["model"],
            s["condition"],
        ):
            raise ValueError(f"{run_dir}: answers and scores are not aligned")
        rows.append(
            Row(
                run=run_dir.name,
                model=a["model"],
                language=a["language"],
                condition=a["condition"],
                mitigation=mitigation,
                item_id=a["item_id"],
                fact_id=a["fact_id"],
                label=s["label"],
                calls=int(a.get("calls") or 1),
                tokens=int(a.get("input_tokens") or 0) + int(a.get("output_tokens") or 0),
                latency_s=a.get("latency_s"),
                cached=a.get("cached"),
                has_current=a.get("context_has_current"),
            )
        )
    return rows


def load_all(run_dirs: list[Path]) -> list[Row]:
    """All rows. A later run replaces an earlier one for the same (mitigation, condition, model),
    so a gap-filling run can be listed after the run it completes."""
    by_ident: dict[tuple[str, str, str], list[Row]] = {}
    for d in run_dirs:
        fresh: dict[tuple[str, str, str], list[Row]] = {}
        for r in load_run(d):
            fresh.setdefault((r.mitigation, r.condition, r.model), []).append(r)
        by_ident.update(fresh)
    return [r for rows in by_ident.values() for r in rows]
