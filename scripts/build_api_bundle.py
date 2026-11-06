"""Build a slim folder that Vercel can deploy as a Python (FastAPI) function.

    uv run --no-sync python scripts/build_api_bundle.py      # writes deploy/vercel-api/
    cd deploy/vercel-api && npx vercel deploy --prod

The bundle holds the policydrift package, the FastAPI app, the chunks, the version registry, the
dev split (for example questions) and the dev results. It never contains the test split, raw
sources, runs or caches. It uses the lexical retriever, because a serverless function cannot load
the e5-base embedding model; the research always uses e5-base.
"""

from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "deploy" / "vercel-api"

FILES = [
    "configs/models.yaml",
    "data/schemes.yaml",
    "data/processed/chunks.jsonl",
    "data/benchmark/dev/items.jsonl",
    "paper/dev/results.md",
]
REQUIREMENTS = """\
fastapi>=0.115
pydantic>=2.9
pyyaml>=6.0
httpx>=0.28
numpy>=2.0
psycopg[binary]>=3.2
"""
INDEX = '''\
"""Vercel entry point: the PolicyDrift demo API with the lexical retriever."""

import os

os.environ.setdefault("POLICYDRIFT_RETRIEVER", "lexical")
os.environ.setdefault("POLICYDRIFT_CACHE_DIR", "/tmp/policydrift")
os.environ.setdefault("POLICYDRIFT_WARMUP", "0")

from webapi.main import app  # noqa: E402

__all__ = ["app"]
'''


def main() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    shutil.copytree(
        ROOT / "src" / "policydrift",
        OUT / "policydrift",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
    (OUT / "webapi").mkdir()
    (OUT / "webapi" / "__init__.py").write_text("", encoding="utf-8")
    shutil.copyfile(ROOT / "api" / "main.py", OUT / "webapi" / "main.py")
    for rel in FILES:
        target = OUT / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / rel, target)
    (OUT / "requirements.txt").write_text(REQUIREMENTS, encoding="utf-8", newline="\n")
    (OUT / "index.py").write_text(INDEX, encoding="utf-8", newline="\n")
    (OUT / ".python-version").write_text("3.12\n", encoding="utf-8", newline="\n")
    (OUT / ".vercelignore").write_text("__pycache__\n", encoding="utf-8", newline="\n")
    size = sum(p.stat().st_size for p in OUT.rglob("*") if p.is_file())
    print(f"wrote {OUT} ({size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
