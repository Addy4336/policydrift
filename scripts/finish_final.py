"""Drive the final test run to the end, score it and build paper/test.

Run from the repository root:  uv run --no-sync python scripts/finish_final.py

It runs each final config once per model in order (the two models in parallel, since the rate
limits are per model), reruns a config while any answer is missing (the cache holds every answer
received, so a rerun only asks for what failed), waits out free-tier quota errors, then scores the
runs, writes paper/runs.test.yaml and builds paper/test/. Safe to stop and start again.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODELS = ["gemini-flash-lite", "gemini-35-flash-lite"]  # gpt-oss-20b dropped (deviation log)
ORDER = [
    "test-baseline-{m}",
    "test-m-a1-{m}-r3",
    "test-m-a2-{m}-r3",
    "test-m-b-{m}-r3",
    "test-m-c-{m}",
]
# Gemini free-tier daily quotas reset at midnight Pacific time (08:00 UTC in winter).
NOT_BEFORE_UTC = (8, 5)
RETRY_WAIT_S = 1800
MAX_ATTEMPTS = 12


def log(msg: str) -> None:
    print(f"{datetime.now(UTC):%H:%M:%S}Z {msg}", flush=True)


def newest_run(name: str) -> Path | None:
    runs = sorted(r for r in (ROOT / "runs").glob(f"{name}-2*") if (r / "run.json").exists())
    return runs[-1] if runs else None


def missing_answers(run: Path) -> int:
    with (run / "answers.jsonl").open(encoding="utf-8") as f:
        return sum(1 for line in f if line.strip() and json.loads(line)["status"] != "ok")


def run_config(name: str) -> None:
    for attempt in range(1, MAX_ATTEMPTS + 1):
        run = newest_run(name)
        if run is not None and missing_answers(run) == 0:
            log(f"{name}: complete ({run.name})")
            return
        log(f"{name}: attempt {attempt}")
        subprocess.run(
            [
                "uv",
                "run",
                "--no-sync",
                "policydrift",
                "run",
                f"configs/final/{name}.yaml",
                "--final",
            ],
            cwd=ROOT,
            check=False,
        )
        run = newest_run(name)
        left = missing_answers(run) if run is not None else -1
        if left == 0:
            log(f"{name}: complete ({run.name if run else '?'})")
            return
        log(f"{name}: {left} answers missing (quota?); waiting {RETRY_WAIT_S // 60} min")
        time.sleep(RETRY_WAIT_S)
    log(f"{name}: giving up after {MAX_ATTEMPTS} attempts; the run stays incomplete")


def chain(model: str) -> None:
    for pattern in ORDER:
        run_config(pattern.format(m=model))


def main() -> int:
    now = datetime.now(UTC)
    start = now.replace(hour=NOT_BEFORE_UTC[0], minute=NOT_BEFORE_UTC[1], second=0, microsecond=0)
    if now < start:
        wait = (start - now).total_seconds()
        log(f"waiting {wait / 60:.0f} min for the Gemini daily quota to reset")
        time.sleep(wait)
    with ThreadPoolExecutor(max_workers=len(MODELS)) as pool:
        list(pool.map(chain, MODELS))
    names = [p.format(m=m) for m in MODELS for p in ORDER]
    runs = [newest_run(n) for n in names]
    if any(r is None or missing_answers(r) for r in runs):
        log("some runs are incomplete; rerun this script later to finish them")
        return 1
    for run in runs:
        assert run is not None
        if not (run / "scores.jsonl").exists():
            log(f"scoring {run.name}")
            subprocess.run(
                ["uv", "run", "--no-sync", "policydrift", "score", str(run)], cwd=ROOT, check=True
            )
    manifest = ROOT / "paper" / "runs.test.yaml"
    lines = ["# Scored final test runs behind paper/test.", "split: test", "runs:"]
    lines += [f"  - runs/{r.name}" for r in runs if r is not None]
    manifest.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    subprocess.run(
        ["uv", "run", "--no-sync", "policydrift", "paper", "--manifest", str(manifest), "--final"],
        cwd=ROOT,
        check=True,
    )
    log("done: see paper/test/results.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
