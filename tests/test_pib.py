from datetime import date

import pytest

from policydrift.ingest.pib import clean_text, parse_pib

EN = """Ministry of Finance
Some Title

Subheading
Posted On: 01 FEB 2025 1:28PM by PIB Delhi

First paragraph.

Second paragraph.

*****

NB/VM

(Release ID: 2098406)
"""

GU = """નાણા મંત્રાલય
શીર્ષક
પોસ્ટેડ ઓન: 23 JUL 2024 1:14PM by PIB Ahmedabad

પહેલો ફકરો.

CB/GP/JD

સોશિયલ મીડિયા પર અમને ફોલો કરો : @PIBAhmedabad /pibahmedabad1964

(રીલીઝ આઈડી: 2035916)
"""

HI = """वित्त मंत्रालय
शीर्षक
प्रविष्टि तिथि: 29 OCT 2024 3:00PM by PIB Delhi

यह नई सीमा 24 अक्टूबर, 2024 को प्रभावी हुई।

पीडीएफ में देखने के लिए यहां क्लिक करें

***

एमजी / एएम / आर/वाईबी

(रिलीज़ आईडी: 2069230)
"""


def test_english_header_and_body() -> None:
    r = parse_pib(EN)
    assert (r.ministry, r.title, r.prid) == ("Ministry of Finance", "Some Title", "2098406")
    assert r.posted_on == date(2025, 2, 1)
    assert r.posted_by == "PIB Delhi"
    assert EN[r.body_start : r.body_end] == "First paragraph.\n\nSecond paragraph."


def test_gujarati_signoff_and_social_footer_are_excluded() -> None:
    r = parse_pib(GU)
    assert r.posted_on == date(2024, 7, 23)
    assert r.prid == "2035916"
    assert GU[r.body_start : r.body_end] == "પહેલો ફકરો."


def test_hindi_boilerplate_and_initials_are_excluded() -> None:
    r = parse_pib(HI)
    assert r.posted_on == date(2024, 10, 29)
    assert HI[r.body_start : r.body_end] == "यह नई सीमा 24 अक्टूबर, 2024 को प्रभावी हुई।"


def test_missing_release_id_is_an_error() -> None:
    with pytest.raises(ValueError, match="Release ID"):
        parse_pib(EN.replace("(Release ID: 2098406)", ""))


def test_clean_text_removes_private_use_bullets_and_expands_ligatures() -> None:
    assert clean_text(" Simplification of forms") == "Simplification of forms"
    assert clean_text("up to 9 reﬁlls; aﬀordable") == "up to 9 refills; affordable"


def test_clean_text_keeps_indic_joiners() -> None:
    # U+200D (zero-width joiner) is meaningful in Devanagari conjuncts and must survive.
    word = "वित्‍त"
    assert clean_text(word) == word
