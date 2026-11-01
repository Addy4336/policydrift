"""LLM judge for answers the deterministic matcher cannot decide.

The judge only does matching: it is given the two candidate values and asked which one the
answer commits to. It is never told which value is correct, and it needs no rule knowledge.
"""

from __future__ import annotations

import json
import re
from typing import Literal

from policydrift.llm import LLMClient, LLMError, LLMRequest
from policydrift.scoring.matcher import Label, Verdict

SYSTEM = (
    "You are a strict labelling assistant. You compare an answer with two candidate values and "
    "report which one the answer commits to as the figure that applies. You do not judge which "
    "value is true."
)

TEMPLATE = """Question: {question}

Candidate value A: {a}
Candidate value B: {b}

Answer to label:
\"\"\"
{answer}
\"\"\"

Decide what the answer commits to as the figure that applies now:
- "A" if it commits to value A (the same quantity in any wording, script, unit or language)
- "B" if it commits to value B
- "neither" if it commits to some other figure
- "refusal" if it declines to give a figure or says the information is missing
If the answer mentions a value only as an earlier, replaced or alternative figure, it does not
commit to it. If it is genuinely ambiguous, use "neither".

Reply with JSON only: {{"commits_to": "A" | "B" | "neither" | "refusal"}}"""

_JSON = re.compile(r"\{.*?\}", re.S)


def judge_prompt(question: str, answer: str, a: str, b: str) -> str:
    return TEMPLATE.format(question=question, answer=answer.strip(), a=a, b=b)


def parse_judgement(text: str) -> Literal["A", "B", "neither", "refusal"] | None:
    for m in _JSON.finditer(text):
        try:
            value = json.loads(m.group(0)).get("commits_to")
        except (json.JSONDecodeError, AttributeError):
            continue
        if value in {"A", "B", "neither", "refusal"}:
            return value  # type: ignore[no-any-return]
    return None


def judge_answer(
    client: LLMClient,
    provider: Literal["gemini", "groq"],
    model: str,
    question: str,
    answer: str,
    old_text: str,
    current_text: str,
    *,
    swap: bool = False,
) -> Verdict:
    """Label an undecided answer. ``swap`` puts the current value first (position-bias check)."""
    a, b = (current_text, old_text) if swap else (old_text, current_text)
    request = LLMRequest(
        provider=provider,
        model=model,
        system=SYSTEM,
        prompt=judge_prompt(question, answer, a, b),
        max_tokens=1024,
        json_mode=False,
        purpose="judge",
    )
    try:
        reply = client.complete(request)
    except LLMError as exc:
        return Verdict(label=None, reason=f"judge failed: {exc}")
    choice = parse_judgement(reply.text)
    if choice is None:
        return Verdict(label=None, reason="judge reply unreadable")
    if choice == "refusal":
        return Verdict(label="refusal", reason="judge: refusal")
    if choice == "neither":
        return Verdict(label="other", reason="judge: other figure")
    first_is_old = not swap
    picked_old = (choice == "A") == first_is_old
    label: Label = "outdated" if picked_old else "current"
    return Verdict(label=label, reason="judge: commits to " + label)
