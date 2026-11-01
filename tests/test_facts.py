from pathlib import Path

import pytest

from policydrift.bench.facts import Evidence, Fact, FactValue, load_facts, validate_facts
from policydrift.bench.forms import (
    amount_forms,
    count_forms,
    indian_grouping,
    percent_forms,
    to_script,
)
from policydrift.ingest.registry import load_registry
from policydrift.retrieval.search import load_chunks


def load_registry_ids() -> list[str]:
    return list(load_registry(Path(__file__).resolve().parents[1] / "data" / "schemes.yaml"))


@pytest.fixture
def facts(root: Path) -> list[Fact]:
    return load_facts(root / "data" / "facts.yaml")


def test_shipped_facts_are_consistent_with_sources_and_registry(
    root: Path, facts: list[Fact]
) -> None:
    chunks = load_chunks(root / "data" / "processed" / "chunks.jsonl")
    registry = load_registry(root / "data" / "schemes.yaml")
    assert validate_facts(facts, chunks, registry) == []


def test_numeric_schemes_have_facts_and_all_kinds_are_covered(facts: list[Fact]) -> None:
    assert len(facts) >= 30
    # pmjay-senior is deliberately absent: its change (everyone aged 70+ is eligible regardless
    # of income) is categorical, and the Phase 3 scorer is built for numeric answers.
    assert {f.scheme for f in facts} == set(load_registry_ids()) - {"pmjay-senior"}
    assert {f.kind for f in facts} == {"inr", "count", "days", "years", "months", "percent"}


def test_restated_facts_are_flagged(facts: list[Fact]) -> None:
    restated = {f.id for f in facts if f.old.evidence_kind == "restated"}
    assert {"mis-single-account-limit", "mis-joint-account-limit"} <= restated
    # GST item rates are restated by construction: the 2017 release gives no item rates.
    assert {f.id for f in facts if f.scheme == "gst"} <= restated
    assert not any(f.current.evidence_kind == "restated" for f in facts)


def _fact(**changes: object) -> Fact:
    base = Fact(
        id="f",
        scheme="pmuy-subsidy",
        attribute="x",
        kind="inr",
        old=FactValue(
            version="v1",
            value=200,
            evidence=[
                Evidence(chunk_id="pmuy-subsidy:v1:en:1910516:000", quote="Rs.200 per 14.2 kg")
            ],
        ),
        current=FactValue(
            version="v4",
            value=300,
            evidence=[
                Evidence(
                    chunk_id="pmuy-subsidy:v4:en:2269944:002", quote="transfer of ₹300 a cylinder"
                )
            ],
        ),
        changed_in="v2",
    )
    return base.model_copy(update=changes)


def test_validator_catches_a_wrong_value_a_bad_quote_and_a_wrong_version(root: Path) -> None:
    chunks = load_chunks(root / "data" / "processed" / "chunks.jsonl")
    registry = load_registry(root / "data" / "schemes.yaml")
    assert validate_facts([_fact()], chunks, registry) == []

    wrong_value = _fact().model_copy(
        update={"current": _fact().current.model_copy(update={"value": 350})}
    )
    assert any(
        "does not appear in quote" in p for p in validate_facts([wrong_value], chunks, registry)
    )

    bad_quote = _fact().model_copy(
        update={
            "old": _fact().old.model_copy(
                update={
                    "evidence": [
                        Evidence(chunk_id="pmuy-subsidy:v1:en:1910516:000", quote="Rs.999")
                    ]
                }
            )
        }
    )
    assert any("quote not found" in p for p in validate_facts([bad_quote], chunks, registry))

    wrong_version = _fact().model_copy(
        update={"old": _fact().old.model_copy(update={"version": "v2"})}
    )
    assert any(
        "expected pmuy-subsidy/v2" in p for p in validate_facts([wrong_version], chunks, registry)
    )

    same = _fact().model_copy(update={"current": _fact().current.model_copy(update={"value": 200})})
    assert any("values are equal" in p for p in validate_facts([same], chunks, registry))

    stale_current = _fact().model_copy(update={"current": _fact().old})
    assert any("must precede" in p for p in validate_facts([stale_current], chunks, registry))


def test_indian_grouping() -> None:
    assert indian_grouping(350000) == "3,50,000"
    assert indian_grouping(1500000) == "15,00,000"
    assert indian_grouping(15000) == "15,000"
    assert indian_grouping(999) == "999"
    assert indian_grouping(12345678) == "1,23,45,678"


def test_amount_forms_in_three_languages() -> None:
    en = amount_forms(350000, "en")
    assert {"3,50,000", "350000", "3.5 lakh", "₹3.5 lakh", "Rs. 3.5 lakh", "3.50 lakh"} <= set(en)
    hi = amount_forms(350000, "hi")
    assert {"3.5 लाख", "३,५०,०००", "३.५ लाख"} <= set(hi)  # noqa: RUF001
    gu = amount_forms(350000, "gu")
    assert {"3.5 લાખ", "૩,૫૦,૦૦૦", "₹૩.૫ લાખ"} <= set(gu)  # noqa: RUF001
    assert "10 lakh" in amount_forms(1000000, "en") and "10 lakh" not in amount_forms(900000, "en")
    assert "15,000" in amount_forms(15000, "en") and not any(
        "lakh" in f for f in amount_forms(15000)
    )


def test_count_forms_and_digit_conversion() -> None:
    assert count_forms(9, "en") == ["9"]
    assert count_forms(9, "hi") == ["9", "९"]
    assert count_forms(125, "gu") == ["125", "૧૨૫"]
    assert to_script("2024-25", "hi") == "२०२४-२५"


def test_percent_forms_handle_fractions_and_scripts() -> None:
    en = percent_forms(12.5, "en")
    assert {"12.5", "12.5%", "12.5 per cent", "12.5 percent"} <= set(en)
    assert "12.50" not in en
    assert {"12.5 ટકા", "૧૨.૫ ટકા"} <= set(percent_forms(12.5, "gu"))
    hi = percent_forms(20, "hi")
    assert {"20 प्रतिशत", "२० प्रतिशत", "२०%"} <= set(hi)
    gu = percent_forms(5, "gu")
    assert {"5 ટકા", "૫ ટકા"} <= set(gu)
    assert "5" in percent_forms(5, "en")
