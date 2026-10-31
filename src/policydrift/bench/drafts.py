"""LLM-drafted question wording (milestone 2c).

The LLM only phrases questions. Gold answers come from ``data/facts.yaml`` and are never shown
to the model, so it cannot leak or invent them. Each draft is one fact x one question style,
written in en, hi and gu in a single call so the three languages stay paired.
Drafts are unverified until a human reviews them (milestone 2d).
"""

from __future__ import annotations

import json
import re
from collections.abc import Sequence
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict

from policydrift.bench.facts import Fact, value_forms
from policydrift.ingest.registry import Registry
from policydrift.llm import LLMClient, LLMError, LLMRequest

LANGS = ("en", "hi", "gu")
Style = Literal["direct", "scenario", "helpline"]
STYLES: dict[str, str] = {
    "direct": "A short, plain question asking for the figure that applies today.",
    "scenario": (
        "A question from an ordinary person describing their situation in one sentence "
        "(no numbers in the situation) and asking what figure applies to them."
    ),
    "helpline": (
        "A formal question as a citizen would put it to an official helpline, naming the "
        "scheme or law explicitly."
    ),
}

SYSTEM = (
    "You write evaluation questions about Indian government rules, in English, Hindi and "
    "Gujarati. Rules:\n"
    "- Ask for exactly one figure. The question must be answerable with a single number.\n"
    "- Ask about the rule as it applies today. Never use words such as old, previous, earlier, "
    "new, revised, changed, updated or raised, and never mention a year of change.\n"
    "- Never state any figure that could be the answer. Do not put amounts or percentages "
    "from the rule in the question.\n"
    "- Use natural, standard Hindi (Devanagari) and Gujarati (Gujarati script). Keep scheme "
    "names and legal terms the way officials write them. Write numerals as ASCII digits.\n"
    'Reply with JSON only: {"en": "...", "hi": "...", "gu": "..."}'
)


class DraftItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_id: str  # "<fact id>/<style>"
    fact_id: str
    style: str
    questions: dict[str, str]
    drafter: str  # "<provider>:<model>"
    model_version: str | None = None
    leaks: list[str] = []  # languages whose question contains the old or current value
    status: Literal["draft"] = "draft"  # becomes verified/rejected in milestone 2d


def build_prompt(fact: Fact, scheme_name: str, style: str) -> str:
    return (
        f"Scheme or law: {scheme_name}\n"
        f"What to ask about: {fact.attribute}\n"
        f"Style: {STYLES[style]}\n"
        "Write the question in all three languages with the same meaning."
    )


def parse_questions(text: str) -> dict[str, str] | None:
    """Pull the three questions out of a model reply; None if the reply is unusable."""
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if match is None:
        return None
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    out = {lang: str(data.get(lang, "")).strip() for lang in LANGS}
    return out if all(len(q) >= 10 for q in out.values()) else None


def find_leaks(fact: Fact, questions: dict[str, str]) -> list[str]:
    """Languages whose question spells out the old or current value (a hint to the answerer)."""
    leaks: list[str] = []
    for lang, question in questions.items():
        forms = [
            form
            for value in (fact.old.value, fact.current.value)
            for form in value_forms(fact.kind, value, lang)
        ]
        if any(re.search(rf"(?<![\d.,]){re.escape(f)}(?![\d])", question) for f in forms):
            leaks.append(lang)
    return leaks


def draft_item(
    client: LLMClient,
    fact: Fact,
    scheme_name: str,
    style: str,
    provider: Literal["gemini", "groq"],
    model: str,
) -> DraftItem | None:
    request = LLMRequest(
        provider=provider,
        model=model,
        system=SYSTEM,
        prompt=build_prompt(fact, scheme_name, style),
        temperature=0.0,
        max_tokens=2048,
        json_mode=True,
        purpose="draft",
    )
    try:
        reply = client.complete(request)
    except LLMError:
        return None
    questions = parse_questions(reply.text)
    if questions is None:
        return None
    return DraftItem(
        item_id=f"{fact.id}/{style}",
        fact_id=fact.id,
        style=style,
        questions=questions,
        drafter=f"{provider}:{model}",
        model_version=reply.model_version,
        leaks=find_leaks(fact, questions),
    )


def draft_all(
    client: LLMClient,
    facts: Sequence[Fact],
    registry: Registry,
    provider: Literal["gemini", "groq"],
    model: str,
    styles: Sequence[str] = tuple(STYLES),
) -> tuple[list[DraftItem], list[str]]:
    """Draft every fact x style. Returns (drafts, ids that failed)."""
    drafts: list[DraftItem] = []
    failed: list[str] = []
    for fact in facts:
        name = registry[fact.scheme].name
        for style in styles:
            item = draft_item(client, fact, name, style, provider, model)
            if item is None:
                failed.append(f"{fact.id}/{style}")
            else:
                drafts.append(item)
    return drafts, failed


def write_drafts(drafts: Sequence[DraftItem], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for d in drafts:
            f.write(d.model_dump_json() + "\n")


def load_drafts(path: Path) -> list[DraftItem]:
    with path.open(encoding="utf-8") as f:
        return [DraftItem.model_validate_json(line) for line in f if line.strip()]
