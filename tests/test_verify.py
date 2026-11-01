import csv
from pathlib import Path

from policydrift.bench.drafts import DraftItem
from policydrift.bench.facts import Fact, load_facts
from policydrift.bench.verify import export_review_sheet, import_review_sheet
from policydrift.ingest.registry import load_registry

FACT_ID = "pmuy-subsidy-per-cylinder"  # 200 -> 300 rupees


def _drafts() -> list[DraftItem]:
    qs = {"en": "What is the subsidy per cylinder?", "hi": "सब्सिडी कितनी है?", "gu": "સબસિડી કેટલી?"}
    return [
        DraftItem(item_id=f"{FACT_ID}/{s}", fact_id=FACT_ID, style=s, questions=qs, drafter="t:m")
        for s in ("direct", "scenario", "helpline")
    ]


def _facts(root: Path) -> list[Fact]:
    return load_facts(root / "data" / "facts.yaml")


def _sheet(root: Path, tmp_path: Path, edits: dict[str, dict[str, str]]) -> Path:
    path = tmp_path / "sheet.csv"
    export_review_sheet(
        _drafts(), _facts(root), load_registry(root / "data" / "schemes.yaml"), path
    )
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
        names = list(rows[0])
    for row in rows:
        row.update(edits.get(row["item_id"], {}))
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=names)
        writer.writeheader()
        writer.writerows(rows)
    return path


GOOD = {"en_ok": "Y", "hi_ok": "Y", "gu_ok": "Y", "include": "Y", "reviewer": "aditya"}


def test_export_shows_gold_and_source_to_the_reviewer(root: Path, tmp_path: Path) -> None:
    path = _sheet(root, tmp_path, {})
    with path.open(encoding="utf-8-sig", newline="") as f:
        row = next(csv.DictReader(f))
    assert row["gold_current"].startswith("300") and row["gold_old"].startswith("200")
    assert "₹300" in row["source_quote"] and row["hi"] == "सब्सिडी कितनी है?"
    assert row["include"] == ""


def test_round_trip_ok_fix_reject_and_pending(root: Path, tmp_path: Path) -> None:
    f = FACT_ID
    sheet = _sheet(
        root,
        tmp_path,
        {
            f"{f}/direct": GOOD,
            f"{f}/scenario": {**GOOD, "gu_ok": "N", "gu_fix": "સિલિન્ડર દીઠ સબસિડી કેટલી છે?"},
            # helpline left blank: stays pending
        },
    )
    items, report = import_review_sheet(sheet, _drafts(), _facts(root))
    assert (report.verified, report.rejected, report.pending) == (2, 0, [f"{f}/helpline"])
    assert report.problems == []
    scenario = next(i for i in items if i.style == "scenario")
    assert scenario.lang_status["gu"] == "fixed" and scenario.questions["gu"].startswith("સિલિન્ડર")
    assert scenario.questions["en"] == "What is the subsidy per cylinder?"


def test_bad_rows_are_reported_not_guessed(root: Path, tmp_path: Path) -> None:
    f = FACT_ID
    sheet = _sheet(
        root,
        tmp_path,
        {
            f"{f}/direct": {**GOOD, "en_ok": "N"},  # N without a fix
            f"{f}/scenario": {**GOOD, "reviewer": ""},
            f"{f}/helpline": {**GOOD, "en_ok": "N", "en_fix": "Is the subsidy Rs.300?"},  # leak
        },
    )
    items, report = import_review_sheet(sheet, _drafts(), _facts(root))
    assert items == []
    joined = " ".join(report.problems)
    assert "en_ok must be" in joined and "reviewer name" in joined and "reveals" in joined


def test_premise_rejection_and_unsure_language(root: Path, tmp_path: Path) -> None:
    f = FACT_ID
    sheet = _sheet(
        root,
        tmp_path,
        {
            f"{f}/direct": {**GOOD, "premise_ok": "N", "notes": "scheme was renamed"},
            f"{f}/scenario": {**GOOD, "gu_ok": "?"},
            f"{f}/helpline": {"include": "N", "reviewer": "aditya"},
        },
    )
    items, report = import_review_sheet(sheet, _drafts(), _facts(root))
    status = {i.style: i.status for i in items}
    assert status == {"direct": "rejected", "scenario": "verified", "helpline": "rejected"}
    assert next(i for i in items if i.style == "scenario").lang_status["gu"] == "unsure"
    assert report.problems == []
