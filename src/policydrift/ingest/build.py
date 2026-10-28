"""Build ``data/processed/chunks.jsonl``: chunks carrying full version metadata."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from policydrift.ingest.chunking import chunk_spans
from policydrift.ingest.manifest import Language, load_manifest, verify_sources
from policydrift.ingest.pib import clean_text, parse_pib
from policydrift.ingest.registry import load_registry, validate_registry

DEFAULT_MAX_CHARS = 800


class Chunk(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    chunk_id: str
    scheme: str
    version: str
    effective_from: date | None
    effective_to: date | None
    announced_on: date | None
    language: Language
    source_url: str
    source_path: str
    source_sha256: str
    source_prid: str
    ministry: str
    title: str
    posted_on: date
    chunk_index: int
    raw_start: int  # [raw_start, raw_end) offsets into the captured source file
    raw_end: int
    text: str


class IngestError(RuntimeError):
    pass


def build_chunks(root: Path, max_chars: int = DEFAULT_MAX_CHARS) -> Iterator[Chunk]:
    """Verify every source and the registry, then yield chunks in a deterministic order."""
    raw_dir = root / "data" / "raw"
    sources = load_manifest(raw_dir / "manifest.jsonl")
    registry = load_registry(root / "data" / "schemes.yaml")

    problems = verify_sources(sources, raw_dir) + validate_registry(registry)
    for s in sources:
        if s.scheme not in registry:
            problems.append(f"{s.path}: scheme '{s.scheme}' is not in schemes.yaml")
        elif s.version not in {v.id for v in registry[s.scheme].versions}:
            problems.append(f"{s.path}: version '{s.version}' is not in schemes.yaml")
    if problems:
        raise IngestError("\n".join(problems))

    for source in sorted(sources, key=lambda s: (s.scheme, s.version, s.language, s.prid)):
        version = registry[source.scheme].version(source.version)
        raw = (raw_dir / source.path).read_text(encoding="utf-8")
        release = parse_pib(raw)
        if release.prid != source.prid:
            raise IngestError(f"{source.path}: Release ID {release.prid} != manifest {source.prid}")
        spans = chunk_spans(raw, release.body_start, release.body_end, max_chars)
        for index, (start, end) in enumerate(spans):
            yield Chunk(
                chunk_id=f"{source.scheme}:{source.version}:{source.language}:{source.prid}:{index:03d}",
                scheme=source.scheme,
                version=source.version,
                effective_from=version.effective_from,
                effective_to=version.effective_to,
                announced_on=version.announced_on,
                language=source.language,
                source_url=source.url,
                source_path=source.path,
                source_sha256=source.sha256,
                source_prid=source.prid,
                ministry=release.ministry,
                title=release.title,
                posted_on=release.posted_on,
                chunk_index=index,
                raw_start=start,
                raw_end=end,
                text=clean_text(raw[start:end]),
            )


def write_jsonl(chunks: Iterator[Chunk], path: Path) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for chunk in chunks:
            f.write(chunk.model_dump_json() + "\n")
            count += 1
    return count
