"""Prompt construction for the answering step. Mitigation prompts arrive in Phase 4."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date

from policydrift.ingest.build import Chunk

LANGUAGE_NAMES = {"en": "English", "hi": "Hindi", "gu": "Gujarati"}

SYSTEM = (
    "You are an assistant that answers questions about Indian government rules, schemes and "
    "tax provisions. Give the figure the question asks for, then one short sentence of context. "
    "Answer in the language of the question."
)

_WITH_PASSAGES = (
    "Use the passages below to answer. If the passages do not contain the answer, say so.\n\n"
    "{passages}\n\nQuestion: {question}"
)
_CLOSED_BOOK = "Question: {question}"


def _window(chunk: Chunk) -> str:
    start, end = chunk.effective_from, chunk.effective_to

    def fmt(d: date | None) -> str:
        return d.isoformat() if d else "?"

    if start is None and end is None:
        return "dates not stated"
    return f"in force from {fmt(start)} to {end.isoformat() if end else 'present'}"


def format_passages(chunks: Sequence[Chunk], show_dates: bool) -> str:
    blocks = []
    for i, c in enumerate(chunks, start=1):
        header = f"[{i}] {c.title}"
        if show_dates:
            header += f" ({_window(c)})"
        blocks.append(f"{header}\n{c.text}")
    return "\n\n".join(blocks)


def build_prompt(question: str, chunks: Sequence[Chunk], show_dates: bool) -> str:
    if not chunks:
        return _CLOSED_BOOK.format(question=question)
    return _WITH_PASSAGES.format(passages=format_passages(chunks, show_dates), question=question)
