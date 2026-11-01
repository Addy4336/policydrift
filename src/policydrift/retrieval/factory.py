"""Build the default local retriever (e5-base, exact search) from the repository files."""

from __future__ import annotations

from pathlib import Path

from policydrift.ingest.registry import load_registry
from policydrift.retrieval.embed import (
    DEFAULT_MODEL,
    MODELS,
    EmbeddingCache,
    SentenceTransformerEmbedder,
)
from policydrift.retrieval.search import Retriever, load_chunks


def local_retriever(root: Path) -> Retriever:
    model = MODELS[DEFAULT_MODEL]
    chunks = load_chunks(root / "data" / "processed" / "chunks.jsonl")
    registry = load_registry(root / "data" / "schemes.yaml")
    cache = EmbeddingCache(root / ".cache" / "embeddings", model)
    return Retriever(chunks, SentenceTransformerEmbedder(model), cache, registry)
