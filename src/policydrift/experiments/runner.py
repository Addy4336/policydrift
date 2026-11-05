"""Run one experiment config: build prompts, call the cached client, log every raw answer."""

from __future__ import annotations

import hashlib
import json
import subprocess
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

from policydrift.agents.mitigations import (
    Checked,
    run_conflict_checker,
    show_dates_for,
    system_for,
)
from policydrift.bench.split import BenchItem, load_items
from policydrift.experiments.config import Condition, ExperimentConfig, Language
from policydrift.experiments.prompts import SYSTEM, build_prompt
from policydrift.ingest.build import Chunk
from policydrift.llm import LLMClient, LLMError, LLMRequest, LLMResponse
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
    mitigation: str
    system: str
    prompt: str
    answer: str | None
    status: str  # "ok" or "missing"
    error: str | None
    input_tokens: int | None
    output_tokens: int | None
    calls: int  # LLM calls behind this answer (1, or 2-3 for the conflict checker)
    draft: str | None  # M-b only: the answer before the check
    check: str | None  # M-b only: consistent, revised or unparsed
    max_tokens: int  # budget of the call that produced the answer (or the last failed attempt)
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


def _documents_in(
    item: BenchItem, lang: str, versions: Sequence[str], cfg: ExperimentConfig
) -> str:
    return "en" if cfg.doc_language == "english" else doc_language(item, lang, versions)


def corrupted_dates(
    chunks: Sequence[Chunk], cfg: ExperimentConfig
) -> dict[str, tuple[date | None, date | None]]:
    """Effective windows replaced for a hash-chosen share of chunks (M-c robustness test)."""
    if cfg.date_corruption == "none" or cfg.date_corruption_share == 0.0:
        return {}
    out: dict[str, tuple[date | None, date | None]] = {}
    for c in chunks:
        digest = hashlib.sha256(f"{cfg.seed}|{c.chunk_id}".encode()).digest()
        if int.from_bytes(digest[:8], "big") / 2**64 >= cfg.date_corruption_share:
            continue
        if cfg.date_corruption == "missing":
            out[c.chunk_id] = (None, None)
        elif c.effective_to is not None:  # expired chunk made to look in force
            out[c.chunk_id] = (c.effective_from, None)
        else:  # in-force chunk made to look expired
            out[c.chunk_id] = (c.effective_from, cfg.as_of - timedelta(days=1))
    return out


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
        dl = _documents_in(item, lang, [cur], cfg)
        as_of = cfg.as_of if cfg.mitigation == "M-c" else None
        flt = Filters(
            language=dl, as_of=as_of, date_override=corrupted_dates(retriever.chunks, cfg)
        )
        hits = retriever.search(question, cfg.k, flt)
        return Context([h.chunk for h in hits], dl)
    if condition == "R2":
        dl = _documents_in(item, lang, [cur], cfg)
        flt = Filters(schemes=frozenset({item.scheme}), versions=frozenset({cur}), language=dl)
        return Context([h.chunk for h in retriever.search(question, cfg.k, flt)], dl)
    dl = "en" if condition == "X" else _documents_in(item, lang, [cur, old], cfg)

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


def build_request(
    cfg: ExperimentConfig, spec: dict[str, Any], prompt: str, system: str = SYSTEM
) -> LLMRequest:
    return LLMRequest(
        provider=spec["provider"],
        model=spec["model"],
        system=system,
        prompt=prompt,
        max_tokens=cfg.max_tokens,
        seed=cfg.seed,
        purpose="answer",
    )


class _Uncached(Exception):
    """A dry run reached a call that is not in the cache."""


def _ask(client: LLMClient, cfg: ExperimentConfig, request: LLMRequest) -> LLMResponse:
    """One call, with the bigger-budget retry for length-truncated empty answers."""
    try:
        return client.complete(request).model_copy(update={"max_tokens": request.max_tokens})
    except LLMError as exc:
        retry = _bigger_budget(cfg, request)
        if retry is not None and "finish_reason=length" in str(exc):
            return client.complete(retry).model_copy(update={"max_tokens": retry.max_tokens})
        raise


def _peek(client: LLMClient, cfg: ExperimentConfig, request: LLMRequest) -> LLMResponse:
    retry = _bigger_budget(cfg, request)
    for candidate in (request, retry):
        if candidate is None:
            continue
        hit = client.peek(candidate)
        if hit is not None:
            return hit.model_copy(update={"max_tokens": candidate.max_tokens})
    raise _Uncached


def _bigger_budget(cfg: ExperimentConfig, request: LLMRequest) -> LLMRequest | None:
    if cfg.retry_max_tokens <= request.max_tokens:
        return None
    return request.model_copy(update={"max_tokens": cfg.retry_max_tokens})


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
            question = item.questions[lang]
            show = show_dates_for(cfg.mitigation, SHOW_DATES[condition])
            system = system_for(cfg.mitigation, cfg.as_of)
            prompt = build_prompt(question, ctx.chunks, show)
            request = build_request(cfg, spec, prompt, system)
            checker = cfg.mitigation == "M-b" and bool(ctx.chunks)

            def make(sys_: str, prompt_: str, spec: dict[str, Any] = spec) -> LLMRequest:
                return build_request(cfg, spec, prompt_, sys_)

            if dry_run:
                try:
                    if checker:
                        run_conflict_checker(
                            lambda r: _peek(client, cfg, r),
                            make,
                            question,
                            ctx.chunks,
                            show,
                            cfg.as_of,
                        )
                    else:
                        _peek(client, cfg, request)
                except _Uncached:
                    uncached += 1
                continue
            answer = error = None
            reply = None
            checked: Checked | None = None
            try:
                if checker:
                    checked = run_conflict_checker(
                        lambda r: _ask(client, cfg, r),
                        make,
                        question,
                        ctx.chunks,
                        show,
                        cfg.as_of,
                    )
                    reply = checked.final
                else:
                    reply = _ask(client, cfg, request)
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
                mitigation=cfg.mitigation,
                system=system,
                prompt=prompt,
                answer=answer,
                status="ok" if reply else "missing",
                error=error,
                input_tokens=(checked.input_tokens if checked else reply.input_tokens)
                if reply
                else None,
                output_tokens=(checked.output_tokens if checked else reply.output_tokens)
                if reply
                else None,
                calls=checked.calls if checked else 1,
                draft=checked.draft if checked else None,
                check=checked.verdict if checked else None,
                max_tokens=(reply.max_tokens if reply else None) or request.max_tokens,
                latency_s=(checked.latency_s if checked else reply.latency_s) if reply else None,
                cached=(checked.cached if checked else reply.cached) if reply else None,
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
            "config": cfg.model_dump(mode="json"),
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
