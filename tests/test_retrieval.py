from collections.abc import Sequence
from datetime import date
from pathlib import Path

import numpy as np
import pytest

from policydrift.ingest.build import Chunk
from policydrift.ingest.registry import Registry, Scheme, Version
from policydrift.retrieval.embed import (
    EmbeddingCache,
    EmbedModel,
    Matrix,
    text_key,
)
from policydrift.retrieval.probes import Probe, evaluate, gold_ids, is_gold, summarise
from policydrift.retrieval.search import Filters, Retriever, chunk_matches

MODEL = EmbedModel("fake", "fake/model", query_prefix="q: ", passage_prefix="p: ")
WORDS = ["alpha", "beta", "gamma", "delta", "epsilon"]


class FakeEmbedder:
    """Bag-of-keywords embedder: deterministic, counts how many texts it was asked to encode."""

    def __init__(self) -> None:
        self.model = MODEL
        self.encoded = 0

    def encode(self, texts: Sequence[str]) -> Matrix:
        self.encoded += len(texts)
        rows = []
        for t in texts:
            v = np.array([t.lower().count(w) for w in WORDS], dtype=np.float32) + 1e-3
            rows.append(v / np.linalg.norm(v))
        return np.stack(rows)


def make_chunk(
    cid: str,
    text: str,
    version: str,
    frm: date | None,
    to: date | None,
    scheme: str = "s",
    lang: str = "en",
) -> Chunk:
    return Chunk(
        chunk_id=cid,
        scheme=scheme,
        version=version,
        effective_from=frm,
        effective_to=to,
        announced_on=None,
        language=lang,  # type: ignore[arg-type]
        source_url="https://example.org",
        source_path="x.txt",
        source_sha256="0" * 64,
        source_release_id="1",
        source_release_id_kind="prid",
        ministry="M",
        title="T",
        posted_on=date(2024, 1, 1),
        posted_by=None,
        chunk_index=0,
        raw_start=0,
        raw_end=len(text),
        text=text,
    )


OLD = (date(2020, 1, 1), date(2023, 12, 31))
NEW = (date(2024, 1, 1), None)
CHUNKS = [
    make_chunk("old-a", "alpha alpha old rule", "v1", *OLD),
    make_chunk("new-a", "alpha new rule", "v2", *NEW),
    make_chunk("new-b", "beta new rule", "v2", *NEW),
    make_chunk("hi-a", "alpha hindi", "v2", *NEW, lang="hi"),
    make_chunk("other-a", "alpha other scheme", "v1", *NEW, scheme="t"),
]
REGISTRY: Registry = {
    "s": Scheme(
        name="S",
        versions=[
            Version(id="v1", effective_from=OLD[0], effective_to=OLD[1]),
            Version(id="v2", effective_from=NEW[0], effective_to=None),
        ],
    )
}


@pytest.fixture
def retriever(tmp_path: Path) -> Retriever:
    return Retriever(CHUNKS, FakeEmbedder(), EmbeddingCache(tmp_path, MODEL), REGISTRY)


def ids(hits: list) -> list[str]:  # type: ignore[type-arg]
    return [h.chunk.chunk_id for h in hits]


def test_as_of_boundaries_are_inclusive() -> None:
    old = CHUNKS[0]
    assert chunk_matches(old, Filters(as_of=date(2023, 12, 31)))
    assert not chunk_matches(old, Filters(as_of=date(2024, 1, 1)))
    assert not chunk_matches(old, Filters(as_of=date(2019, 12, 31)))
    new = CHUNKS[1]
    assert chunk_matches(new, Filters(as_of=date(2024, 1, 1)))
    assert not chunk_matches(new, Filters(as_of=date(2023, 12, 31)))
    assert chunk_matches(new, Filters(as_of=date(2030, 1, 1)))  # open-ended


def test_open_ended_bounds_do_not_exclude() -> None:
    no_start = make_chunk("x", "alpha", "v1", None, date(2021, 1, 1))
    assert chunk_matches(no_start, Filters(as_of=date(1999, 1, 1)))
    assert not chunk_matches(no_start, Filters(as_of=date(2021, 1, 2)))


def test_search_ranks_by_similarity_and_is_deterministic(retriever: Retriever) -> None:
    first = ids(retriever.search("alpha alpha", 5))
    assert first[0] == "old-a"
    assert first == ids(retriever.search("alpha alpha", 5))


def test_current_only_excludes_superseded_versions(retriever: Retriever) -> None:
    assert "old-a" not in ids(retriever.search("alpha", 5, Filters(current_only=True)))
    assert "old-a" in ids(retriever.search("alpha", 5))


def test_as_of_filter_selects_the_version_in_force(retriever: Retriever) -> None:
    in_2022 = ids(retriever.search("alpha", 5, Filters(as_of=date(2022, 6, 1))))
    assert "old-a" in in_2022 and "new-a" not in in_2022
    in_2025 = ids(retriever.search("alpha", 5, Filters(as_of=date(2025, 6, 1))))
    assert "new-a" in in_2025 and "old-a" not in in_2025


def test_scheme_language_and_version_filters(retriever: Retriever) -> None:
    assert ids(retriever.search("alpha", 5, Filters(schemes=frozenset({"t"})))) == ["other-a"]
    assert ids(retriever.search("alpha", 5, Filters(language="hi"))) == ["hi-a"]
    assert set(ids(retriever.search("alpha", 5, Filters(versions=frozenset({"v1"}))))) == {
        "old-a",
        "other-a",
    }


def test_filter_matching_nothing_returns_no_hits(retriever: Retriever) -> None:
    assert retriever.search("alpha", 5, Filters(schemes=frozenset({"missing"}))) == []


def test_search_versions_returns_current_then_previous(retriever: Retriever) -> None:
    hits = retriever.search_versions("alpha", "s", k_each=1, language="en", which="both")
    assert ids(hits) == ["new-a", "old-a"]
    assert [h.rank for h in hits] == [1, 2]
    assert ids(retriever.search_versions("alpha", "s", 1, "en", "current")) == ["new-a"]
    assert ids(retriever.search_versions("alpha", "s", 1, "en", "previous")) == ["old-a"]


def test_search_versions_needs_a_registry(tmp_path: Path) -> None:
    r = Retriever(CHUNKS, FakeEmbedder(), EmbeddingCache(tmp_path, MODEL))
    with pytest.raises(ValueError, match="registry"):
        r.search_versions("alpha", "s")


def test_embeddings_are_cached_across_instances(tmp_path: Path) -> None:
    e1 = FakeEmbedder()
    r1 = Retriever(CHUNKS, e1, EmbeddingCache(tmp_path, MODEL))
    assert r1.computed == len(CHUNKS)
    r1.search("alpha", 1)
    r1.search("alpha", 1)  # same query: no second encode
    assert e1.encoded == len(CHUNKS) + 1

    e2 = FakeEmbedder()
    r2 = Retriever(CHUNKS, e2, EmbeddingCache(tmp_path, MODEL))
    assert r2.computed == 0 and e2.encoded == 0
    assert np.allclose(r1.matrix, r2.matrix)


def test_cache_key_changes_with_model_revision_prefix_and_text() -> None:
    base = text_key(MODEL, "passage", "x")
    assert base != text_key(MODEL, "query", "x")
    assert base != text_key(MODEL, "passage", "y")
    pinned = EmbedModel("fake", "fake/model", "q: ", "p: ", revision="abc")
    assert base != text_key(pinned, "passage", "x")


def test_probe_gold_and_summary(retriever: Retriever) -> None:
    probe = Probe(
        id="p1",
        query="alpha alpha",
        query_lang="en",
        doc_lang="en",
        scheme="s",
        version="v1",
        contains="old rule",
    )
    assert gold_ids(probe, CHUNKS) == {"old-a"}
    assert is_gold(probe, CHUNKS[0]) and not is_gold(probe, CHUNKS[1])
    wrong_version = probe.model_copy(update={"id": "p2", "version": "v2", "contains": "new rule"})
    results = evaluate(retriever, [probe, wrong_version])
    assert results[0].first_gold_rank == 1 and not results[0].top1_wrong_version
    assert results[1].first_gold_rank is not None and results[1].first_gold_rank > 1
    assert results[1].top1_wrong_version
    summary = summarise(results)["all"]
    assert summary["n"] == 2 and summary["recall@1"] == 0.5


def test_shipped_probes_all_have_gold_chunks(root: Path) -> None:
    from policydrift.retrieval.probes import load_probes
    from policydrift.retrieval.search import load_chunks

    chunks = load_chunks(root / "data" / "processed" / "chunks.jsonl")
    probes = load_probes(root / "data" / "probes" / "retrieval_probes.jsonl")
    assert len(probes) >= 30
    assert {p.query_lang for p in probes} == {"en", "hi", "gu"}
    assert [p.id for p in probes if not gold_ids(p, chunks)] == []
    assert len({p.id for p in probes}) == len(probes)
