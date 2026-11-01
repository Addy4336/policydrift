"""Deterministic scoring: which of the old and current values does an answer state?

This is step 1 of the scoring order in the pre-registration. Answers it cannot decide
(both values, no recognisable number, number words) go to the LLM judge.
"""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict

from policydrift.scoring.numbers import extract_numbers, has_number_words, mentions_zero

Label = Literal["current", "outdated", "other", "refusal"]

_REFUSAL = re.compile(
    r"(?:cannot|can't|can not|unable to|not able to|do(?:es)? not (?:have|contain|specify|mention|"
    r"provide)|don't have|no (?:specific )?information|not (?:provided|mentioned|specified|"
    r"available|stated|found)|insufficient|i'm not sure|i am not sure|"
    r"जानकारी (?:उपलब्ध )?नहीं|उपलब्ध नहीं|नहीं बता|बताना संभव नहीं|उल्लेख नहीं|निर्दिष्ट नहीं|"
    r"માહિતી (?:ઉપલબ્ધ )?નથી|ઉપલબ્ધ નથી|જણાવી શકત|ઉલ્લેખ નથી|નિર્દિષ્ટ નથી)",
    re.I,
)


class Verdict(BaseModel):
    model_config = ConfigDict(frozen=True)

    label: Label | None  # None: undecided, send to the judge
    reason: str
    numbers: tuple[float, ...] = ()


def same_value(found: float, target: float) -> bool:
    return abs(found - target) <= max(0.005, 1e-9 * abs(target))


def score_answer(answer: str, old: float, current: float) -> Verdict:
    """Label ``answer`` by the old and current gold values."""
    numbers = extract_numbers(answer)
    has_old = any(same_value(n, old) for n in numbers) or (old == 0 and mentions_zero(answer))
    has_cur = any(same_value(n, current) for n in numbers) or (
        current == 0 and mentions_zero(answer)
    )
    nums = tuple(numbers)
    if has_old and has_cur:
        return Verdict(label=None, reason="states both values", numbers=nums)
    if has_cur:
        return Verdict(label="current", reason="states the current value", numbers=nums)
    if has_old:
        return Verdict(label="outdated", reason="states the old value", numbers=nums)
    if _REFUSAL.search(answer):
        return Verdict(label="refusal", reason="declines to give a value", numbers=nums)
    if numbers:
        return Verdict(label="other", reason="states a different number", numbers=nums)
    if has_number_words(answer):
        return Verdict(label=None, reason="number in words", numbers=nums)
    return Verdict(label=None, reason="no recognisable value", numbers=nums)
