"""BM25 retrieval for the hosted demo.

Free hosting tiers cannot hold the e5-base model in memory, so the deployed demo searches the
English passages lexically. Hindi and Gujarati questions are already translated to English and
routed to a scheme before retrieval, which is what makes a lexical search good enough here. The
research experiments always use the dense e5-base retriever; this module is for the demo only.
It returns the same ``Hit`` objects and honours the same ``Filters`` as the dense retriever.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from collections.abc import Sequence

from policydrift.ingest.build import Chunk
from policydrift.retrieval.search import Filters, Hit, chunk_matches

_TOKEN = re.compile(r"[a-z0-9]+")
_STOP = frozenset(
    [
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "for",
        "from",
        "has",
        "have",
        "in",
        "is",
        "it",
        "its",
        "of",
        "on",
        "or",
        "that",
        "the",
        "this",
        "to",
        "under",
        "was",
        "were",
        "what",
        "which",
        "who",
        "will",
        "with",
        "how",
        "much",
        "many",
        "per",
    ]
)


def tokens(text: str) -> list[str]:
    return [t for t in _TOKEN.findall(text.lower()) if t not in _STOP]


class LexicalRetriever:
    def __init__(self, chunks: Sequence[Chunk], k1: float = 1.4, b: float = 0.75) -> None:
        self.chunks = list(chunks)
        self.k1, self.b = k1, b
        self._tf = [Counter(tokens(f"{c.title} {c.text}")) for c in self.chunks]
        self._len = [sum(tf.values()) for tf in self._tf]
        self._avg = sum(self._len) / max(1, len(self._len))
        df: Counter[str] = Counter()
        for tf in self._tf:
            df.update(tf.keys())
        n = len(self.chunks)
        self._idf = {t: math.log(1 + (n - d + 0.5) / (d + 0.5)) for t, d in df.items()}

    def _score(self, i: int, query: list[str]) -> float:
        tf, length = self._tf[i], self._len[i]
        score = 0.0
        for t in query:
            f = tf.get(t, 0)
            if f:
                norm = (
                    f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * length / self._avg))
                )
                score += self._idf.get(t, 0.0) * norm
        return score

    def search(self, query: str, k: int = 5, flt: Filters | None = None) -> list[Hit]:
        flt = flt or Filters()
        q = tokens(query)
        scored = [
            (self._score(i, q), i) for i, c in enumerate(self.chunks) if chunk_matches(c, flt)
        ]
        scored.sort(key=lambda s: (-s[0], s[1]))  # ties broken by chunk order
        return [Hit(self.chunks[i], s, rank) for rank, (s, i) in enumerate(scored[:k], start=1)]
