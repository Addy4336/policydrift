"""Exact cosine search over chunk embeddings with scheme, language and version filters."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import numpy as np

from policydrift.ingest.build import Chunk
from policydrift.ingest.registry import Registry
from policydrift.retrieval.embed import Embedder, EmbeddingCache


def load_chunks(path: Path) -> list[Chunk]:
    with path.open(encoding="utf-8") as f:
        return [Chunk.model_validate_json(line) for line in f if line.strip()]


@dataclass(frozen=True)
class Filters:
    """Restrict which chunks may be returned. ``None`` means no restriction."""

    schemes: frozenset[str] | None = None
    language: str | None = None  # language of the document, not of the query
    versions: frozenset[str] | None = None  # explicit version ids
    as_of: date | None = None  # keep chunks whose effective window contains this date
    current_only: bool = False  # keep only each scheme's open-ended (current) version


@dataclass(frozen=True)
class Hit:
    chunk: Chunk
    score: float
    rank: int  # 1-based


def chunk_matches(chunk: Chunk, flt: Filters) -> bool:
    if flt.schemes is not None and chunk.scheme not in flt.schemes:
        return False
    if flt.language is not None and chunk.language != flt.language:
        return False
    if flt.versions is not None and chunk.version not in flt.versions:
        return False
    if flt.current_only and chunk.effective_to is not None:
        return False
    if flt.as_of is not None:
        if chunk.effective_from is not None and chunk.effective_from > flt.as_of:
            return False
        if chunk.effective_to is not None and flt.as_of > chunk.effective_to:
            return False
    return True


class Retriever:
    def __init__(
        self,
        chunks: Sequence[Chunk],
        embedder: Embedder,
        cache: EmbeddingCache,
        registry: Registry | None = None,
    ) -> None:
        self.chunks = list(chunks)
        self.embedder = embedder
        self.cache = cache
        self.registry = registry
        self.matrix, self.computed = cache.get_or_compute(
            embedder, "passage", [c.text for c in self.chunks]
        )

    def search(self, query: str, k: int = 5, flt: Filters | None = None) -> list[Hit]:
        """Top-``k`` chunks by cosine similarity among those passing ``flt``.

        Ties are broken by chunk order, so results are deterministic.
        """
        flt = flt or Filters()
        allowed = np.array([chunk_matches(c, flt) for c in self.chunks])
        if not allowed.any():
            return []
        qvec, _ = self.cache.get_or_compute(self.embedder, "query", [query])
        scores = self.matrix @ qvec[0]
        scores = np.where(allowed, scores, -np.inf)
        order = np.argsort(-scores, kind="stable")[:k]
        return [
            Hit(self.chunks[i], float(scores[i]), rank)
            for rank, i in enumerate(order, start=1)
            if np.isfinite(scores[i])
        ]

    def search_versions(
        self,
        query: str,
        scheme: str,
        k_each: int = 3,
        language: str | None = None,
        which: str = "both",
    ) -> list[Hit]:
        """Top ``k_each`` chunks from the current version and/or the one before it.

        ``which`` is ``"current"``, ``"previous"`` or ``"both"`` (current first). This is
        the retrieval step of the both-versions conditions R3/R4 in the pre-registration.
        """
        if self.registry is None:
            raise ValueError("a version registry is required")
        versions = self.registry[scheme].versions
        if len(versions) < 2 and which != "current":
            raise ValueError(f"{scheme} has no previous version")
        wanted = {"current": [-1], "previous": [-2], "both": [-1, -2]}[which]
        hits: list[Hit] = []
        for index in wanted:
            flt = Filters(
                schemes=frozenset({scheme}),
                versions=frozenset({versions[index].id}),
                language=language,
            )
            hits.extend(self.search(query, k_each, flt))
        return [Hit(h.chunk, h.score, rank) for rank, h in enumerate(hits, start=1)]
