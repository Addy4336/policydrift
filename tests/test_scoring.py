# ruff: noqa: RUF001
import pytest

from policydrift.scoring.agreement import cohen_kappa
from policydrift.scoring.judge import parse_judgement
from policydrift.scoring.matcher import score_answer
from policydrift.scoring.numbers import extract_numbers
from policydrift.scoring.pipeline import describe_value, knowledge_state


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("The limit is Rs. 3,50,000 per year.", [350000.0]),
        ("₹3.5 lakh", [350000.0]),
        ("सीमा ३,५०,००० रुपये है", [350000.0]),
        ("મર્યાદા ₹૩.૫ લાખ છે", [350000.0]),
        ("12.5% on gains", [12.5]),
        ("करोड़ 1.5 करोड़ रुपये", [15000000.0]),
        ("Effective 23 July 2024, FY 2024-25: ₹1,25,000.", [125000.0]),
        ("Section 112A applies; limit 1.25 lakh.", [125000.0]),
        ("1. First point\n2. Second point: 4 years", [4.0]),
        ("૨૦૨૪-૨૫ માં ૪ વર્ષ", [4.0]),
    ],
)
def test_extract_numbers(text: str, expected: list[float]) -> None:
    assert extract_numbers(text) == expected


def test_matcher_labels_current_outdated_other_and_refusal() -> None:
    assert score_answer("The limit is Rs 1,25,000.", 100000, 125000).label == "current"
    assert score_answer("आपकी सीमा १ लाख रुपये है।", 100000, 125000).label == "outdated"
    assert score_answer("The limit is 90,000.", 100000, 125000).label == "other"
    assert score_answer("The passages do not specify the amount.", 100000, 125000).label == (
        "refusal"
    )
    assert score_answer("માહિતી ઉપલબ્ધ નથી.", 100000, 125000).label == "refusal"


def test_matcher_defers_ambiguous_answers_to_the_judge() -> None:
    both = score_answer("It was ₹1 lakh, now ₹1.25 lakh.", 100000, 125000)
    assert both.label is None and "both" in both.reason
    words = score_answer("About four years.", 2, 5)
    assert words.label is None
    assert score_answer("No idea.", 2, 5).label is None


def test_matcher_reads_zero_as_nil_or_exempt() -> None:
    assert score_answer("GST is nil on this item.", 5, 0).label == "current"
    assert score_answer("5% GST applies.", 5, 0).label == "outdated"


def test_judge_reply_parsing() -> None:
    assert parse_judgement('{"commits_to": "A"}') == "A"
    assert parse_judgement('Sure: {"commits_to": "refusal"} done') == "refusal"
    assert parse_judgement("A") is None
    assert parse_judgement('{"commits_to": "maybe"}') is None


def test_cohen_kappa() -> None:
    same = ["current", "outdated", "other", "current"]
    assert cohen_kappa(same, same) == 1.0
    assert cohen_kappa(["a", "a", "b", "b"], ["a", "b", "a", "b"]) == 0.0
    with pytest.raises(ValueError, match="equally long"):
        cohen_kappa(["a"], [])


def test_describe_value_and_knowledge_state() -> None:
    assert describe_value("inr", 350000) == "₹3,50,000"
    assert describe_value("percent", 12.5) == "12.5%"
    assert describe_value("years", 4) == "4 years"
    assert knowledge_state("outdated") == "knows_old"
    assert knowledge_state("current") == "knows_current"
    assert knowledge_state("refusal") == "neither"
