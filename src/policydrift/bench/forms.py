"""Surface forms of numbers in English, Hindi and Gujarati.

Used to cross-check curated values against their source quotes now, and as the accepted
answer forms for the Phase 3 scorer later. Words such as "three and a half lakh" are not
generated; the scorer will treat unmatched answers as undecided rather than guess.
"""

from __future__ import annotations

_DIGITS = {
    "hi": str.maketrans("0123456789", "०१२३४५६७८९"),
    "gu": str.maketrans("0123456789", "૦૧૨૩૪૫૬૭૮૯"),
}
_LAKH = {"en": ("lakh", "lakhs", "Lakh", "Lakhs"), "hi": ("लाख",), "gu": ("લાખ",)}
_CRORE = {"en": ("crore", "Crore"), "hi": ("करोड़", "करोड"), "gu": ("કરોડ",)}
_CURRENCY = {
    "en": ("₹", "₹ ", "Rs.", "Rs. ", "Rs ", "INR "),
    "hi": ("₹", "₹ ", "रु.", "रुपये "),
    "gu": ("₹", "₹ ", "રૂ.", "રૂ. "),
}


def indian_grouping(n: int) -> str:
    """12345678 -> '1,23,45,678' (lakh/crore grouping)."""
    s = str(n)
    if len(s) <= 3:
        return s
    head, tail = s[:-3], s[-3:]
    groups: list[str] = []
    while len(head) > 2:
        groups.insert(0, head[-2:])
        head = head[:-2]
    if head:
        groups.insert(0, head)
    return ",".join([*groups, tail])


def to_script(text: str, lang: str) -> str:
    """Convert ASCII digits to the native digits of ``lang`` (no-op for English)."""
    table = _DIGITS.get(lang)
    return text.translate(table) if table else text


def _trim(x: float, places: int) -> str:
    return f"{x:.{places}f}".rstrip("0").rstrip(".")


def _scaled(value: int, unit: int) -> list[str]:
    scaled = value / unit
    forms = {_trim(scaled, 2), _trim(scaled, 1), f"{scaled:.2f}"}
    return sorted(f for f in forms if float(f) == scaled)


def amount_forms(value: int, lang: str = "en") -> list[str]:
    """Rupee amount as written in running text, with and without currency markers."""
    numbers: set[str] = {str(value), indian_grouping(value)}
    if value >= 100_000:
        numbers |= {f"{n} {w}" for n in _scaled(value, 100_000) for w in _LAKH[lang]}
        numbers |= {f"{n}{w}" for n in _scaled(value, 100_000) for w in _LAKH[lang]}
    if value >= 10_000_000:
        numbers |= {f"{n} {w}" for n in _scaled(value, 10_000_000) for w in _CRORE[lang]}
    forms = set(numbers)
    for prefix in _CURRENCY[lang]:
        forms |= {prefix + n for n in numbers}
    native = {to_script(f, lang) for f in forms} if lang != "en" else set()
    return sorted(forms | native)


def count_forms(value: int, lang: str = "en") -> list[str]:
    """A plain count (refills, days, years) in ASCII and native digits."""
    forms = {str(value), to_script(str(value), lang)}
    return sorted(forms)
