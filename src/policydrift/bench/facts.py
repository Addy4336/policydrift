"""Curated rule facts: what changed, the old and current value, and the chunks that prove it.

The LLM never decides what is correct. Every gold answer comes from this table, and
:func:`validate_facts` checks each value against the exact source text it cites.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict

from policydrift.bench.forms import amount_forms, count_forms
from policydrift.ingest.build import Chunk
from policydrift.ingest.registry import Registry

Kind = Literal["inr", "count", "days", "years"]


class Evidence(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    chunk_id: str
    quote: str  # must appear verbatim in the chunk text


class FactValue(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    version: str
    value: int
    evidence: list[Evidence]
    # "contemporary": the cited document belongs to this version's own period.
    # "restated": the value is only known from a later document ("raised from X to Y").
    evidence_kind: Literal["contemporary", "restated"] = "contemporary"
    quote_in_words: bool = False  # the quote spells the number out, so skip the digit check


class Fact(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    scheme: str
    attribute: str  # English description, used to write questions
    kind: Kind
    old: FactValue
    current: FactValue
    changed_in: str  # version in which the value changed
    caveat: str | None = None


def load_facts(path: Path) -> list[Fact]:
    with path.open(encoding="utf-8") as f:
        return [Fact.model_validate(item) for item in yaml.safe_load(f)]


def value_forms(kind: Kind, value: int, lang: str = "en") -> list[str]:
    return amount_forms(value, lang) if kind == "inr" else count_forms(value, lang)


def validate_facts(facts: Sequence[Fact], chunks: Sequence[Chunk], registry: Registry) -> list[str]:
    """Return one message per problem; an empty list means the table is consistent."""
    by_id = {c.chunk_id: c for c in chunks}
    problems: list[str] = []
    seen: set[str] = set()
    for fact in facts:
        tag = fact.id
        if fact.id in seen:
            problems.append(f"{tag}: duplicate fact id")
        seen.add(fact.id)
        scheme = registry.get(fact.scheme)
        if scheme is None:
            problems.append(f"{tag}: unknown scheme {fact.scheme}")
            continue
        order = [v.id for v in scheme.versions]
        for label, version in (
            ("old", fact.old.version),
            ("current", fact.current.version),
            ("changed_in", fact.changed_in),
        ):
            if version not in order:
                problems.append(f"{tag}: {label} version {version} is not in the registry")
        if problems and any(p.startswith(f"{tag}:") and "registry" in p for p in problems):
            continue
        if fact.current.version != order[-1]:
            problems.append(f"{tag}: current.version must be the scheme's current version")
        if order.index(fact.old.version) >= order.index(fact.current.version):
            problems.append(f"{tag}: old version must precede the current version")
        if (
            not order.index(fact.old.version)
            < order.index(fact.changed_in)
            <= order.index(fact.current.version)
        ):
            problems.append(f"{tag}: changed_in must be after old and not after current")
        if fact.old.value == fact.current.value:
            problems.append(f"{tag}: old and current values are equal")
        for label, fv in (("old", fact.old), ("current", fact.current)):
            problems += _check_value(tag, label, fv, fact, by_id, order[-1])
    return problems


def _check_value(
    tag: str,
    label: str,
    fv: FactValue,
    fact: Fact,
    by_id: dict[str, Chunk],
    current_version: str,
) -> list[str]:
    problems: list[str] = []
    if not fv.evidence:
        return [f"{tag}.{label}: no evidence"]
    expected_version = fv.version if fv.evidence_kind == "contemporary" else current_version
    for ev in fv.evidence:
        chunk = by_id.get(ev.chunk_id)
        if chunk is None:
            problems.append(f"{tag}.{label}: unknown chunk {ev.chunk_id}")
            continue
        if chunk.scheme != fact.scheme or chunk.version != expected_version:
            problems.append(
                f"{tag}.{label}: chunk {ev.chunk_id} is {chunk.scheme}/{chunk.version}, "
                f"expected {fact.scheme}/{expected_version}"
            )
        if ev.quote not in chunk.text:
            problems.append(f"{tag}.{label}: quote not found in {ev.chunk_id}: {ev.quote!r}")
        elif not fv.quote_in_words and not any(
            form in ev.quote for form in value_forms(fact.kind, fv.value, "en")
        ):
            problems.append(
                f"{tag}.{label}: value {fv.value} does not appear in quote {ev.quote!r}"
            )
    return problems
