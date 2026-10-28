"""Paragraph-preserving chunking that keeps character offsets into the source text."""

from __future__ import annotations

import re

Span = tuple[int, int]  # [start, end) character offsets into the source text

_BLANK_LINES = re.compile(r"\n[ \t]*\n")
# Sentence ends for English (. ! ?) and Hindi/Gujarati (danda । and full stop).
_SENTENCE_END = re.compile(r"(?<=[.!?।])\s+")


def paragraph_spans(text: str, start: int, end: int) -> list[Span]:
    """Spans of the blank-line-separated paragraphs within ``text[start:end]``."""
    spans: list[Span] = []
    pos = start
    for sep in _BLANK_LINES.finditer(text, start, end):
        spans.append((pos, sep.start()))
        pos = sep.end()
    spans.append((pos, end))
    return [_strip(text, s) for s in spans if text[s[0] : s[1]].strip()]


def chunk_spans(text: str, start: int, end: int, max_chars: int) -> list[Span]:
    """Greedily merge whole paragraphs into chunks of at most ``max_chars`` characters.

    A paragraph longer than ``max_chars`` is split at sentence boundaries. A single
    sentence longer than ``max_chars`` is kept whole rather than cut mid-sentence.
    """
    if max_chars <= 0:
        raise ValueError("max_chars must be positive")
    pieces: list[Span] = []
    for para in paragraph_spans(text, start, end):
        if para[1] - para[0] <= max_chars:
            pieces.append(para)
        else:
            pieces.extend(_sentence_spans(text, para))

    chunks: list[Span] = []
    current: Span | None = None
    for piece in pieces:
        if current is None:
            current = piece
        elif piece[1] - current[0] <= max_chars:
            current = (current[0], piece[1])
        else:
            chunks.append(current)
            current = piece
    if current is not None:
        chunks.append(current)
    return chunks


def _sentence_spans(text: str, span: Span) -> list[Span]:
    spans: list[Span] = []
    pos = span[0]
    for m in _SENTENCE_END.finditer(text, span[0], span[1]):
        spans.append((pos, m.start()))
        pos = m.end()
    spans.append((pos, span[1]))
    return [s for s in spans if s[1] > s[0]]


def _strip(text: str, span: Span) -> Span:
    start, end = span
    while start < end and text[start].isspace():
        start += 1
    while end > start and text[end - 1].isspace():
        end -= 1
    return start, end
