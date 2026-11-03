"""Command-line entry point: ``uv run policydrift <command>``."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Annotated, Any

import typer

from policydrift.ingest.build import DEFAULT_MAX_CHARS, IngestError, build_chunks, write_jsonl
from policydrift.ingest.manifest import load_manifest, verify_sources
from policydrift.ingest.registry import load_registry, validate_registry

app = typer.Typer(help="PolicyDrift research pipeline.", no_args_is_help=True)
ingest_app = typer.Typer(help="Build the versioned document store.", no_args_is_help=True)
app.add_typer(ingest_app, name="ingest")
llm_app = typer.Typer(help="Cached, rate-limited LLM client.", no_args_is_help=True)
app.add_typer(llm_app, name="llm")
bench_app = typer.Typer(help="Build the benchmark.", no_args_is_help=True)
app.add_typer(bench_app, name="bench")

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
    from policydrift.retrieval.factory import local_retriever

    return local_retriever(root)


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


@bench_app.command("draft")
def bench_draft(
    root: RootOption = Path("."),
    model: Annotated[str, typer.Option(help="Key in configs/models.yaml.")] = "groq-gpt-oss",
    limit: Annotated[int, typer.Option(help="Only the first N facts (0 = all).")] = 0,
    fact: Annotated[list[str] | None, typer.Option(help="Only this fact id (repeatable).")] = None,
) -> None:
    """Draft en/hi/gu question wording for every fact x style (unverified; see milestone 2d).

    With --fact, only those facts are redrafted and replace their earlier drafts in the file.
    """
    from policydrift.bench.drafts import draft_all, load_drafts, write_drafts
    from policydrift.bench.facts import load_facts
    from policydrift.llm import client_from_root
    from policydrift.llm.client import load_models

    models = load_models(root / "configs" / "models.yaml")["models"]
    assert isinstance(models, dict)
    spec = models[model]
    facts = load_facts(root / "data" / "facts.yaml")
    if limit:
        facts = facts[:limit]
    out = root / "data" / "benchmark" / "drafts" / "drafts.jsonl"
    if fact:
        unknown = set(fact) - {f.id for f in facts}
        if unknown:
            raise typer.BadParameter(f"unknown fact ids: {sorted(unknown)}")
        facts = [f for f in facts if f.id in set(fact)]
    registry = load_registry(root / "data" / "schemes.yaml")
    client = client_from_root(root)
    drafts, failed = draft_all(client, facts, registry, spec["provider"], spec["model"])
    if fact and out.is_file():
        redrafted = {d.item_id for d in drafts}
        kept = [d for d in load_drafts(out) if d.item_id not in redrafted]
        drafts = [*kept, *drafts]
    write_drafts(drafts, out)
    leaky = [d.item_id for d in drafts if d.leaks]
    typer.echo(
        f"{len(drafts)} drafts -> {out} ({client.calls_made} new calls, rest cached); "
        f"{len(failed)} failed, {len(leaky)} flagged as leaking a value"
    )
    for item_id in failed:
        typer.echo(f"  failed: {item_id}", err=True)
    for item_id in leaky:
        typer.echo(f"  leak: {item_id}", err=True)


@bench_app.command("export")
def bench_export(
    root: RootOption = Path("."),
    fact: Annotated[list[str] | None, typer.Option(help="Only this fact id (repeatable).")] = None,
    style: Annotated[list[str] | None, typer.Option(help="Only this style (repeatable).")] = None,
    name: Annotated[str, typer.Option(help="Sheet file name.")] = "review_sheet.csv",
) -> None:
    """Write the review spreadsheet for human verification (milestone 2d)."""
    from policydrift.bench.drafts import load_drafts
    from policydrift.bench.facts import load_facts
    from policydrift.bench.verify import export_review_sheet

    bench = root / "data" / "benchmark"
    drafts = load_drafts(bench / "drafts" / "drafts.jsonl")
    if fact:
        drafts = [d for d in drafts if d.fact_id in set(fact)]
    if style:
        drafts = [d for d in drafts if d.style in set(style)]
    facts = load_facts(root / "data" / "facts.yaml")
    registry = load_registry(root / "data" / "schemes.yaml")
    out = bench / "verification" / name
    export_review_sheet(drafts, facts, registry, out)
    typer.echo(f"{len(drafts)} rows -> {out} (open in Excel; save as CSV UTF-8 when done)")


@bench_app.command("import")
def bench_import(
    sheet: Annotated[Path, typer.Argument(help="The reviewed CSV.")],
    root: RootOption = Path("."),
) -> None:
    """Read a reviewed sheet into data/benchmark/verification/verified.jsonl."""
    from policydrift.bench.drafts import load_drafts
    from policydrift.bench.facts import load_facts
    from policydrift.bench.verify import import_review_sheet, load_verified, write_verified

    bench = root / "data" / "benchmark"
    drafts = load_drafts(bench / "drafts" / "drafts.jsonl")
    facts = load_facts(root / "data" / "facts.yaml")
    items, report = import_review_sheet(sheet, drafts, facts)
    out = bench / "verification" / "verified.jsonl"
    # Merge by item id so a partial sheet never discards earlier reviews.
    earlier = {i.item_id: i for i in load_verified(out)} if out.is_file() else {}
    earlier.update({i.item_id: i for i in items})
    write_verified(list(earlier.values()), out)
    typer.echo(
        f"{report.verified} verified, {report.rejected} rejected, "
        f"{len(report.pending)} still pending, {len(report.problems)} problems -> {out}"
    )
    for problem in report.problems:
        typer.echo(f"  problem: {problem}", err=True)
    if report.problems:
        raise typer.Exit(code=1)


@bench_app.command("freeze")
def bench_freeze(root: RootOption = Path(".")) -> None:
    """Split the verified items by scheme into dev and test, write them, and checksum the test set.

    Refuses to run if the test split already exists: later changes go in the deviation log.
    """
    from policydrift.bench.facts import load_facts
    from policydrift.bench.split import (
        SEED,
        FrozenSplitError,
        assign_schemes,
        build_items,
        freeze,
        load_flags,
    )
    from policydrift.bench.verify import load_verified
    from policydrift.retrieval.search import load_chunks

    bench = root / "data" / "benchmark"
    facts = load_facts(root / "data" / "facts.yaml")
    registry = load_registry(root / "data" / "schemes.yaml")
    chunks = load_chunks(root / "data" / "processed" / "chunks.jsonl")
    verified = load_verified(bench / "verification" / "verified.jsonl")
    split_map = assign_schemes(facts, SEED)
    items = build_items(
        verified, facts, registry, chunks, split_map, load_flags(bench / "flags.yaml")
    )
    try:
        record = freeze(root, items, split_map, SEED)
    except FrozenSplitError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(
        f"dev: {record['dev_items']} items, {record['dev_facts']} facts {record['dev_schemes']}\n"
        f"test: {record['test_items']} items, {record['test_facts']} facts, "
        f"sha256 {record['test_items_sha256'][:16]}..."
    )


@bench_app.command("show")
def bench_show(
    split: Annotated[str, typer.Option(help="dev or test.")] = "dev",
    final: Annotated[
        bool, typer.Option("--final", help="Required to read the test split.")
    ] = False,
    root: RootOption = Path("."),
) -> None:
    """Print item counts for a split. The test split needs --final."""
    from policydrift.bench.split import FrozenSplitError, TestSplitLocked, load_items

    if split not in {"dev", "test"}:
        raise typer.BadParameter("split must be dev or test")
    try:
        items = load_items(root, split, final=final)  # type: ignore[arg-type]
    except (TestSplitLocked, FrozenSplitError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc
    confirmatory = sum(i.confirmatory for i in items)
    typer.echo(
        f"{split}: {len(items)} items, {len({i.fact_id for i in items})} facts, "
        f"{confirmatory} confirmatory"
    )


@app.command("run")
def run_cmd(
    config: Annotated[
        Path, typer.Argument(help="Experiment YAML, e.g. configs/experiments/x.yaml.")
    ],
    root: RootOption = Path("."),
    final: Annotated[
        bool, typer.Option("--final", help="Required to run on the frozen test split.")
    ] = False,
    dry_run: Annotated[bool, typer.Option(help="Count planned and uncached calls only.")] = False,
) -> None:
    """Run one experiment and write runs/<run_id>/ (config, git commit, raw answers)."""
    from policydrift.bench.split import FrozenSplitError, TestSplitLocked
    from policydrift.experiments.config import load_config
    from policydrift.experiments.runner import run_experiment
    from policydrift.llm import client_from_root

    cfg = load_config(config)
    retriever = _local_retriever(root) if any(c != "R0" for c in cfg.conditions) else None
    client = client_from_root(root)

    def show(n: int, total: int) -> None:
        if n % 25 == 0 or n == total:
            typer.echo(f"  {n}/{total}")

    try:
        summary = run_experiment(
            cfg, root, client, retriever, final=final, dry_run=dry_run, progress=show
        )
    except (TestSplitLocked, FrozenSplitError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc
    if dry_run:
        typer.echo(
            f"{summary['planned_calls']} calls planned, {summary['uncached_calls']} not yet cached."
        )
        return
    c = summary["counts"]
    typer.echo(
        f"{summary['run_id']}: {c['ok']} answered ({c['cached']} from cache), "
        f"{c['missing']} missing -> runs/{summary['run_id']}/"
    )


def _run_meta(run_dir: Path, root: Path) -> dict[str, Any]:
    """``run.json``, or for a run still in progress the config it was started from (dev only)."""
    import json

    path = run_dir / "run.json"
    if path.exists():
        meta: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        return meta
    from policydrift.experiments.config import load_config

    name = run_dir.name.rsplit("-", 1)[0]
    cfg = load_config(root / "configs" / "experiments" / f"{name}.yaml")
    if cfg.split != "dev":
        raise typer.BadParameter(f"{run_dir} has no run.json and is not a dev run")
    typer.echo("run.json not written yet (run in progress): scoring the answers so far.")
    return {"config": cfg.model_dump(mode="json"), "final": False}


@app.command("score")
def score_cmd(
    run_dir: Annotated[Path, typer.Argument(help="A runs/<run_id> directory.")],
    root: RootOption = Path("."),
    judge: Annotated[bool, typer.Option(help="Send undecided answers to the LLM judge.")] = True,
) -> None:
    """Score a run: deterministic matcher, then the judge for what it cannot decide."""
    import json

    from policydrift.bench.split import load_items
    from policydrift.llm import client_from_root
    from policydrift.llm.client import load_models
    from policydrift.scoring.pipeline import load_answers, score_run, summarise

    meta = _run_meta(run_dir, root)
    cfg = meta["config"]
    items = {i.item_id: i for i in load_items(root, cfg["split"], final=meta["final"])}
    judge_spec = None
    if judge:
        spec = load_models(root / "configs" / "models.yaml")["models"][cfg["judge_model"]]  # type: ignore[index]
        judge_spec = (client_from_root(root), spec["provider"], spec["model"])
    scores = score_run(load_answers(run_dir), items, judge_spec)
    (run_dir / "scores.jsonl").write_text(
        "".join(s.model_dump_json() + "\n" for s in scores), encoding="utf-8", newline="\n"
    )
    rows = summarise(scores)
    (run_dir / "summary.json").write_text(
        json.dumps(rows, indent=1) + "\n", encoding="utf-8", newline="\n"
    )
    typer.echo("model              cond lang    n  cur  old  oth  ref  unres  miss  outdated")
    for r in rows:
        rate = "-" if r["outdated_rate"] is None else f"{r['outdated_rate']:.2f}"
        typer.echo(
            f"{r['model']:18s} {r['condition']:4s} {r['language']:3s} {r['n']:4d} "
            f"{r['current']:4d} {r['outdated']:4d} {r['other']:4d} {r['refusal']:4d} "
            f"{r['unresolved']:6d} {r['missing']:5d}  {rate}"
        )


@app.command("label-sheet")
def label_sheet_cmd(
    run_dir: Annotated[Path, typer.Argument(help="A scored runs/<run_id> directory.")],
    root: RootOption = Path("."),
    size: Annotated[int, typer.Option(help="Number of answers to label.")] = 45,
) -> None:
    """Write the human labelling sheet (automatic labels hidden) for judge validation."""

    from policydrift.bench.split import load_items
    from policydrift.scoring.agreement import export_label_sheet
    from policydrift.scoring.pipeline import ScoreRecord, load_answers

    meta = _run_meta(run_dir, root)
    items = {i.item_id: i for i in load_items(root, meta["config"]["split"], final=meta["final"])}
    with (run_dir / "scores.jsonl").open(encoding="utf-8") as f:
        scores = [ScoreRecord.model_validate_json(line) for line in f if line.strip()]
    out = root / "data" / "benchmark" / "judge_validation" / f"{run_dir.name}.csv"
    n = export_label_sheet(scores, load_answers(run_dir), items, out, size=size)
    typer.echo(f"{n} answers -> {out}\nFill human_label with: current, outdated, other or refusal.")


@app.command("label-agree")
def label_agree_cmd(sheet: Annotated[Path, typer.Argument(help="The labelled CSV.")]) -> None:
    """Cohen's kappa of the automatic labels against the human labels."""
    import json

    from policydrift.scoring.agreement import agreement_report

    typer.echo(json.dumps(agreement_report(sheet), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    app()
