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
llm_app = typer.Typer(help="Cached, rate-limited LLM client.", no_args_is_help=True)
app.add_typer(llm_app, name="llm")

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


index_app = typer.Typer(help="Embeddings and retrieval.", no_args_is_help=True)
app.add_typer(index_app, name="index")


@index_app.command("probe")
def probe(
    model: Annotated[str, typer.Option(help="Embedding model key: e5-base or bge-m3.")] = "e5-base",
    root: RootOption = Path("."),
) -> None:
    """Embed the chunk store (cached) and report retrieval quality on the dev probes."""
    import time

    from policydrift.retrieval.embed import MODELS, EmbeddingCache, SentenceTransformerEmbedder
    from policydrift.retrieval.probes import evaluate, gold_ids, load_probes, summarise
    from policydrift.retrieval.search import Retriever, load_chunks

    if model not in MODELS:
        raise typer.BadParameter(f"unknown model '{model}'; choose from {sorted(MODELS)}")
    chunks = load_chunks(root / "data" / "processed" / "chunks.jsonl")
    probes = load_probes(root / "data" / "probes" / "retrieval_probes.jsonl")
    empty = [p.id for p in probes if not gold_ids(p, chunks)]
    if empty:
        typer.echo(f"probes with no gold chunk: {empty}", err=True)
        raise typer.Exit(code=1)

    started = time.perf_counter()
    embedder = SentenceTransformerEmbedder(MODELS[model])
    cache = EmbeddingCache(root / ".cache" / "embeddings", MODELS[model])
    retriever = Retriever(chunks, embedder, cache)
    typer.echo(
        f"{model}: embedded {retriever.computed} new passages "
        f"({len(chunks)} total) in {time.perf_counter() - started:.0f}s"
    )
    results = evaluate(retriever, probes)
    for name, row in summarise(results).items():
        typer.echo(
            f"  {name:6s} n={int(row['n']):2d}"
            f"  R@1={row['recall@1']:.2f}  R@5={row['recall@5']:.2f}"
            f"  R@10={row['recall@10']:.2f}  MRR={row['mrr']:.2f}"
            f"  scheme@1={row['top1_right_scheme']:.2f}"
            f"  wrong-version@1={row['top1_wrong_version']:.2f}"
        )
    for r in results:
        if r.first_gold_rank is None or r.first_gold_rank > 5:
            typer.echo(f"  miss: {r.probe.id} (first gold rank {r.first_gold_rank})")


db_app = typer.Typer(help="Supabase demo database.", no_args_is_help=True)
app.add_typer(db_app, name="db")


@db_app.command("migrate")
def db_migrate(root: RootOption = Path(".")) -> None:
    """Apply any unapplied SQL files in supabase/migrations to the database in .env."""
    from policydrift.db import apply_migrations, connect

    with connect(root) as conn:
        applied = apply_migrations(conn, root / "supabase" / "migrations")
    typer.echo(f"Applied: {', '.join(applied)}" if applied else "Nothing to apply; up to date.")


def _local_retriever(root: Path):  # type: ignore[no-untyped-def]
    from policydrift.ingest.registry import load_registry
    from policydrift.retrieval.embed import (
        DEFAULT_MODEL,
        MODELS,
        EmbeddingCache,
        SentenceTransformerEmbedder,
    )
    from policydrift.retrieval.search import Retriever, load_chunks

    model = MODELS[DEFAULT_MODEL]
    chunks = load_chunks(root / "data" / "processed" / "chunks.jsonl")
    registry = load_registry(root / "data" / "schemes.yaml")
    cache = EmbeddingCache(root / ".cache" / "embeddings", model)
    return Retriever(chunks, SentenceTransformerEmbedder(model), cache, registry)


@db_app.command("load")
def db_load(root: RootOption = Path(".")) -> None:
    """Upload the chunks and their cached embeddings (idempotent upsert)."""
    from policydrift.db import connect, upload_chunks
    from policydrift.retrieval.embed import DEFAULT_MODEL

    retriever = _local_retriever(root)
    if retriever.computed:
        typer.echo(f"note: {retriever.computed} passages were not cached and had to be embedded")
    with connect(root) as conn:
        n = upload_chunks(conn, retriever.chunks, retriever.matrix.tolist(), DEFAULT_MODEL)
    typer.echo(f"Uploaded {n} chunks.")


@db_app.command("check")
def db_check(root: RootOption = Path("."), k: int = 5) -> None:
    """Compare Supabase match_chunks with local search on every dev probe."""
    from policydrift.db import connect, vector_literal
    from policydrift.retrieval.probes import load_probes
    from policydrift.retrieval.search import Filters

    retriever = _local_retriever(root)
    probes = load_probes(root / "data" / "probes" / "retrieval_probes.jsonl")
    mismatches = 0
    with connect(root) as conn, conn.cursor() as cur:
        cur.execute("select count(*) from public.chunks")
        row = cur.fetchone()
        typer.echo(f"rows in database: {row[0] if row else 0} (local: {len(retriever.chunks)})")
        for p in probes:
            lang = p.doc_lang if p.cross_lingual else None
            local = [h.chunk.chunk_id for h in retriever.search(p.query, k, Filters(language=lang))]
            qvec, _ = retriever.cache.get_or_compute(retriever.embedder, "query", [p.query])
            cur.execute(
                "select chunk_id from public.match_chunks(%s::vector, %s, null, %s)",
                (vector_literal(qvec[0]), k, lang),
            )
            remote = [r[0] for r in cur.fetchall()]
            if local != remote:
                mismatches += 1
                typer.echo(f"  differs: {p.id}\n    local:  {local}\n    remote: {remote}")
    typer.echo(f"{len(probes) - mismatches}/{len(probes)} probes return identical top-{k}.")
    if mismatches:
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()


@llm_app.command("check")
def llm_check(root: RootOption = Path(".")) -> None:
    """Send one tiny prompt to each provider that has a key (cached, so repeat runs are free)."""
    from policydrift.llm import LLMError, LLMRequest, client_from_root
    from policydrift.llm.client import KEY_VARS, load_models

    models = load_models(root / "configs" / "models.yaml")["models"]
    assert isinstance(models, dict)
    client = client_from_root(root)
    failed = False
    for name, spec in models.items():
        request = LLMRequest(
            provider=spec["provider"],
            model=spec["model"],
            prompt="Reply with the single word: ready",
            max_tokens=512,
            purpose="check",
        )
        try:
            reply = client.complete(request)
        except LLMError as exc:
            failed = True
            typer.echo(f"{name}: FAILED ({exc}); key variable is {KEY_VARS[spec['provider']]}")
            continue
        origin = "cache" if reply.cached else f"{reply.latency_s}s"
        typer.echo(
            f"{name}: {reply.text.strip()!r} ({origin}, version {reply.model_version}, "
            f"tokens {reply.input_tokens}/{reply.output_tokens})"
        )
    if failed:
        raise typer.Exit(code=1)
