# ruff: noqa: E501
"""Spot-check the live demo: in-scope questions with known answers (dev facts only), a false
premise, and out-of-scope questions that must be declined rather than answered.

    uv run --no-sync python scripts/demo_eval.py [--api URL]

Expected values come from data/facts.yaml (dev split), where each value is quoted from an
official release. Writes a JSON log next to the printed table.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import httpx

CASES = [
    # id, kind, language, as_of, question, expected (substring forms), note
    (
        "A1",
        "in-scope",
        "en",
        None,
        "How many days of guaranteed work does the rural employment guarantee law now give each household in a year?",
        ["125"],
        "current v2; old 100",
    ),
    (
        "A2",
        "in-scope",
        "hi",
        None,
        "सूचीबद्ध शेयरों पर अल्पकालिक पूंजीगत लाभ (धारा 111A) पर अभी कर की दर क्या है?",
        ["20"],
        "current 20%; old 15%",
    ),
    (
        "A3",
        "in-scope",
        "gu",
        None,
        "પીએમ ઉજ્જવલા યોજના હેઠળ દરેક LPG સિલિન્ડર પર કેટલી સબસિડી મળે છે?",
        ["300"],
        "current ₹300; old ₹200",
    ),
    (
        "A4",
        "past-date",
        "en",
        "2023-06-01",
        "What was the maximum loan under PM Mudra Yojana?",
        ["10 lakh", "1,000,000", "10,00,000"],
        "v1 in force on 2023-06-01: ₹10 lakh",
    ),
    (
        "A5",
        "past-date",
        "hi",
        "2023-01-01",
        "पीएम स्वनिधि योजना में दूसरी किस्त का ऋण कितना है?",
        ["20,000", "20000"],
        "v1: ₹20,000",
    ),
    (
        "A6",
        "in-scope",
        "gu",
        None,
        "પીએમ સ્વનિધિ યોજના હેઠળ બીજી લોન કેટલી મળે છે?",
        ["25,000", "25000"],
        "current ₹25,000",
    ),
    (
        "A7",
        "in-scope",
        "en",
        None,
        "What is the long-term capital gains tax rate on gold and unlisted assets now?",
        ["12.5"],
        "current 12.5%; old 20%",
    ),
    (
        "A8",
        "in-scope",
        "en",
        None,
        "How long must gold be held to count as a long-term capital asset?",
        ["24"],
        "current 24 months; old 36",
    ),
    (
        "F1",
        "false-premise",
        "en",
        None,
        "Why did the government reduce the PM Mudra loan limit to Rs 5 lakh in 2025?",
        ["20 lakh", "2,000,000", "20,00,000"],
        "should correct the premise: limit is ₹20 lakh",
    ),
    (
        "O1",
        "out-of-scope",
        "en",
        None,
        "What specific modification did the Digital Personal Data Protection (Removal of Difficulties) Order, 2026 make to Section 9(1) regarding verifiable consent, and what is its exact effective date?",
        [],
        "not in corpus: must decline",
    ),
    (
        "O2",
        "out-of-scope",
        "hi",
        None,
        "गृह मंत्रालय द्वारा 16 अक्टूबर 2026 को अधिसूचित जनगणना (संशोधन) नियम, 2026 के अनुसार, निजी क्षेत्र के पेशेवरों की किस विशिष्ट श्रेणी को अब प्रगणक के रूप में तैनात करने की अनुमति दी गई है?",
        [],
        "not in corpus: must decline",
    ),
    (
        "O3",
        "out-of-scope",
        "gu",
        None,
        "મર્ચન્ટ શિપિંગ (રેગ્યુલેશન ઓફ એન્ટ્રી ઓફ શિપ્સ ઇનટુ કોસ્ટલ વોટર્સ) રૂલ્સ, 2026 વિદેશી ધ્વજવાળા જહાજો માટે કઈ મંજૂરીઓ ફરજિયાત બનાવે છે?",
        [],
        "not in corpus: must decline",
    ),
    (
        "O4",
        "out-of-scope",
        "en",
        None,
        "What is the exact short title and implementation timeline under the CBDT Gazette notification G.S.R. 198(E)?",
        [],
        "not in corpus (near the tax schemes): must decline",
    ),
]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", default="https://policydrift-api.vercel.app")
    ap.add_argument("--out", default="docs/demo_eval.json")
    args = ap.parse_args()
    log = []
    for cid, kind, lang, as_of, q, expect, note in CASES:
        body = {"question": q, "language": lang} | ({"as_of": as_of} if as_of else {})
        t = time.time()
        r = httpx.post(f"{args.api}/api/ask", json=body, timeout=180)
        d = r.json()
        ans = d.get("answer") or d.get("detail", "")
        flat = " ".join(ans.replace("₹", "").replace("Rs ", "").split())
        found = [e for e in expect if e in flat] if expect else []
        entry = {
            "id": cid,
            "kind": kind,
            "language": lang,
            "as_of": as_of,
            "question": q,
            "expected": expect,
            "note": note,
            "status": r.status_code,
            "seconds": round(time.time() - t, 1),
            "answer": ans,
            "search_query": d.get("search_query"),
            "rule_versions": d.get("rule_versions"),
            "conflicts": [c["note"] for c in d.get("conflicts", [])],
            "numbers": d.get("checks", {}).get("numbers"),
            "warnings": d.get("warnings"),
            "expected_found": found,
        }
        log.append(entry)
        rv = ", ".join(f"{v['scheme']}:{v['version']}" for v in d.get("rule_versions") or [])
        print(
            f"{cid} [{lang}] {r.status_code} {entry['seconds']}s | {rv} | match={bool(found) if expect else '-'}\n    {ans[:260]}\n"
        )
    Path(args.out).write_text(
        json.dumps(log, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
