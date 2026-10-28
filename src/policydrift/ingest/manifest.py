"""Raw-source manifest: what was captured, from where, when, and its SHA-256."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict

Language = Literal["en", "hi", "gu"]


class RawSource(BaseModel):
    """One captured official document, as recorded in ``data/raw/manifest.jsonl``."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    path: str
    scheme: str
    version: str
    language: Language
    source_type: Literal["pib_release"]
    publisher: str
    prid: str
    url: str
    retrieved_at: AwareDatetime
    capture_method: str
    normalization: str
    sha256: str
    chars: int
    notes: str | None = None


def load_manifest(path: Path) -> list[RawSource]:
    with path.open(encoding="utf-8") as f:
        return [RawSource.model_validate_json(line) for line in f if line.strip()]


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_sources(sources: list[RawSource], raw_dir: Path) -> list[str]:
    """Return one message per problem; an empty list means every file exists and matches."""
    problems: list[str] = []
    seen: set[str] = set()
    for source in sources:
        if source.path in seen:
            problems.append(f"duplicate manifest entry: {source.path}")
        seen.add(source.path)
        file = raw_dir / source.path
        if not file.is_file():
            problems.append(f"missing file: {source.path}")
        elif sha256_file(file) != source.sha256:
            problems.append(f"sha256 mismatch: {source.path}")
    return problems
