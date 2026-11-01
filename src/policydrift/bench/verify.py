"""Human verification of drafted questions (milestone 2d): export a CSV, import the reviewed one.

The sheet shows the reviewer the gold answer and its source quote next to each draft, so they
can judge whether the question asks about that fact and nothing else. Reviewer columns:

- ``<lang>_ok``: Y (wording is right), N (wrong; give a fix), ? (cannot judge this language).
- ``<lang>_fix``: replacement wording, required when ``<lang>_ok`` is N.
- ``premise_ok``: Y/N. N means the question presupposes something false (a renamed scheme, an
  ambiguous quantity), so the whole item is rejected.
- ``include``: Y keeps the item, N drops it.
"""

from __future__ import annotations

import csv
from collections.abc import Sequence
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict

from policydrift.bench.drafts import LANGS, DraftItem, find_leaks
from policydrift.bench.facts import Fact
from policydrift.ingest.registry import Registry

REVIEW_FIELDS = (
    *[f"{lang}_{kind}" for lang in LANGS for kind in ("ok", "fix")],
    "premise_ok",
    "include",
    "reviewer",
    "notes",
)
INFO_FIELDS = (
    "item_id",
    "scheme",
    "style",
    "asks_about",
    "gold_current",
    "gold_old",
    "source_quote",
    "en",
    "hi",
    "gu",
)
LangStatus = Literal["ok", "fixed", "unsure"]


class VerifiedItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_id: str
    fact_id: str
    style: str
    questions: dict[str, str]  # final wording after fixes
    lang_status: dict[str, LangStatus]
    status: Literal["verified", "rejected"]
    reviewer: str
    notes: str = ""
    drafter: str
    leaks: list[str] = []


class ImportReport(BaseModel):
    verified: int = 0
    rejected: int = 0
    pending: list[str] = []
    problems: list[str] = []


def export_review_sheet(
    drafts: Sequence[DraftItem], facts: Sequence[Fact], registry: Registry, path: Path
) -> None:
    by_fact = {f.id: f for f in facts}
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[*INFO_FIELDS, *REVIEW_FIELDS])
        writer.writeheader()
        for d in drafts:
            fact = by_fact[d.fact_id]
            writer.writerow(
                {
                    "item_id": d.item_id,
                    "scheme": registry[fact.scheme].name,
                    "style": d.style,
                    "asks_about": fact.attribute,
                    "gold_current": f"{fact.current.value} ({fact.current.version})",
                    "gold_old": f"{fact.old.value} ({fact.old.version})",
                    "source_quote": fact.current.evidence[0].quote.replace("\n\n", " | "),
                    **d.questions,
                }
            )


def _norm(value: str | None) -> str:
    return (value or "").strip()


def import_review_sheet(
    path: Path, drafts: Sequence[DraftItem], facts: Sequence[Fact]
) -> tuple[list[VerifiedItem], ImportReport]:
    """Read a reviewed sheet. Rows left blank stay pending; bad rows are reported, not guessed."""
    by_id = {d.item_id: d for d in drafts}
    by_fact = {f.id: f for f in facts}
    report = ImportReport()
    items: list[VerifiedItem] = []
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        item_id = _norm(row.get("item_id"))
        draft = by_id.get(item_id)
        if draft is None:
            report.problems.append(f"{item_id or '<blank>'}: not a known draft")
            continue
        include = _norm(row.get("include")).upper()
        if include == "":
            report.pending.append(item_id)
            continue
        if include not in {"Y", "N"}:
            report.problems.append(f"{item_id}: include must be Y or N, got {include!r}")
            continue
        reviewer = _norm(row.get("reviewer"))
        if not reviewer:
            report.problems.append(f"{item_id}: reviewer name is required")
            continue
        premise = _norm(row.get("premise_ok")).upper() or "Y"
        questions = dict(draft.questions)
        statuses: dict[str, LangStatus] = {}
        problem = False
        for lang in LANGS:
            ok = _norm(row.get(f"{lang}_ok")).upper()
            fix = _norm(row.get(f"{lang}_fix"))
            if ok == "Y":
                statuses[lang] = "ok"
            elif ok == "N" and fix:
                questions[lang] = fix
                statuses[lang] = "fixed"
            elif ok == "?":
                statuses[lang] = "unsure"
            elif include == "Y":
                report.problems.append(f"{item_id}: {lang}_ok must be Y, N with a fix, or ?")
                problem = True
            else:
                statuses[lang] = "unsure"
        if problem:
            continue
        rejected = include == "N" or premise == "N"
        leaks = find_leaks(by_fact[draft.fact_id], questions)
        if leaks and not rejected:
            report.problems.append(f"{item_id}: wording reveals an answer value in {leaks}")
            continue
        items.append(
            VerifiedItem(
                item_id=item_id,
                fact_id=draft.fact_id,
                style=draft.style,
                questions=questions,
                lang_status=statuses,
                status="rejected" if rejected else "verified",
                reviewer=reviewer,
                notes=_norm(row.get("notes")),
                drafter=draft.drafter,
                leaks=leaks,
            )
        )
        if rejected:
            report.rejected += 1
        else:
            report.verified += 1
    return items, report


def write_verified(items: Sequence[VerifiedItem], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for item in items:
            f.write(item.model_dump_json() + "\n")
