"""Version registry: which rule version was in force when (``data/schemes.yaml``)."""

from __future__ import annotations

from datetime import date, timedelta
from itertools import pairwise
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict


class Version(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    effective_from: date | None
    effective_to: date | None
    announced_on: date | None = None
    notes: str | None = None

    def in_force_on(self, day: date) -> bool:
        starts_ok = self.effective_from is None or self.effective_from <= day
        ends_ok = self.effective_to is None or day <= self.effective_to
        return starts_ok and ends_ok


class Scheme(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    question_name: str | None = None  # how questions should refer to it; defaults to name
    versions: list[Version]

    def version(self, version_id: str) -> Version:
        for v in self.versions:
            if v.id == version_id:
                return v
        raise KeyError(version_id)

    def in_force_on(self, day: date) -> Version | None:
        matches = [v for v in self.versions if v.in_force_on(day)]
        return matches[0] if len(matches) == 1 else None


Registry = dict[str, Scheme]


def load_registry(path: Path) -> Registry:
    with path.open(encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return {scheme_id: Scheme.model_validate(body) for scheme_id, body in raw.items()}


def validate_registry(registry: Registry) -> list[str]:
    """Check that each scheme's versions form one contiguous, non-overlapping timeline."""
    problems: list[str] = []
    for scheme_id, scheme in registry.items():
        versions = scheme.versions
        if not versions:
            problems.append(f"{scheme_id}: no versions")
            continue
        ids = [v.id for v in versions]
        if len(set(ids)) != len(ids):
            problems.append(f"{scheme_id}: duplicate version ids")
        for v in versions:
            if v.effective_from and v.effective_to and v.effective_from > v.effective_to:
                problems.append(f"{scheme_id}/{v.id}: effective_from is after effective_to")
        for v in versions[:-1]:
            if v.effective_to is None:
                problems.append(f"{scheme_id}/{v.id}: only the last version may be open-ended")
        for earlier, later in pairwise(versions):
            if earlier.effective_to is None or later.effective_from is None:
                problems.append(f"{scheme_id}/{later.id}: boundary with previous version is unset")
            elif later.effective_from != earlier.effective_to + timedelta(days=1):
                problems.append(
                    f"{scheme_id}/{later.id}: must start the day after {earlier.id} ends"
                )
    return problems
