"""Pick the scheme a question is about, before retrieval.

Dense retrieval alone sometimes ranks a similar scheme first (a SVANidhi loan question can land
on Mudra loans), so a question that names a scheme, in English, Hindi or Gujarati or a common
misspelling, is routed to it by name. Otherwise the scheme with the highest summed similarity over
the top hits wins.
"""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Sequence

from policydrift.retrieval.search import Hit

ALIASES: dict[str, tuple[str, ...]] = {
    "pm-svanidhi": (
        "svanidhi",
        "swanidhi",
        "swarnidhi",
        "svnidhi",
        "street vendor",
        "स्वनिधि",
        "સ્વનિધિ",
        "રેકડી",
        "फेरीवाल",
    ),
    "pm-mudra": ("mudra", "मुद्रा", "મુદ્રા", "shishu", "kishore", "tarun"),
    "pmuy-subsidy": (
        "ujjwala",
        "उज्ज्वला",
        "ઉજ્જવલા",
        "lpg",
        "cylinder",
        "सिलेंडर",
        "સિલિન્ડર",
        "refill",
    ),
    "pmay-urban": ("awas", "आवास", "આવાસ", "pmay", "clss", "housing"),
    "pmjay-senior": ("pm-jay", "pmjay", "ayushman", "आयुष्मान", "આયુષ્માન", "vay vandana"),
    "rural-employment-guarantee": (
        "mgnrega",
        "nrega",
        "vb-g ram g",
        "rural employment",
        "मनरेगा",
        "રોજગાર",
        "रोजगार",
    ),
    "income-tax-new-regime": (
        "new tax regime",
        "new regime",
        "income tax slab",
        "rebate",
        "87a",
        "नई कर व्यवस्था",
        "નવી કર",
    ),
    "capital-gains": ("capital gain", "ltcg", "stcg", "112a", "111a", "पूंजीगत लाभ", "મૂડી લાભ"),
    "gst": ("gst", "जीएसटी", "જીએસટી", "goods and services tax"),
    "kcc-miss": ("kisan credit", "kcc", "interest subvention", "किसान क्रेडिट", "કિસાન ક્રેડિટ"),
    "msp-kharif": ("kharif", "खरीफ", "ખરીફ", "paddy", "धान", "ડાંગર"),
    "msp-rabi": ("rabi", "रबी", "રવી", "wheat", "गेहूं", "ઘઉં", "mustard"),
    "scss-mis": (
        "senior citizens savings",
        "scss",
        "monthly income scheme",
        "post office mis",
        "वरिष्ठ नागरिक बचत",
        "માસિક આવક",
    ),
    "nmmss": ("nmmss", "means-cum-merit", "means cum merit", "scholarship", "छात्रवृत्ति", "શિષ્યવૃત્તિ"),
}


def named_schemes(*texts: str) -> list[str]:
    """Schemes named in any of ``texts``, most mentions first."""
    blob = " ".join(texts).lower()
    counts = {
        scheme: sum(len(re.findall(re.escape(a.lower()), blob)) for a in aliases)
        for scheme, aliases in ALIASES.items()
    }
    return [s for s, n in sorted(counts.items(), key=lambda kv: -kv[1]) if n > 0]


def pick_scheme(hits: Sequence[Hit], *texts: str) -> str | None:
    named = named_schemes(*texts)
    if named:
        return named[0]
    if not hits:
        return None
    totals: dict[str, float] = defaultdict(float)
    for h in hits:
        totals[h.chunk.scheme] += h.score
    return max(totals, key=lambda s: totals[s])
