import json
from pathlib import Path

import httpx

from policydrift.bench.drafts import (
    DraftItem,
    draft_all,
    find_leaks,
    load_drafts,
    parse_questions,
    write_drafts,
)
from policydrift.bench.facts import Fact, load_facts
from policydrift.ingest.registry import load_registry
from policydrift.llm import LLMClient, ResponseCache


def _fact(root: Path, fact_id: str) -> Fact:
    return next(f for f in load_facts(root / "data" / "facts.yaml") if f.id == fact_id)


def test_parse_questions_accepts_wrapped_json_and_rejects_junk() -> None:
    good = '```json\n{"en": "What is the limit?", "hi": "सीमा क्या है?", "gu": "મર્યાદા શું છે?"}\n```'
    parsed = parse_questions(good)
    assert parsed is not None and set(parsed) == {"en", "hi", "gu"}
    assert parse_questions("no json here") is None
    assert parse_questions('{"en": "What is the limit?"}') is None
    assert parse_questions('{"en": "x", "hi": "y", "gu": "z"}') is None


def test_leak_check_catches_values_in_any_script(root: Path) -> None:
    fact = _fact(root, "pmuy-subsidy-per-cylinder")  # 200 -> 300 rupees
    clean = {"en": "What is the subsidy per 14.2 kg cylinder?", "hi": "x" * 12, "gu": "y" * 12}
    assert find_leaks(fact, clean) == []
    leaky = {**clean, "en": "Is the subsidy Rs.300 per cylinder?", "hi": "क्या सब्सिडी ३०० रुपये है?"}
    assert find_leaks(fact, leaky) == ["en", "hi"]


def test_percent_leak_and_decimal_boundary(root: Path) -> None:
    fact = _fact(root, "cg-ltcg-112a-rate")  # 10 -> 12.5 percent
    assert find_leaks(fact, {"en": "Is the rate 12.5%?"}) == ["en"]
    assert find_leaks(fact, {"en": "Is it 112.5 or 2.10?"}) == []


def _client(tmp_path: Path, handler: httpx.MockTransport) -> LLMClient:
    return LLMClient(
        ResponseCache(tmp_path / "c.sqlite"),
        {"groq": "k"},
        {"groq": 1000},
        http=httpx.Client(transport=handler),
        sleep=lambda s: None,
    )


def test_draft_all_pairs_languages_flags_leaks_and_records_failures(
    root: Path, tmp_path: Path
) -> None:
    facts = [_fact(root, "pmuy-subsidy-per-cylinder")]
    registry = load_registry(root / "data" / "schemes.yaml")
    direct = {"en": "What is the subsidy per cylinder?", "hi": "प्रति सिलेंडर सब्सिडी कितनी है?"}
    direct["gu"] = "સિલિન્ડર દીઠ સબસિડી કેટલી છે?"
    scenario = {"en": "I use one cylinder, is it Rs.300?", "hi": "मुझे कितनी सब्सिडी मिलेगी?"}
    scenario["gu"] = "મને કેટલી સબસિડી મળશે?"
    replies = {"direct": json.dumps(direct), "scenario": json.dumps(scenario)}

    def handler(request: httpx.Request) -> httpx.Response:
        body = request.content.decode("utf-8")
        for style, text in replies.items():
            if f"Style: {style}" in body or (style == "direct" and "short, plain" in body):
                return _ok(text)
            if style == "scenario" and "ordinary person" in body:
                return _ok(text)
        return httpx.Response(400, text="no")

    def _ok(text: str) -> httpx.Response:
        return httpx.Response(
            200, json={"model": "m", "choices": [{"message": {"content": text}}], "usage": {}}
        )

    client = _client(tmp_path, httpx.MockTransport(handler))
    drafts, failed = draft_all(client, facts, registry, "groq", "m")
    by_style = {d.style: d for d in drafts}
    assert set(by_style) == {"direct", "scenario"} and failed == []
    _, failed = draft_all(client, facts, registry, "groq", "m", styles=("helpline",))
    assert failed == ["pmuy-subsidy-per-cylinder/helpline"]
    assert by_style["direct"].leaks == [] and by_style["scenario"].leaks == ["en"]
    assert set(by_style["direct"].questions) == {"en", "hi", "gu"}

    path = tmp_path / "d.jsonl"
    write_drafts(drafts, path)
    again: list[DraftItem] = load_drafts(path)
    assert [d.item_id for d in again] == [d.item_id for d in drafts]
    assert all(d.status == "draft" for d in again)


def test_prompt_uses_the_question_name_not_the_registry_label(root: Path) -> None:
    from policydrift.bench.drafts import build_prompt

    registry = load_registry(root / "data" / "schemes.yaml")
    rural = registry["rural-employment-guarantee"]
    assert rural.question_name and "never call it MGNREGA" in rural.question_name
    tax = registry["income-tax-new-regime"]
    assert tax.question_name and "new tax regime" in tax.question_name
    fact = _fact(root, "rural-guaranteed-days")
    assert "VB-G RAM G" in build_prompt(fact, rural.question_name, "direct")
