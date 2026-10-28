from datetime import date
from pathlib import Path

from policydrift.ingest.manifest import load_manifest
from policydrift.ingest.registry import Scheme, Version, load_registry, validate_registry


def test_registry_timelines_are_contiguous(root: Path) -> None:
    assert validate_registry(load_registry(root / "data" / "schemes.yaml")) == []


def test_every_manifest_entry_has_a_registered_version(root: Path) -> None:
    registry = load_registry(root / "data" / "schemes.yaml")
    for s in load_manifest(root / "data" / "raw" / "manifest.jsonl"):
        assert s.version in {v.id for v in registry[s.scheme].versions}, s.path


def test_version_in_force_on_a_date(root: Path) -> None:
    registry = load_registry(root / "data" / "schemes.yaml")
    tax = registry["income-tax-new-regime"]
    assert tax.in_force_on(date(2024, 3, 31)) == tax.version("fy2023-24")
    assert tax.in_force_on(date(2024, 4, 1)) == tax.version("fy2024-25")
    assert tax.in_force_on(date(2026, 10, 28)) == tax.version("fy2025-26")
    jobs = registry["rural-employment-guarantee"]
    assert jobs.in_force_on(date(2026, 6, 30)) == jobs.version("v1")
    assert jobs.in_force_on(date(2026, 7, 1)) == jobs.version("v2")


def _scheme(*versions: Version) -> dict[str, Scheme]:
    return {"s": Scheme(name="S", versions=list(versions))}


def test_gap_between_versions_is_reported() -> None:
    reg = _scheme(
        Version(id="a", effective_from=date(2020, 1, 1), effective_to=date(2020, 12, 31)),
        Version(id="b", effective_from=date(2021, 1, 2), effective_to=None),
    )
    assert validate_registry(reg) == ["s/b: must start the day after a ends"]


def test_open_ended_version_must_be_last() -> None:
    reg = _scheme(
        Version(id="a", effective_from=date(2020, 1, 1), effective_to=None),
        Version(id="b", effective_from=date(2021, 1, 1), effective_to=None),
    )
    problems = validate_registry(reg)
    assert "s/a: only the last version may be open-ended" in problems


def test_inverted_window_is_reported() -> None:
    reg = _scheme(Version(id="a", effective_from=date(2021, 1, 1), effective_to=date(2020, 1, 1)))
    assert validate_registry(reg) == ["s/a: effective_from is after effective_to"]
