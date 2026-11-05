"""Statistics and report generation."""

from __future__ import annotations

import json
import math
from pathlib import Path

from typer.testing import CliRunner

from policydrift.analysis.data import load_all
from policydrift.analysis.stats import (
    cluster_bootstrap_ci,
    holm,
    mcnemar_one_sided,
    mcnemar_two_sided,
)
from policydrift.cli import app


def test_exact_mcnemar() -> None:
    assert mcnemar_one_sided(0, 0) == 1.0
    assert math.isclose(mcnemar_one_sided(5, 0), 1 / 32)
    assert math.isclose(mcnemar_one_sided(0, 5), 1.0)
    assert math.isclose(mcnemar_two_sided(5, 0), 2 / 32)
    assert mcnemar_two_sided(3, 3) == 1.0


def test_holm_is_monotone_and_capped() -> None:
    adj = holm([0.01, 0.04, 0.03])
    assert adj == [0.03, 0.06, 0.06]
    assert holm([0.9, 0.8]) == [1.0, 1.0]


def test_cluster_bootstrap_keeps_clusters_together() -> None:
    # Two clusters, one all 1s and one all 0s: every resample mean lies in {0, 0.5, 1}.
    point, lo, hi = cluster_bootstrap_ci(
        [1.0, 1.0, 0.0, 0.0], ["a", "a", "b", "b"], resamples=500, seed=1
    )
    assert point == 0.5 and lo == 0.0 and hi == 1.0


def _write_run(root: Path, name: str, mitigation: str, condition: str, labels: list[str]) -> Path:
    d = root / name
    d.mkdir()
    (d / "run.json").write_text(
        json.dumps({"config": {"mitigation": mitigation}, "final": False}), encoding="utf-8"
    )
    answers, scores = [], []
    for i, label in enumerate(labels):
        base = {
            "item_id": f"f{i % 4}/direct",
            "language": ["en", "hi", "gu"][i % 3],
            "model": "m",
            "condition": condition,
        }
        answers.append(
            {
                **base,
                "fact_id": f"f{i % 4}",
                "calls": 2 if mitigation == "M-b" else 1,
                "input_tokens": 100,
                "output_tokens": 20,
                "latency_s": 1.0,
                "cached": False,
                "context_has_current": True,
            }
        )
        scores.append({**base, "label": label})
    (d / "answers.jsonl").write_text("\n".join(map(json.dumps, answers)) + "\n", encoding="utf-8")
    (d / "scores.jsonl").write_text("\n".join(map(json.dumps, scores)) + "\n", encoding="utf-8")
    return d


def test_load_all_later_run_replaces_earlier(tmp_path: Path) -> None:
    a = _write_run(tmp_path, "a", "none", "R1", ["missing"] * 4)
    b = _write_run(tmp_path, "b", "none", "R1", ["current"] * 4)
    rows = load_all([a, b])
    assert {r.run for r in rows} == {"b"} and len(rows) == 4


def test_paper_command_builds_tables(tmp_path: Path) -> None:
    runs = [
        _write_run(tmp_path, "base", "none", "R3", ["outdated", "current"] * 6),
        _write_run(tmp_path, "mb", "M-b", "R3", ["current", "current"] * 6),
    ]
    manifest = tmp_path / "runs.yaml"
    manifest.write_text(
        "split: dev\nruns:\n" + "".join(f"  - {r.as_posix()}\n" for r in runs), encoding="utf-8"
    )
    out = tmp_path / "out"
    result = CliRunner().invoke(
        app, ["paper", "--manifest", str(manifest), "--out", str(out), "--root", str(Path("/"))]
    )
    assert result.exit_code == 0, result.output
    h3 = (out / "tables" / "h3_r3.md").read_text(encoding="utf-8")
    assert "M-b" in h3 and "6 / 0" in h3
    assert (out / "figures" / "fig_outdated_by_condition.png").exists()


def test_test_manifest_needs_final(tmp_path: Path) -> None:
    manifest = tmp_path / "runs.yaml"
    manifest.write_text("split: test\nruns: []\n", encoding="utf-8")
    result = CliRunner().invoke(
        app, ["paper", "--manifest", str(manifest), "--root", str(Path("/"))]
    )
    assert result.exit_code != 0
