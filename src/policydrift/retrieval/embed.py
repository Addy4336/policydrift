"""Embedding models and an on-disk cache so no text is ever embedded twice."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import numpy as np
from numpy.typing import NDArray

Matrix = NDArray[np.float32]


@dataclass(frozen=True)
class EmbedModel:
    """A sentence-embedding model plus the prefixes it expects for queries and passages."""

    key: str  # short name used in configs and cache paths
    hf_name: str
    query_prefix: str = ""
    passage_prefix: str = ""
    revision: str | None = None  # pin to a Hugging Face commit once chosen


MODELS: dict[str, EmbedModel] = {
    "bge-m3": EmbedModel("bge-m3", "BAAI/bge-m3"),
    # Chosen on the dev probes (see docs/retrieval.md); revision pinned for reproducibility.
    "e5-base": EmbedModel(
        "e5-base",
        "intfloat/multilingual-e5-base",
        "query: ",
        "passage: ",
        revision="d128750597153bb5987e10b1c3493a34e5a4502a",
    ),
}

DEFAULT_MODEL = "e5-base"


class Embedder(Protocol):
    model: EmbedModel

    def encode(self, texts: Sequence[str]) -> Matrix: ...


class SentenceTransformerEmbedder:
    """Wraps ``sentence_transformers`` on CPU; returns L2-normalised float32 vectors."""

    def __init__(self, model: EmbedModel, batch_size: int = 8) -> None:
        from sentence_transformers import SentenceTransformer

        self.model = model
        self.batch_size = batch_size
        self._st = SentenceTransformer(model.hf_name, revision=model.revision, device="cpu")

    def encode(self, texts: Sequence[str]) -> Matrix:
        vectors = self._st.encode(
            list(texts),
            batch_size=self.batch_size,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        return np.asarray(vectors, dtype=np.float32)


def text_key(model: EmbedModel, role: str, text: str) -> str:
    """Cache key: changes if the model, its revision, the role prefix or the text changes."""
    prefix = model.query_prefix if role == "query" else model.passage_prefix
    payload = json.dumps([model.hf_name, model.revision, prefix, text], ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class EmbeddingCache:
    """One ``.npz`` per model holding vectors keyed by :func:`text_key`."""

    def __init__(self, cache_dir: Path, model: EmbedModel) -> None:
        self.path = cache_dir / f"{model.key}.npz"
        self._vectors: dict[str, Matrix] = {}
        if self.path.is_file():
            with np.load(self.path) as data:
                keys = [str(k) for k in data["keys"]]
                matrix = data["vectors"]
                self._vectors = {k: matrix[i] for i, k in enumerate(keys)}

    def __len__(self) -> int:
        return len(self._vectors)

    def get_or_compute(
        self, embedder: Embedder, role: str, texts: Sequence[str]
    ) -> tuple[Matrix, int]:
        """Return vectors for ``texts`` and the number that had to be computed."""
        model = embedder.model
        prefix = model.query_prefix if role == "query" else model.passage_prefix
        keys = [text_key(model, role, t) for t in texts]
        missing = sorted({i for i, k in enumerate(keys) if k not in self._vectors})
        if missing:
            computed = embedder.encode([prefix + texts[i] for i in missing])
            for i, vector in zip(missing, computed, strict=True):
                self._vectors[keys[i]] = vector
            self._save()
        return np.stack([self._vectors[k] for k in keys]), len(missing)

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        keys = sorted(self._vectors)
        np.savez(
            self.path,
            keys=np.array(keys),
            vectors=np.stack([self._vectors[k] for k in keys]),
        )
