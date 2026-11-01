"""Pull numeric values out of free text in English, Hindi and Gujarati.

Handles Devanagari and Gujarati digits, Indian digit grouping (3,50,000), lakh/crore/thousand
multipliers and percent signs. Dates and fiscal years are removed first so that "2024-25" or
"1 April 2026" never read as quantities.
"""

from __future__ import annotations

import re

_NATIVE_DIGITS = str.maketrans("०१२३४५६७८९૦૧૨૩૪૫૬૭૮૯", "01234567890123456789")

_MONTHS = (
    "january|february|march|april|may|june|july|august|september|october|november|december|"
    "jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec|"
    "जनवरी|फरवरी|मार्च|अप्रैल|मई|जून|जुलाई|अगस्त|सितंबर|सितम्बर|अक्टूबर|नवंबर|नवम्बर|दिसंबर|दिसम्बर|"
    "જાન્યુઆરી|ફેબ્રુઆરી|માર્ચ|એપ્રિલ|મે|જૂન|જુલાઈ|ઓગસ્ટ|સપ્ટેમ્બર|ઓક્ટોબર|નવેમ્બર|ડિસેમ્બર"
)
_DATE_PATTERNS = [
    re.compile(r"\b(?:19|20)\d{2}\s*[-–/]\s*(?:\d{4}|\d{2})\b"),  # 2024-25, 2024/2025  # noqa: RUF001
    re.compile(r"\b\d{1,2}\s*[-/.]\s*\d{1,2}\s*[-/.]\s*(?:19|20)?\d{2}\b"),  # 23-07-2024
    re.compile(
        rf"\b\d{{1,2}}(?:st|nd|rd|th)?\s+(?:{_MONTHS})\b(?:\s*,?\s*(?:19|20)\d{{2}})?", re.I
    ),
    re.compile(rf"\b(?:{_MONTHS})\s+\d{{1,2}}(?:st|nd|rd|th)?\s*,?\s*(?:19|20)\d{{2}}\b", re.I),
    re.compile(rf"\b(?:{_MONTHS})\s*,?\s*(?:19|20)\d{{2}}\b", re.I),
    re.compile(r"\b(?:FY|F\.Y\.|AY|A\.Y\.)\s*(?:19|20)\d{2}\b", re.I),
]
_LIST_MARKER = re.compile(r"(?m)^\s*(?:[-*•]\s*)?\(?\d{1,2}[.)]\s+")
_SECTION_REF = re.compile(
    r"\b(?:section|sec\.?|धारा|કલમ|ધારા|clause|article|rule)\s*\d+[A-Za-z]*(?:\(\w+\))*",
    re.I,
)

_MULTIPLIERS: dict[str, float] = {
    "lakh": 1e5,
    "lakhs": 1e5,
    "lac": 1e5,
    "lacs": 1e5,
    "लाख": 1e5,
    "લાખ": 1e5,
    "crore": 1e7,
    "crores": 1e7,
    "करोड़": 1e7,
    "करोड": 1e7,
    "કરોડ": 1e7,
    "thousand": 1e3,
    "हज़ार": 1e3,
    "हजार": 1e3,
    "હજાર": 1e3,
}
_UNIT = "|".join(sorted((re.escape(k) for k in _MULTIPLIERS), key=len, reverse=True))
_NUMBER = re.compile(
    rf"(?P<int>\d{{1,3}}(?:,\d{{2,3}})+|\d+)(?:\.(?P<frac>\d+))?(?:\s*(?P<mult>{_UNIT})(?![\w]))?",
    re.I,
)

NUMBER_WORDS = re.compile(
    r"\b(?:zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|fifteen|"
    r"twenty|thirty|fifty|hundred|thousand|lakh|lakhs|crore)\b",
    re.I,
)

_ZERO_WORDS = re.compile(
    r"\b(?:nil|zero|exempt(?:ed|ion)?|no\s+(?:gst|tax|duty))\b|शून्य|शुन्य|કર\s*મુક્ત|શૂન્ય|छूट",
    re.I,
)


def normalise_digits(text: str) -> str:
    return text.translate(_NATIVE_DIGITS)


def strip_non_quantities(text: str) -> str:
    """Remove dates, fiscal years, list numbering and section references."""
    text = normalise_digits(text)
    for pattern in _DATE_PATTERNS:
        text = pattern.sub(" ", text)
    text = _SECTION_REF.sub(" ", text)
    return _LIST_MARKER.sub("", text)


def extract_numbers(text: str) -> list[float]:
    """All quantities in ``text`` as plain floats (3.5 lakh -> 350000.0)."""
    out: list[float] = []
    for m in _NUMBER.finditer(strip_non_quantities(text)):
        whole = m.group("int").replace(",", "")
        value = float(f"{whole}.{m.group('frac')}" if m.group("frac") else whole)
        mult = m.group("mult")
        if mult:
            value *= _MULTIPLIERS[mult.lower() if mult.isascii() else mult]
        out.append(value)
    return out


def mentions_zero(text: str) -> bool:
    return bool(_ZERO_WORDS.search(text))


def has_number_words(text: str) -> bool:
    return bool(NUMBER_WORDS.search(text))
