"""Run one experiment config: build prompts, call the cached client, log every raw answer."""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

from policydrift.bench.split import BenchItem, load_items
from policydrift.experiments.config import Condition, ExperimentConfig, Language
from policydrift.experiments.prompts import SYSTEM, build_prompt
from policydrift.ingest.build import Chunk
from policydrift.llm import LLMClient, LLMError, LLMRequest
from policydrift.llm.client import load_models
from policydrift.retrieval.search import Filters, Retriever
from policydrift.scoring.matcher import same_value
from policydrift.scoring.numbers import extract_numbers

SHOW_DATES: dict[Condition, bool] = {
    "R0": False,
    "R1": False,
    "R2": False,
    "R3": True,
    "R4": False,
    "X": True,
}


class AnswerRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    item_id: str
    fact_id: str
    model: str  # key in configs/models.yaml
    model_id: str
    model_version: str | None
    language: str
    condition: str
    doc_language: str | None
    chunk_ids: list[str]
    context_has_current: bool | None  # does any retrieved chunk state the current value?
    context_has_old: bool | None
    system: str
    prompt: str
    answer: str | None
    status: str  # "ok" or "missing"
    error: str | None
    input_tokens: int | None
    output_tokens: int | None
    latency_s: float | None
    cached: bool | None
    created_at: str | None


@dataclass(frozen=True)
class Context:
    chunks: list[Chunk]
    doc_language: str | None


def doc_language(item: BenchItem, lang: str, versions: Sequence[str]) -> str:
    """The question's language if every needed version has a source in it, else English."""
    ok = all(lang in item.source_languages.get(v, []) for v in versions)
    return lang if ok else "en"


def select_context(
    retriever: Retriever,
    item: BenchItem,
    lang: str,
    condition: Condition,
    cfg: ExperimentConfig,
    position: int,
) -> Context:
    """Retrieve the passages the model sees under ``condition`` (pre-registration §2)."""
    if condition == "R0":
        return Context([], None)
    question = item.questions[lang]
    cur, old = item.current.version, item.old.version
    if condition == "R1":
        dl = doc_language(item, lang, [cur])
        hits = retriever.search(question, cfg.k, Filters(language=dl))
        return Context([h.chunk for h in hits], dl)
    if condition == "R2":
        dl = doc_language(item, lang, [cur])
        flt = Filters(schemes=frozenset({item.scheme}), versions=frozenset({cur}), language=dl)
        return Context([h.chunk for h in retriever.search(question, cfg.k, flt)], dl)
    dl = "en" if condition == "X" else doc_language(item, lang, [cur, old])

    def top(version: str) -> list[Chunk]:
        flt = Filters(schemes=frozenset({item.scheme}), versions=frozenset({version}), language=dl)
        return [h.chunk for h in retriever.search(question, cfg.k_each, flt)]

    current_first = {
        "current_first": True,
        "old_first": False,
        "counterbalanced": position % 2 == 0,
    }[cfg.passage_order]
    pair = [top(cur), top(old)]
    return Context([c for part in (pair if current_first else pair[::-1]) for c in part], dl)


def _states(chunks: Sequence[Chunk], value: float) -> bool:
    return any(same_value(n, value) for c in chunks for n in extract_numbers(c.text))


def planned_conditions(cfg: ExperimentConfig, lang: str) -> list[Condition]:
    """X only differs from R3 when the question is not English."""
    return [c for c in cfg.conditions if not (c == "X" and lang == "en")]


def git_state(root: Path) -> dict[str, Any]:
    def run(*args: str) -> str:
        try:
            out = subprocess.run(
                ["git", *args], cwd=root, capture_output=True, text=True, check=True
            )
            return out.stdout.strip()
        except (OSError, subprocess.CalledProcessError):
            return "unknown"

    return {"commit": run("rev-parse", "HEAD"), "dirty": bool(run("status", "--porcelain"))}


def plan(
    cfg: ExperimentConfig, items: Sequence[BenchItem]
) -> Iterator[tuple[str, BenchItem, Language, Condition, int]]:
    for model in cfg.models:
        for position, item in enumerate(items):
            for lang in cfg.languages:
                for condition in planned_conditions(cfg, lang):
                    yield model, item, lang, condition, position


def select_items(cfg: ExperimentConfig, root: Path, final: bool) -> list[BenchItem]:
    items = load_items(root, cfg.split, final=final)
    if cfg.only_confirmatory:
        items = [i for i in items if i.confirmatory]
    items = sorted(items, key=lambda i: i.item_id)
    return items[: cfg.item_limit] if cfg.item_limit else items


def build_request(cfg: ExperimentConfig, spec: dict[str, Any], prompt: str) -> LLMRequest:
    return LLMRequest(
        provider=spec["provider"],
        model=spec["model"],
        system=SYSTEM,
        prompt=prompt,
        max_tokens=cfg.max_tokens,
        seed=cfg.seed,
        purpose="answer",
    )


def run_experiment(
    cfg: ExperimentConfig,
    root: Path,
    client: LLMClient,
    retriever: Retriever | None,
    *,
    final: bool = False,
    dry_run: bool = False,
    progress: Callable[[int, int], None] | None = None,
) -> dict[str, Any]:
    """Run every planned call and write ``runs/<run_id>/{run.json,answers.jsonl}``.

    With ``dry_run`` nothing is called or written; the result counts planned and uncached calls.
    """
    models = load_models(root / "configs" / "models.yaml")["models"]
    assert isinstance(models, dict)
    unknown = [m for m in cfg.models if m not in models]
    if unknown:
        raise ValueError(f"models not in configs/models.yaml: {unknown}")
    items = select_items(cfg, root, final)
    steps = list(plan(cfg, items))
    needs_retrieval = any(c != "R0" for c in cfg.conditions)
    if needs_retrieval and retriever is None:
        raise ValueError("this config retrieves passages but no retriever was given")

    started = datetime.now(UTC)
    run_id = f"{cfg.name}-{started:%Y%m%dT%H%M%SZ}"
    out_dir = root / "runs" / run_id
    uncached = 0
    versions: dict[str, set[str]] = {m: set() for m in cfg.models}
    counts = {"ok": 0, "missing": 0, "cached": 0}
    handle = None
    if not dry_run:
        out_dir.mkdir(parents=True)
        handle = (out_dir / "answers.jsonl").open("w", encoding="utf-8", newline="\n")
    try:
        for n, (model, item, lang, condition, position) in enumerate(steps, start=1):
            spec = models[model]
            if condition == "R0":
                ctx = Context([], None)
            else:
                assert retriever is not None
                ctx = select_context(retriever, item, lang, condition, cfg, position)
            prompt = build_prompt(item.questions[lang], ctx.chunks, SHOW_DATES[condition])
            request = build_request(cfg, spec, prompt)
            if dry_run:
                uncached += 0 if client.is_cached(request) else 1
                continue
            answer = error = None
            reply = None
            try:
                reply = client.complete(request)
                answer = reply.text
            except LLMError as exc:
                error = str(exc)
            if reply is not None and reply.model_version:
                versions[model].add(reply.model_version)
            counts["ok" if reply else "missing"] += 1
            counts["cached"] += 1 if reply and reply.cached else 0
            record = AnswerRecord(
                run_id=run_id,
                item_id=item.item_id,
                fact_id=item.fact_id,
                model=model,
                model_id=spec["model"],
                model_version=reply.model_version if reply else None,
                language=lang,
                condition=condition,
                doc_language=ctx.doc_language,
                chunk_ids=[c.chunk_id for c in ctx.chunks],
                context_has_current=_states(ctx.chunks, item.current.value) if ctx.chunks else None,
                context_has_old=_states(ctx.chunks, item.old.value) if ctx.chunks else None,
                system=SYSTEM,
                prompt=prompt,
                answer=answer,
                status="ok" if reply else "missing",
                error=error,
                input_tokens=reply.input_tokens if reply else None,
                output_tokens=reply.output_tokens if reply else None,
                latency_s=reply.latency_s if reply else None,
                cached=reply.cached if reply else None,
                created_at=reply.created_at if reply else None,
            )
            assert handle is not None
            handle.write(record.model_dump_json() + "\n")
            handle.flush()
            if progress:
                progress(n, len(steps))
    finally:
        if handle:
            handle.close()
    summary: dict[str, Any] = {
        "run_id": run_id,
        "planned_calls": len(steps),
        "uncached_calls": uncached if dry_run else None,
        "counts": counts,
    }
    if not dry_run:
        meta = {
            "run_id": run_id,
            "config": cfg.model_dump(),
            "final": final,
            "git": git_state(root),
            "started_at": started.isoformat(timespec="seconds"),
            "finished_at": datetime.now(UTC).isoformat(timespec="seconds"),
            "models": {m: {**models[m], "versions_seen": sorted(versions[m])} for m in cfg.models},
            "counts": counts,
            "planned_calls": len(steps),
        }
        (out_dir / "run.json").write_text(
            json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n"
        )
    return summary
