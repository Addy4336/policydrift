from datetime import date

import pytest

from policydrift.agents.mitigations import (
    parse_check,
    run_conflict_checker,
    show_dates_for,
    system_for,
)
from policydrift.experiments.config import ExperimentConfig
from policydrift.experiments.prompts import SYSTEM
from policydrift.llm import LLMRequest, LLMResponse

TODAY = date(2026, 11, 1)


def _reply(text: str, tokens: int = 10, cached: bool = False) -> LLMResponse:
    return LLMResponse(
        text=text,
        provider="groq",
        model="m",
        input_tokens=tokens,
        output_tokens=tokens,
        latency_s=1.0,
        cached=cached,
    )


def _make(system: str, prompt: str) -> LLMRequest:
    return LLMRequest(provider="groq", model="m", system=system, prompt=prompt)


def test_prompt_wording_per_mitigation() -> None:
    assert system_for("none", TODAY) == SYSTEM
    assert system_for("M-c", TODAY) == SYSTEM
    assert "2026-11-01" in system_for("M-a1", TODAY) and "in force today" in system_for(
        "M-a1", TODAY
    )
    assert "labelled with the period" in system_for("M-a2", TODAY)
    assert show_dates_for("M-a2", False) is True
    assert show_dates_for("none", False) is False and show_dates_for("M-a1", True) is True


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ('{"consistent": true}', (True, "")),
        (
            'Sure: {"consistent": false, "reason": "uses the 2019 limit"}',
            (False, "uses the 2019 limit"),
        ),
        ('{"consistent": "yes"}', (None, "")),
        ("no json here", (None, "")),
        ("{broken", (None, "")),
    ],
)
def test_parse_check(text: str, expected: tuple[bool | None, str]) -> None:
    assert parse_check(text) == expected


def _run(replies: list[str]) -> tuple[object, list[LLMRequest]]:
    seen: list[LLMRequest] = []
    queue = iter(replies)

    def ask(request: LLMRequest) -> LLMResponse:
        seen.append(request)
        return _reply(next(queue))

    out = run_conflict_checker(ask, _make, "What is the limit?", [], False, TODAY)
    return out, seen


def test_conflict_checker_keeps_a_consistent_draft() -> None:
    out, seen = _run(["Rs 1,25,000", '{"consistent": true}'])
    assert out.final.text == "Rs 1,25,000" and out.calls == 2 and out.verdict == "consistent"  # type: ignore[attr-defined]
    assert len(seen) == 2 and "Draft answer: Rs 1,25,000" in seen[1].prompt


def test_conflict_checker_revises_a_stale_draft() -> None:
    out, seen = _run(["Rs 1 lakh", '{"consistent": false, "reason": "old limit"}', "Rs 1.25 lakh"])
    assert out.final.text == "Rs 1.25 lakh" and out.draft == "Rs 1 lakh"  # type: ignore[attr-defined]
    assert out.calls == 3 and out.verdict == "revised" and out.input_tokens == 30  # type: ignore[attr-defined]
    assert "old limit" in seen[2].prompt and "2026-11-01" in (seen[2].system or "")


def test_conflict_checker_keeps_the_draft_when_the_check_is_unreadable() -> None:
    out, _ = _run(["Rs 1 lakh", "I think it is fine"])
    assert out.final.text == "Rs 1 lakh" and out.verdict == "unparsed"  # type: ignore[attr-defined]


def test_mitigations_are_limited_to_r1_and_r3() -> None:
    with pytest.raises(ValueError, match="only defined"):
        ExperimentConfig(name="t", models=["m"], conditions=["R1", "R2"], mitigation="M-a1")
    ok = ExperimentConfig(name="t", models=["m"], conditions=["R1", "R3"], mitigation="M-b")
    assert ok.as_of == TODAY
