"""Citation validation for generated answers.

An answer cites passages with markers such as ``[1]`` or ``[2, 3]``. Validation checks that:

- every marker points at a passage that was actually shown to the model,
- the answer cites at least one passage (unless it says the passages do not answer it),
- every figure in the answer appears in at least one cited passage.

The figure check reuses the benchmark's number normaliser, so lakh/crore wording and Devanagari
or Gujarati digits are compared as numbers.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, field

from policydrift.scoring.matcher import same_value
from policydrift.scoring.numbers import extract_numbers, normalise_digits

_MARKER = re.compile(r"\[(\s*\d+(?:\s*[,;]\s*\d+)*\s*)\]")


@dataclass(frozen=True)
class NumberCheck:
    value: str  # the number as normalised from the answer
    verified: bool  # found in at least one cited passage
    cited_in: list[int]  # passage ids whose text contains it


@dataclass(frozen=True)
class CitationReport:
    cited: list[int]  # valid passage ids cited, in order of first appearance
    invalid_markers: list[int]  # ids cited that were not shown to the model
    uncited: bool  # the answer states something but cites nothing
    numbers: list[NumberCheck] = field(default_factory=list)

    @property
    def citations_valid(self) -> bool:
        return not self.invalid_markers and not self.uncited

    @property
    def numbers_verified(self) -> bool:
        return all(n.verified for n in self.numbers)


_ODD_MARKER = re.compile(r"[【\[]\s*(\d+(?:\s*[,;]\s*\d+)*)\s*(?:†[^】\]]*)?[】\]]")


def normalise_markers(answer: str) -> str:
    """Rewrite marker styles some models emit (``【4】``, ``[4†source]``) as ``[4]``."""
    return _ODD_MARKER.sub(lambda m: f"[{m.group(1)}]", answer)


def cited_ids(answer: str) -> list[int]:
    """Passage ids in citation markers, in order of first appearance, without repeats."""
    seen: list[int] = []
    for group in _MARKER.findall(answer):
        for part in re.split(r"[,;]", group):
            n = int(part.strip())
            if n not in seen:
                seen.append(n)
    return seen


_DATES = re.compile(
    r"\b\d{1,2}\s+[^\W\d_]+\.?,?\s+(?:19|20)\d{2}\b"  # 24 October 2024, 24 अक्टूबर 2024
    r"|\b(?:19|20)\d{2}[-‑]\d{2}[-‑]\d{2}\b"  # noqa: RUF001  (2024-10-24, also with non-breaking hyphens)
    r"|\b(?:19|20)\d{2}\s*[-‐‑‒–/]\s*\d{2,4}\b"  # noqa: RUF001  (2024-25, 2025/26, en dash)
    r"|\b(?:19|20)\d{2}\b"  # a bare year
)


def strip_markers(answer: str) -> str:
    """The answer without citation markers and dates (for checking figures)."""
    return _DATES.sub(" ", _MARKER.sub(" ", answer))


def _format(value: float) -> str:
    return f"{value:,.0f}" if value == int(value) else f"{value:,.2f}".rstrip("0").rstrip(".")


def validate(
    answer: str, passages: Sequence[str], *, says_no_answer: bool = False
) -> CitationReport:
    """Check ``answer`` against the passages it was given (``passages[i]`` has id ``i + 1``)."""
    answer = normalise_markers(answer)
    ids = cited_ids(normalise_digits(answer))
    valid = [i for i in ids if 1 <= i <= len(passages)]
    invalid = [i for i in ids if not 1 <= i <= len(passages)]
    body = strip_markers(normalise_digits(answer))
    numbers: list[NumberCheck] = []
    targets = valid or list(range(1, len(passages) + 1))  # uncited: look in every passage
    passage_numbers = {i: extract_numbers(passages[i - 1]) for i in targets}
    seen: set[float] = set()
    for value in extract_numbers(body):
        if value in seen:
            continue
        seen.add(value)
        hits = [i for i in targets if any(same_value(n, value) for n in passage_numbers[i])]
        numbers.append(
            NumberCheck(value=_format(value), verified=bool(hits and valid), cited_in=hits)
        )
    uncited = not valid and not says_no_answer and bool(answer.strip())
    return CitationReport(cited=valid, invalid_markers=invalid, uncited=uncited, numbers=numbers)
