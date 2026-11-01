"""Score a run: deterministic matcher first, LLM judge for what it cannot decide."""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from policydrift.bench.forms import indian_grouping
from policydrift.bench.split import BenchItem
from policydrift.llm import LLMClient
from policydrift.scoring.judge import judge_answer
from policydrift.scoring.matcher import score_answer

LABELS = ("current", "outdated", "other", "refusal")


class ScoreRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_id: str
    fact_id: str
    model: str
    language: str
    condition: str
    label: str  # current | outdated | other | refusal | missing | unresolved
    method: Literal["matcher", "judge", "none"]
    reason: str
    numbers: list[float]


def describe_value(kind: str, value: float) -> str:
    """A value as the judge sees it (English, with the unit)."""
    if kind == "inr":
        return f"₹{indian_grouping(int(value))}"
    number = f"{value:g}"
    return {
        "percent": f"{number}%",
        "years": f"{number} years",
        "months": f"{number} months",
        "days": f"{number} days",
    }.get(kind, number)


def load_answers(run_dir: Path) -> list[dict[str, Any]]:
    with (run_dir / "answers.jsonl").open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def score_run(
    answers: Sequence[Mapping[str, Any]],
    items: Mapping[str, BenchItem],
    judge: tuple[LLMClient, Literal["gemini", "groq"], str] | None = None,
) -> list[ScoreRecord]:
    out: list[ScoreRecord] = []
    for n, a in enumerate(answers):
        item = items[a["item_id"]]
        base: dict[str, Any] = {
            "item_id": a["item_id"],
            "fact_id": a["fact_id"],
            "model": a["model"],
            "language": a["language"],
            "condition": a["condition"],
        }
        if a["status"] != "ok" or not a["answer"]:
            out.append(
                ScoreRecord(
                    **base, label="missing", method="none", reason=a["error"] or "", numbers=[]
                )
            )
            continue
        verdict = score_answer(a["answer"], item.old.value, item.current.value)
        method: Literal["matcher", "judge", "none"] = "matcher"
        if verdict.label is None and judge is not None:
            client, provider, model = judge
            judged = judge_answer(
                client,
                provider,
                model,
                item.questions[a["language"]],
                a["answer"],
                describe_value(item.kind, item.old.value),
                describe_value(item.kind, item.current.value),
                swap=n % 2 == 1,  # alternate the order to spread any position bias
            )
            verdict, method = judged, "judge"
        label = verdict.label or "unresolved"
        out.append(
            ScoreRecord(
                **base,
                label=label,
                method=method if verdict.label else "none",
                reason=verdict.reason,
                numbers=list(verdict.numbers),
            )
        )
    return out


def summarise(scores: Sequence[ScoreRecord]) -> list[dict[str, Any]]:
    """Counts and outdated rate per model x language x condition.

    The rate is outdated / answered (refusals and other answers stay in the denominator;
    missing answers are excluded, as pre-registered).
    """
    groups: dict[tuple[str, str, str], Counter[str]] = {}
    for s in scores:
        groups.setdefault((s.model, s.condition, s.language), Counter())[s.label] += 1
    rows = []
    for (model, condition, language), c in sorted(groups.items()):
        answered = sum(v for k, v in c.items() if k != "missing")
        rows.append(
            {
                "model": model,
                "condition": condition,
                "language": language,
                "n": answered,
                **{label: c[label] for label in (*LABELS, "unresolved", "missing")},
                "outdated_rate": round(c["outdated"] / answered, 3) if answered else None,
            }
        )
    return rows


def knowledge_state(label: str) -> str:
    """Closed-book (R0) label -> the pre-registered knowledge state."""
    return {"current": "knows_current", "outdated": "knows_old"}.get(label, "neither")
