"""Dev/test split, freeze and the guarded benchmark loader (milestone 2e).

The split is by scheme, not by item or fact: facts of one scheme share source documents, so
putting some on each side would let tuning on dev leak into test. The test file is written once,
checksummed, and the loader refuses to return it without ``final=True``.
"""

from __future__ import annotations

import hashlib
import json
import random
import subprocess
from collections import Counter
from collections.abc import Mapping, Sequence
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict

from policydrift.bench.facts import Fact
from policydrift.bench.verify import VerifiedItem
from policydrift.ingest.build import Chunk
from policydrift.ingest.registry import Registry

Split = Literal["dev", "test"]
SEED = 20261101
DEV_FACT_TARGET = 14  # about a third of 42 facts


class TestSplitLocked(RuntimeError):
    """Raised when the test split is requested without the explicit final flag."""

    __test__ = False  # not a pytest class


class FrozenSplitError(RuntimeError):
    """Raised when the frozen test split is missing, changed, or would be overwritten."""


class ValueInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: str
    value: float
    effective_from: date | None
    effective_to: date | None
    evidence_kind: Literal["contemporary", "restated"]


class BenchItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_id: str
    fact_id: str
    scheme: str
    split: Split
    style: str
    questions: dict[str, str]
    kind: str
    attribute: str
    old: ValueInfo
    current: ValueInfo
    changed_in: str
    source_languages: dict[str, list[str]]  # version -> languages with a source document
    lang_status: dict[str, str]
    reviewer: str
    confirmatory: bool = True  # False: report separately, never use to support H1-H3
    flags: list[str] = []


def assign_schemes(
    facts: Sequence[Fact], seed: int = SEED, dev_target: int = DEV_FACT_TARGET
) -> dict[str, Split]:
    """Pick whole schemes for dev so that dev has about ``dev_target`` facts and every kind."""
    sizes = Counter(f.scheme for f in facts)
    kinds: dict[str, set[str]] = {}
    for f in facts:
        kinds.setdefault(f.scheme, set()).add(f.kind)
    all_kinds = {f.kind for f in facts}
    schemes = sorted(sizes)
    rng = random.Random(seed)
    best: tuple[float, tuple[str, ...]] | None = None
    for _ in range(5000):
        k = rng.randint(3, 6)
        pick = tuple(sorted(rng.sample(schemes, k)))
        n = sum(sizes[s] for s in pick)
        got = set().union(*(kinds[s] for s in pick))
        score = abs(n - dev_target) + 2 * len(all_kinds - got)
        if best is None or score < best[0]:
            best = (score, pick)
    assert best is not None
    dev = set(best[1])
    return {s: ("dev" if s in dev else "test") for s in schemes}


def load_flags(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"facts": {}, "items": {}}
    with path.open(encoding="utf-8") as f:
        loaded: dict[str, Any] = yaml.safe_load(f) or {}
    return {"facts": loaded.get("facts", {}), "items": loaded.get("items", {})}


def build_items(
    verified: Sequence[VerifiedItem],
    facts: Sequence[Fact],
    registry: Registry,
    chunks: Sequence[Chunk],
    split_map: Mapping[str, Split],
    flags: Mapping[str, Any],
) -> list[BenchItem]:
    by_fact = {f.id: f for f in facts}
    langs: dict[tuple[str, str], set[str]] = {}
    for c in chunks:
        langs.setdefault((c.scheme, c.version), set()).add(c.language)
    items: list[BenchItem] = []
    for v in verified:
        if v.status != "verified":
            continue
        fact = by_fact[v.fact_id]
        scheme = registry[fact.scheme]

        def info(fv: Any, scheme: Any = scheme) -> ValueInfo:
            ver = scheme.version(fv.version)
            return ValueInfo(
                version=fv.version,
                value=fv.value,
                effective_from=ver.effective_from,
                effective_to=ver.effective_to,
                evidence_kind=fv.evidence_kind,
            )

        fact_flag = flags["facts"].get(fact.id, {})
        item_flag = flags["items"].get(v.item_id, {})
        notes = [x["reason"] for x in (fact_flag, item_flag) if x.get("reason")]
        items.append(
            BenchItem(
                item_id=v.item_id,
                fact_id=fact.id,
                scheme=fact.scheme,
                split=split_map[fact.scheme],
                style=v.style,
                questions=v.questions,
                kind=fact.kind,
                attribute=fact.attribute,
                old=info(fact.old),
                current=info(fact.current),
                changed_in=fact.changed_in,
                source_languages={
                    ver.id: sorted(langs.get((fact.scheme, ver.id), set()))
                    for ver in scheme.versions
                    if ver.id in {fact.old.version, fact.current.version}
                },
                lang_status=dict(v.lang_status),
                reviewer=v.reviewer,
                confirmatory=fact_flag.get("confirmatory", True)
                and item_flag.get("confirmatory", True),
                flags=notes + ([fact.caveat] if fact.caveat else []),
            )
        )
    return sorted(items, key=lambda i: i.item_id)


def _dump(items: Sequence[BenchItem]) -> bytes:
    lines = [i.model_dump_json() for i in items]
    return ("\n".join(lines) + "\n").encode("utf-8")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_head(root: Path) -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=True
        )
        return out.stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def freeze(
    root: Path, items: Sequence[BenchItem], split_map: Mapping[str, Split], seed: int
) -> dict[str, Any]:
    """Write dev and test files and the test checksum. Refuses to touch an existing freeze."""
    bench = root / "data" / "benchmark"
    test_file = bench / "test" / "items.jsonl"
    record_file = bench / "test" / "FROZEN.json"
    if test_file.exists() or record_file.exists():
        raise FrozenSplitError(
            "the test split is already frozen; changes go in the deviation log in "
            "docs/preregistration.md, not in a re-freeze"
        )
    dev_items = [i for i in items if i.split == "dev"]
    test_items = [i for i in items if i.split == "test"]
    (bench / "dev").mkdir(parents=True, exist_ok=True)
    (bench / "test").mkdir(parents=True, exist_ok=True)
    (bench / "dev" / "items.jsonl").write_bytes(_dump(dev_items))
    test_file.write_bytes(_dump(test_items))
    (bench / "split.json").write_text(
        json.dumps(
            {"seed": seed, "unit": "scheme", "assignment": dict(split_map)},
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    record: dict[str, Any] = {
        "frozen_on": datetime.now(UTC).isoformat(timespec="seconds"),
        "based_on_commit": _git_head(root),
        "test_items_sha256": sha256_file(test_file),
        "test_items": len(test_items),
        "test_facts": len({i.fact_id for i in test_items}),
        "test_schemes": sorted({i.scheme for i in test_items}),
        "dev_items": len(dev_items),
        "dev_facts": len({i.fact_id for i in dev_items}),
        "dev_schemes": sorted({i.scheme for i in dev_items}),
        "inputs_sha256": {
            name: sha256_file(root / rel)
            for name, rel in {
                "facts.yaml": "data/facts.yaml",
                "schemes.yaml": "data/schemes.yaml",
                "verified.jsonl": "data/benchmark/verification/verified.jsonl",
                "chunks.jsonl": "data/processed/chunks.jsonl",
            }.items()
        },
    }
    record_file.write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
    return record


def load_items(root: Path, split: Split, final: bool = False) -> list[BenchItem]:
    """The only supported way to read benchmark items. The test split needs ``final=True``."""
    bench = root / "data" / "benchmark"
    if split == "test":
        if not final:
            raise TestSplitLocked(
                "the test split is frozen and may only be read for the final run: pass --final. "
                "Tuning, prompt development and error analysis use the dev split."
            )
        record = json.loads((bench / "test" / "FROZEN.json").read_text(encoding="utf-8"))
        path = bench / "test" / "items.jsonl"
        if sha256_file(path) != record["test_items_sha256"]:
            raise FrozenSplitError("test/items.jsonl does not match its frozen checksum")
    elif split == "dev":
        path = bench / "dev" / "items.jsonl"
    else:
        raise ValueError(f"unknown split {split!r}; use 'dev' or 'test'")
    with path.open(encoding="utf-8") as f:
        return [BenchItem.model_validate_json(line) for line in f if line.strip()]
