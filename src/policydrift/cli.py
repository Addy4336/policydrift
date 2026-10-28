"""Command-line entry point: ``uv run policydrift <command>``."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Annotated

import typer

from policydrift.ingest.build import DEFAULT_MAX_CHARS, IngestError, build_chunks, write_jsonl
from policydrift.ingest.manifest import load_manifest, verify_sources
from policydrift.ingest.registry import load_registry, validate_registry

app = typer.Typer(help="PolicyDrift research pipeline.", no_args_is_help=True)
ingest_app = typer.Typer(help="Build the versioned document store.", no_args_is_help=True)
app.add_typer(ingest_app, name="ingest")

RootOption = Annotated[Path, typer.Option(help="Repository root.")]


@ingest_app.command("verify")
def verify(root: RootOption = Path(".")) -> None:
    """Check every captured source against its manifest hash, and the version registry."""
    raw_dir = root / "data" / "raw"
    sources = load_manifest(raw_dir / "manifest.jsonl")
    problems = verify_sources(sources, raw_dir)
    problems += validate_registry(load_registry(root / "data" / "schemes.yaml"))
    for problem in problems:
        typer.echo(problem, err=True)
    if problems:
        raise typer.Exit(code=1)
    typer.echo(f"OK: {len(sources)} sources match their hashes; version registry is consistent.")


@ingest_app.command("chunk")
def chunk(
    root: RootOption = Path("."),
    max_chars: Annotated[int, typer.Option(help="Maximum characters per chunk.")] = (
        DEFAULT_MAX_CHARS
    ),
) -> None:
    """Write data/processed/chunks.jsonl from the verified sources."""
    out = root / "data" / "processed" / "chunks.jsonl"
    try:
        chunks = list(build_chunks(root, max_chars=max_chars))
    except IngestError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(code=1) from e
    count = write_jsonl(iter(chunks), out)
    by_lang = Counter(c.language for c in chunks)
    typer.echo(
        f"Wrote {count} chunks to {out} "
        f"(en={by_lang['en']}, hi={by_lang['hi']}, gu={by_lang['gu']})."
    )


if __name__ == "__main__":
    app()
