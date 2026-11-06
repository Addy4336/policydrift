"""Wait for the final test runs, score them, write the manifest and build paper/test.

Run from the repository root:  uv run --no-sync python scripts/finish_final.py
Safe to rerun: runs that are already scored are skipped, and answers come from the cache.
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIGS = sorted((ROOT / "configs" / "final").glob("*.yaml"))
# gpt-oss-20b was dropped from the final run (preregistration deviation log, 2026-11-06).
CONFIGS = [c for c in CONFIGS if "gpt-oss" not in c.name]


def newest_complete(name: str) -> Path | None:
    """Latest run of this config that finished (run.json is written at the end)."""
    runs = sorted((ROOT / "runs").glob(f"{name}-2*"))
    done = [r for r in runs if (r / "run.json").exists()]
    return done[-1] if done else None


def main() -> int:
    while True:
        missing = [c.stem for c in CONFIGS if newest_complete(c.stem) is None]
        if not missing:
            break
        print(f"waiting for {len(missing)} run(s): {', '.join(missing[:3])} ...", flush=True)
        time.sleep(120)
    runs = [newest_complete(c.stem) for c in CONFIGS]
    for run in runs:
        assert run is not None
        if not (run / "scores.jsonl").exists():
            print(f"scoring {run.name}", flush=True)
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
    print("done: see paper/test/results.md", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
