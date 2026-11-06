"""The demo agent: version-aware RAG with validated citations and rule-change flags.

It applies the two mitigations that worked on the dev split:

- **M-c, version-filtered retrieval:** only chunks in force on the as-of date are given to the
  model, so a superseded rule cannot be quoted as current.
- **M-a1, date-stamped prompt:** the model is told the as-of date and to answer with the version
  in force then.

A second, unfiltered search finds superseded (or not yet in force) versions of the same schemes;
those are not shown to the model but are returned as ``conflicts`` so the user sees that the rule
changed. Every LLM call goes through the cached, rate-limited client. The demo keeps its own LLM
and embedding caches under ``.cache/demo/`` so it never writes to the research caches.
"""

from __future__ import annotations

import shutil
import time
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Literal

from policydrift.agents.mitigations import system_for
from policydrift.citations import normalise_markers, validate
from policydrift.db import read_env_file
from policydrift.demo.routing import pick_scheme
from policydrift.experiments.prompts import LANGUAGE_NAMES, format_passages
from policydrift.ingest.build import Chunk
from policydrift.ingest.registry import Registry, load_registry
from policydrift.llm import LLMClient, LLMRequest, ResponseCache
from policydrift.llm.client import KEY_VARS, load_models
from policydrift.retrieval.embed import (
    DEFAULT_MODEL,
    MODELS,
    EmbeddingCache,
    SentenceTransformerEmbedder,
)
from policydrift.retrieval.search import Filters, Retriever, load_chunks

Language = Literal["en", "hi", "gu"]

PROMPT = (
    "Use the passages below to answer. After every figure or rule you state, cite the passage "
    "it comes from in square brackets, for example [1] or [2]. Use only these passages. If they "
    "do not contain the answer, say so plainly and do not guess.\n\n{passages}\n\nQuestion: "
    "{question}\n\nAnswer in {language_name}."
)
TRANSLATE_SYSTEM = (
    "Translate the user's question about an Indian government scheme into English. Keep scheme "
    "names and numbers as they are. Output only the English question, on one line."
)
NO_ANSWER_HINTS = (
    "do not contain",
    "does not contain",
    "not contain the answer",
    "not mentioned",
    "no information",
    "उपलब्ध नहीं",
    "नहीं है",
    "ઉપલબ્ધ નથી",
    "માહિતી નથી",
)


@dataclass(frozen=True)
class DemoSettings:
    model_key: str = "groq-gpt-oss"  # key in configs/models.yaml
    k: int = 4  # passages shown to the model
    k_conflicts: int = 8  # unfiltered search depth for rule-change flags
    doc_language: str = "en"  # passages in English for every question language, as in the study
    max_tokens: int = 2048


def _iso(d: date | None) -> str | None:
    return d.isoformat() if d else None


def _in_force(chunk: Chunk, day: date) -> bool:
    starts_ok = chunk.effective_from is None or chunk.effective_from <= day
    ends_ok = chunk.effective_to is None or day <= chunk.effective_to
    return starts_ok and ends_ok


def _excerpt(text: str, limit: int = 420) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1].rsplit(" ", 1)[0] + "…"


class DemoService:
    def __init__(self, root: Path, settings: DemoSettings | None = None) -> None:
        self.root = root
        self.settings = settings or DemoSettings()
        self.registry: Registry = load_registry(root / "data" / "schemes.yaml")
        self.chunks = load_chunks(root / "data" / "processed" / "chunks.jsonl")
        self._retriever: Retriever | None = None
        self._client: LLMClient | None = None
        models = load_models(root / "configs" / "models.yaml")["models"]
        assert isinstance(models, dict)
        spec = models[self.settings.model_key]
        self.provider: Literal["gemini", "groq"] = spec["provider"]
        self.model_id: str = spec["model"]

    # -- lazy resources ---------------------------------------------------------------------
    @property
    def retriever(self) -> Retriever:
        if self._retriever is None:
            model = MODELS[DEFAULT_MODEL]
            demo_dir = self.root / ".cache" / "demo" / "embeddings"
            research = self.root / ".cache" / "embeddings" / f"{model.key}.npz"
            target = demo_dir / f"{model.key}.npz"
            if not target.exists() and research.exists():  # start from the research vectors
                demo_dir.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(research, target)
            cache = EmbeddingCache(demo_dir, model)
            self._retriever = Retriever(
                self.chunks, SentenceTransformerEmbedder(model), cache, self.registry
            )
        return self._retriever

    @property
    def client(self) -> LLMClient:
        if self._client is None:
            import os

            config = load_models(self.root / "configs" / "models.yaml")
            rpm = config["requests_per_minute"]
            assert isinstance(rpm, dict)
            env = read_env_file(self.root / ".env")
            keys = {p: os.environ.get(v) or env.get(v, "") for p, v in KEY_VARS.items()}
            cache = ResponseCache(self.root / ".cache" / "demo" / "llm.sqlite")
            self._client = LLMClient(cache, keys, {str(k): int(v) for k, v in rpm.items()})
        return self._client

    # -- public API ---------------------------------------------------------------------------
    def scheme_name(self, scheme: str) -> str:
        s = self.registry.get(scheme)
        return s.name if s else scheme

    def schemes(self, today: date | None = None) -> list[dict[str, Any]]:
        day = today or date.today()
        return [
            {
                "id": sid,
                "name": s.name,
                "versions": [
                    {
                        "id": v.id,
                        "effective_from": _iso(v.effective_from),
                        "effective_to": _iso(v.effective_to),
                        "announced_on": _iso(v.announced_on),
                        "in_force": v.in_force_on(day),
                    }
                    for v in s.versions
                ],
            }
            for sid, s in self.registry.items()
        ]

    def search_query(self, question: str, language: Language) -> str:
        """The question in English for retrieval (passages are English; e5-base matches
        Hindi and Gujarati questions to English passages poorly). One cached LLM call."""
        if language == "en":
            return question
        request = LLMRequest(
            provider=self.provider,
            model=self.model_id,
            system=TRANSLATE_SYSTEM,
            prompt=question,
            temperature=0.0,
            max_tokens=1024,
            purpose="demo-translate",
        )
        text = self.client.complete(request).text.strip().strip('"').splitlines()
        return text[0].strip() if text and text[0].strip() else question

    def retrieve(
        self, query: str, as_of: date, question: str = ""
    ) -> tuple[list[Chunk], list[Chunk]]:
        """(passages in force on ``as_of``, other-version chunks of the same scheme).

        The scheme is picked first (by name if the question names one, else by summed
        similarity), and the passages come from that scheme only, so one answer never mixes two
        schemes' rules.
        """
        lang = self.settings.doc_language
        pool = self.retriever.search(
            query, self.settings.k_conflicts, Filters(language=lang, as_of=as_of)
        )
        picked = pick_scheme(pool, question, query)
        if picked is None:
            return [], []
        scheme = frozenset({picked})
        flt = Filters(language=lang, as_of=as_of, schemes=scheme)
        shown = [h.chunk for h in self.retriever.search(query, self.settings.k, flt)]
        wider = self.retriever.search(
            query, self.settings.k_conflicts, Filters(language=lang, schemes=scheme)
        )
        others = [h.chunk for h in wider if not _in_force(h.chunk, as_of)]
        return shown, others

    def ask(self, question: str, language: Language, as_of: date | None = None) -> dict[str, Any]:
        day = as_of or date.today()
        question = question.strip()
        started = time.monotonic()
        query = self.search_query(question, language)
        shown, others = self.retrieve(query, day, question)
        warnings: list[str] = []
        if not shown:
            answer, cached = "", False
            warnings.append("No official passage in force on this date matched the question.")
        else:
            request = LLMRequest(
                provider=self.provider,
                model=self.model_id,
                system=system_for("M-a1", day),
                prompt=PROMPT.format(
                    passages=format_passages(shown, show_dates=True),
                    question=question,
                    language_name=LANGUAGE_NAMES[language],
                ),
                temperature=0.0,
                max_tokens=self.settings.max_tokens,
                purpose="demo",
            )
            response = self.client.complete(request)
            answer, cached = normalise_markers(response.text.strip()), response.cached
        latency_ms = round((time.monotonic() - started) * 1000)

        says_no = any(h in answer.lower() for h in NO_ANSWER_HINTS)
        report = validate(answer, [c.text for c in shown], says_no_answer=says_no)
        if report.invalid_markers:
            warnings.append("The answer cites a passage number that was not provided.")
        if report.uncited:
            warnings.append("The answer does not cite any source; treat it with care.")
        unverified = [n.value for n in report.numbers if not n.verified]
        if unverified:
            warnings.append(
                "Some figures were not found in the cited sources: " + ", ".join(unverified)
            )

        cited = report.cited or []
        citations = [self._citation(i, shown[i - 1], day) for i in range(1, len(shown) + 1)]
        used = [shown[i - 1] for i in cited] or shown[:1]
        rule_versions: list[dict[str, Any]] = []
        for c in used:
            entry = {
                "scheme": c.scheme,
                "scheme_name": self.scheme_name(c.scheme),
                "version": c.version,
                "effective_from": _iso(c.effective_from),
                "effective_to": _iso(c.effective_to),
            }
            if entry not in rule_versions:
                rule_versions.append(entry)
        return {
            "answer": answer,
            "language": language,
            "as_of": day.isoformat(),
            "search_query": query,
            "model": self.model_id,
            "cached": cached,
            "latency_ms": latency_ms,
            "citations": citations,
            "rule_versions": rule_versions,
            "conflicts": self._conflicts(others, shown, day),
            "checks": {
                "citations_valid": report.citations_valid,
                "uncited": report.uncited,
                "invalid_markers": report.invalid_markers,
                "numbers": [
                    {"value": n.value, "verified": n.verified, "cited_in": n.cited_in}
                    for n in report.numbers
                ],
            },
            "warnings": warnings,
        }

    # -- helpers --------------------------------------------------------------------------------
    def _citation(self, n: int, c: Chunk, day: date) -> dict[str, Any]:
        return {
            "id": n,
            "chunk_id": c.chunk_id,
            "scheme": c.scheme,
            "scheme_name": self.scheme_name(c.scheme),
            "version": c.version,
            "effective_from": _iso(c.effective_from),
            "effective_to": _iso(c.effective_to),
            "in_force": _in_force(c, day),
            "title": c.title,
            "source_url": c.source_url,
            "posted_on": c.posted_on.isoformat(),
            "ministry": c.ministry,
            "excerpt": _excerpt(c.text),
        }

    def _conflicts(
        self, others: list[Chunk], shown: list[Chunk], day: date
    ) -> list[dict[str, Any]]:
        current = {c.scheme: c.version for c in shown}
        out: list[dict[str, Any]] = []
        seen: set[tuple[str, str]] = set()
        for c in others:
            key = (c.scheme, c.version)
            if key in seen or c.version == current.get(c.scheme):
                continue
            seen.add(key)
            if c.effective_to is not None and c.effective_to < day:
                note = (
                    f"An older version ({c.version}) applied until {c.effective_to.isoformat()}. "
                    f"The answer uses the version in force on {day.isoformat()} "
                    f"({current.get(c.scheme, '?')})."
                )
            else:
                start = c.effective_from.isoformat() if c.effective_from else "a later date"
                note = f"A newer version ({c.version}) takes effect from {start}."
            out.append(
                {
                    "scheme": c.scheme,
                    "scheme_name": self.scheme_name(c.scheme),
                    "superseded_version": c.version,
                    "effective_from": _iso(c.effective_from),
                    "effective_to": _iso(c.effective_to),
                    "title": c.title,
                    "source_url": c.source_url,
                    "excerpt": _excerpt(c.text, 280),
                    "note": note,
                }
            )
        return out

    def examples(self) -> dict[str, list[str]]:
        """Example questions from the dev split only (the test split stays sealed)."""
        from policydrift.bench.split import load_items

        out: dict[str, list[str]] = {"en": [], "hi": [], "gu": []}
        for item in load_items(self.root, "dev", final=False):
            if item.style != "direct":
                continue
            for lang in out:
                q = item.questions.get(lang)
                if q and len(out[lang]) < 6 and q not in out[lang]:
                    out[lang].append(q)
        return out
