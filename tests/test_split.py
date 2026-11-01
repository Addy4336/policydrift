import shutil
from pathlib import Path

import pytest

from policydrift.bench.facts import load_facts
from policydrift.bench.split import (
    FrozenSplitError,
    TestSplitLocked,
    assign_schemes,
    build_items,
    freeze,
    load_flags,
    load_items,
)
from policydrift.bench.verify import load_verified
from policydrift.ingest.registry import load_registry
from policydrift.retrieval.search import load_chunks


def _build(root: Path):  # type: ignore[no-untyped-def]
    facts = load_facts(root / "data" / "facts.yaml")
    registry = load_registry(root / "data" / "schemes.yaml")
    chunks = load_chunks(root / "data" / "processed" / "chunks.jsonl")
    verified = load_verified(root / "data" / "benchmark" / "verification" / "verified.jsonl")
    split_map = assign_schemes(facts)
    flags = load_flags(root / "data" / "benchmark" / "flags.yaml")
    return (
        facts,
        verified,
        split_map,
        build_items(verified, facts, registry, chunks, split_map, flags),
    )


def test_split_is_by_scheme_deterministic_and_balanced(root: Path) -> None:
    facts, _, split_map, items = _build(root)
    assert split_map == assign_schemes(facts)  # same seed, same result
    dev_schemes = {s for s, v in split_map.items() if v == "dev"}
    test_schemes = {s for s, v in split_map.items() if v == "test"}
    assert dev_schemes and test_schemes and not dev_schemes & test_schemes
    by_split: dict[str, set[str]] = {"dev": set(), "test": set()}
    for i in items:
        by_split[i.split].add(i.fact_id)
    assert not by_split["dev"] & by_split["test"]
    assert 10 <= len(by_split["dev"]) <= 18
    kinds_dev = {f.kind for f in facts if f.id in by_split["dev"]}
    assert kinds_dev == {f.kind for f in facts}  # dev sees every kind of fact


def test_every_verified_item_lands_in_exactly_one_split(root: Path) -> None:
    _, verified, _, items = _build(root)
    kept = {v.item_id for v in verified if v.status == "verified"}
    assert {i.item_id for i in items} == kept
    assert len(items) == len(kept)


def test_flags_reach_the_items(root: Path) -> None:
    _, _, _, items = _build(root)
    by_id = {i.item_id: i for i in items}
    assert not by_id["pmuy-refills-per-year/direct"].confirmatory
    assert not by_id["tds-rent-threshold/scenario"].confirmatory
    assert by_id["tds-rent-threshold/direct"].confirmatory
    assert any("Time-limited" in f for f in by_id["msp-kharif-tur/direct"].flags)


def _sandbox(root: Path, tmp_path: Path) -> Path:
    for rel in ("data/facts.yaml", "data/schemes.yaml", "data/processed/chunks.jsonl"):
        dest = tmp_path / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(root / rel, dest)
    verification = tmp_path / "data" / "benchmark" / "verification"
    verification.mkdir(parents=True)
    shutil.copy(root / "data/benchmark/verification/verified.jsonl", verification)
    return tmp_path


def test_test_split_is_locked_checksummed_and_never_refrozen(root: Path, tmp_path: Path) -> None:
    sandbox = _sandbox(root, tmp_path)
    _, _, split_map, items = _build(sandbox)
    record = freeze(sandbox, items, split_map, 1)
    assert record["test_items"] == sum(i.split == "test" for i in items)

    with pytest.raises(TestSplitLocked, match="--final"):
        load_items(sandbox, "test")
    assert len(load_items(sandbox, "dev")) == record["dev_items"]
    assert len(load_items(sandbox, "test", final=True)) == record["test_items"]

    with pytest.raises(FrozenSplitError, match="already frozen"):
        freeze(sandbox, items, split_map, 1)

    test_file = sandbox / "data" / "benchmark" / "test" / "items.jsonl"
    test_file.write_text(test_file.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    with pytest.raises(FrozenSplitError, match="checksum"):
        load_items(sandbox, "test", final=True)


def test_unknown_split_is_rejected(root: Path) -> None:
    with pytest.raises(ValueError, match="unknown split"):
        load_items(root, "all", final=True)  # type: ignore[arg-type]
