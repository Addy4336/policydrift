"""Phase 4 mitigations (pre-registration §2): prompt wording, version filter, conflict checker.

M-a1 stamps today's date and asks for the rule in force today. M-a2 labels every passage with
the period it applies to. M-b drafts an answer, checks it against the dated passages and
re-answers when the check finds a superseded value. M-c (version-filtered retrieval) lives in
``experiments.runner.select_context`` because it changes what is retrieved, not what is asked.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date

from policydrift.experiments.prompts import SYSTEM, build_prompt, format_passages
from policydrift.ingest.build import Chunk
from policydrift.llm import LLMRequest, LLMResponse

DATE_STAMP = (
    " Today's date is {as_of}. Rules change over time: if the passages describe more than one "
    "version of a rule, answer with the version in force today, not an earlier or later one."
)
VALIDITY = " Each passage is labelled with the period in which it is in force."

CHECK_SYSTEM = (
    "You check answers about Indian government rules against the passages provided. "
    "Use only the passages."
)
CHECK_TEMPLATE = (
    "Today's date is {as_of}.\n\nPassages (each labelled with the period it is in force):\n"
    "{passages}\n\nQuestion: {question}\nDraft answer: {draft}\n\n"
    "Decide whether the draft answer states the rule in force today. It is inconsistent if it "
    "states a value from a superseded version or from a version not yet in force. Reply with "
    'JSON only: {{"consistent": true}} or {{"consistent": false, "reason": "<one short '
    'sentence>"}}'
)
REVISE_TEMPLATE = (
    "\n\nYour earlier draft answer was: {draft}\nA check found that it does not state the rule "
    "in force on {as_of}: {reason}\nAnswer again using the rule in force today."
)

Ask = Callable[[LLMRequest], LLMResponse]
MakeRequest = Callable[[str, str], LLMRequest]  # (system, prompt) -> request


def system_for(mitigation: str, as_of: date) -> str:
    """The answerer's system prompt under ``mitigation``."""
    if mitigation == "M-a1":
        return SYSTEM + DATE_STAMP.format(as_of=as_of.isoformat())
    if mitigation == "M-a2":
        return SYSTEM + VALIDITY
    return SYSTEM


def show_dates_for(mitigation: str, baseline: bool) -> bool:
    """Whether passages carry their effective dates (M-a2 always does)."""
    return True if mitigation == "M-a2" else baseline


def parse_check(text: str) -> tuple[bool | None, str]:
    """(consistent, reason) from the checker's reply; consistent is None when unparsable."""
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return None, ""
    try:
        data = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None, ""
    flag = data.get("consistent") if isinstance(data, dict) else None
    if not isinstance(flag, bool):
        return None, ""
    return flag, str(data.get("reason", ""))


@dataclass(frozen=True)
class Checked:
    final: LLMResponse
    calls: int
    input_tokens: int | None
    output_tokens: int | None
    latency_s: float
    cached: bool
    draft: str
    verdict: str  # "consistent", "revised" or "unparsed"


def _sum(values: Sequence[int | None]) -> int | None:
    known = [v for v in values if v is not None]
    return sum(known) if known else None


def run_conflict_checker(
    ask: Ask,
    make_request: MakeRequest,
    question: str,
    chunks: Sequence[Chunk],
    show_dates: bool,
    as_of: date,
) -> Checked:
    """Draft, check against the dated passages, and re-answer when the check disagrees."""
    stamp = as_of.isoformat()
    draft = ask(make_request(SYSTEM, build_prompt(question, chunks, show_dates)))
    check_prompt = CHECK_TEMPLATE.format(
        as_of=stamp,
        passages=format_passages(chunks, show_dates=True),
        question=question,
        draft=draft.text.strip(),
    )
    check = ask(make_request(CHECK_SYSTEM, check_prompt))
    replies = [draft, check]
    consistent, reason = parse_check(check.text)
    verdict = "unparsed" if consistent is None else "consistent"
    final = draft
    if consistent is False:
        revise = build_prompt(question, chunks, True) + REVISE_TEMPLATE.format(
            draft=draft.text.strip(), as_of=stamp, reason=reason or "it uses another version"
        )
        final = ask(make_request(system_for("M-a1", as_of), revise))
        replies.append(final)
        verdict = "revised"
    return Checked(
        final=final,
        calls=len(replies),
        input_tokens=_sum([r.input_tokens for r in replies]),
        output_tokens=_sum([r.output_tokens for r in replies]),
        latency_s=round(sum(r.latency_s for r in replies if not r.cached), 3),
        cached=all(r.cached for r in replies),
        draft=draft.text,
        verdict=verdict,
    )
