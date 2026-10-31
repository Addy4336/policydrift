"""Dev-only retrieval probes: questions with machine-checkable gold chunks.

A chunk is gold for a probe when it has the probe's scheme, version and document language
and contains the probe's ``contains`` text. These probes calibrate retrieval; they are not
part of the benchmark and are never used to score the frozen test split.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict

from policydrift.ingest.build import Chunk
from policydrift.retrieval.search import Filters, Hit, Retriever


class Probe(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    query: str
    query_lang: Literal["en", "hi", "gu"]
    doc_lang: Literal["en", "hi", "gu"]
    scheme: str
    version: str
    contains: str

    @property
    def cross_lingual(self) -> bool:
        return self.query_lang != self.doc_lang


def load_probes(path: Path) -> list[Probe]:
    with path.open(encoding="utf-8") as f:
        return [Probe.model_validate_json(line) for line in f if line.strip()]


def is_gold(probe: Probe, chunk: Chunk) -> bool:
    return (
        chunk.scheme == probe.scheme
        and chunk.version == probe.version
        and chunk.language == probe.doc_lang
        and probe.contains in chunk.text
    )


def gold_ids(probe: Probe, chunks: Sequence[Chunk]) -> set[str]:
    return {c.chunk_id for c in chunks if is_gold(probe, c)}


@dataclass(frozen=True)
class ProbeResult:
    probe: Probe
    first_gold_rank: int | None  # 1-based rank of the first gold chunk within the top 10
    top1_right_scheme: bool
    top1_wrong_version: bool  # top-1 is the right scheme and document language, wrong version


def evaluate(retriever: Retriever, probes: Sequence[Probe], depth: int = 10) -> list[ProbeResult]:
    results = []
    for probe in probes:
        # Cross-lingual probes (condition X) search only the documents of the other language.
        flt = Filters(language=probe.doc_lang) if probe.cross_lingual else None
        hits: list[Hit] = retriever.search(probe.query, depth, flt)
        first = next((h.rank for h in hits if is_gold(probe, h.chunk)), None)
        top = hits[0].chunk if hits else None
        results.append(
            ProbeResult(
                probe=probe,
                first_gold_rank=first,
                top1_right_scheme=bool(top and top.scheme == probe.scheme),
                top1_wrong_version=bool(
                    top
                    and top.scheme == probe.scheme
                    and top.language == probe.doc_lang
                    and top.version != probe.version
                ),
            )
        )
    return results


def summarise(results: Sequence[ProbeResult]) -> dict[str, dict[str, float]]:
    """Recall@1/5/10, MRR and error rates, overall and per query language / cross-lingual."""
    groups: dict[str, list[ProbeResult]] = defaultdict(list)
    for r in results:
        groups["all"].append(r)
        groups[("xl-" if r.probe.cross_lingual else "") + r.probe.query_lang].append(r)
    out: dict[str, dict[str, float]] = {}
    for name, rs in groups.items():
        n = len(rs)

        def recall(k: int, rs: list[ProbeResult] = rs, n: int = n) -> float:
            return sum(1 for r in rs if r.first_gold_rank and r.first_gold_rank <= k) / n

        out[name] = {
            "n": float(n),
            "recall@1": recall(1),
            "recall@5": recall(5),
            "recall@10": recall(10),
            "mrr": sum(1 / r.first_gold_rank for r in rs if r.first_gold_rank) / n,
            "top1_right_scheme": sum(r.top1_right_scheme for r in rs) / n,
            "top1_wrong_version": sum(r.top1_wrong_version for r in rs) / n,
        }
    return out
