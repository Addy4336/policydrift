"""Parse captured PIB release text (normalisation ``pib-text-v1``) into header and body."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime

# "Posted On: 08 AUG 2025 4:00PM by PIB Delhi" and its Hindi and Gujarati equivalents.
_POSTED = re.compile(
    r"^(?:Posted On|प्रविष्टि तिथि|પોસ્ટેડ ઓન):\s*"
    r"(?P<date>\d{2} [A-Z]{3} \d{4})\s+(?P<time>\d{1,2}:\d{2}[AP]M)\s+by\s+(?P<by>.+)$"
)
_RELEASE_ID = re.compile(r"^\((?:Release ID|रिलीज़ आईडी|રીલીઝ આઈડી):\s*(?P<prid>\d+)\)$")

# Trailing sign-off lines that are not part of the release content.
_STARS = re.compile(r"^\*+$")
_INITIALS = re.compile(r"^[^.।?!]{1,60}/[^.।?!]{0,60}$")  # "MJPS/BM", "एमजी / एएम / आर/वाईबी"
_SHORT_CAPS = re.compile(r"^[A-Z]{2,6}$")  # "DS", "RKJ"
_BOILERPLATE_PREFIXES = (
    "Click here to see in PDF",
    "पीडीएफ में देखने के लिए यहां क्लिक करें",
    "સોશિયલ મીડિયા પર અમને ફોલો કરો",
)

_PRIVATE_USE = re.compile("[-]")
_LATIN_LIGATURES = re.compile("[ﬀ-ﬆ]")


@dataclass(frozen=True)
class PibRelease:
    ministry: str
    title: str
    posted_on: date
    posted_by: str
    prid: str
    body_start: int  # character offsets of the body within the captured text
    body_end: int


def parse_pib(text: str) -> PibRelease:
    """Split a captured release into header fields and the character span of its body."""
    lines = text.split("\n")
    offsets = _line_offsets(lines)

    posted_idx = next((i for i, line in enumerate(lines) if _POSTED.match(line)), None)
    if posted_idx is None:
        raise ValueError("no 'Posted On' line found")
    posted = _POSTED.match(lines[posted_idx])
    assert posted is not None

    last = _last_nonblank(lines, len(lines))
    release = _RELEASE_ID.match(lines[last]) if last is not None else None
    if release is None or last is None:
        raise ValueError("no Release ID line found at the end")

    end = last
    while True:
        prev = _last_nonblank(lines, end)
        if prev is None or prev <= posted_idx or not _is_signoff(lines[prev]):
            break
        end = prev
    body_last = _last_nonblank(lines, end)
    body_first = next((i for i in range(posted_idx + 1, len(lines)) if lines[i].strip()), None)
    if body_first is None or body_last is None or body_last < body_first:
        raise ValueError("empty release body")

    return PibRelease(
        ministry=lines[0],
        title=lines[1],
        posted_on=datetime.strptime(posted["date"].title(), "%d %b %Y").date(),
        posted_by=posted["by"],
        prid=release["prid"],
        body_start=offsets[body_first],
        body_end=offsets[body_last] + len(lines[body_last]),
    )


def clean_text(text: str) -> str:
    """Remove private-use bullets and expand Latin ligatures (e.g. U+FB01 'ﬁ' to 'fi')."""
    text = _PRIVATE_USE.sub("", text)
    text = _LATIN_LIGATURES.sub(lambda m: unicodedata.normalize("NFKC", m.group()), text)
    return "\n".join(line.strip() for line in text.split("\n"))


def _is_signoff(line: str) -> bool:
    return bool(
        _STARS.match(line)
        or _SHORT_CAPS.match(line)
        or _INITIALS.match(line)
        or line.startswith(_BOILERPLATE_PREFIXES)
    )


def _last_nonblank(lines: list[str], before: int) -> int | None:
    for i in range(before - 1, -1, -1):
        if lines[i].strip():
            return i
    return None


def _line_offsets(lines: list[str]) -> list[int]:
    offsets, pos = [], 0
    for line in lines:
        offsets.append(pos)
        pos += len(line) + 1
    return offsets
