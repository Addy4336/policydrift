"""Request and response types shared by every provider."""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict

ProviderName = Literal["gemini", "groq"]


class LLMRequest(BaseModel):
    """Everything that can change a model's output. The cache key is derived from all of it."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    provider: ProviderName
    model: str
    prompt: str
    system: str | None = None
    temperature: float = 0.0
    max_tokens: int = 1024
    seed: int | None = None
    json_mode: bool = False
    # Free-form label for logs ("draft", "judge", ...). Excluded from the cache key.
    purpose: str = ""

    def cache_key(self) -> str:
        body = self.model_dump(exclude={"purpose"})
        canonical = json.dumps(body, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class LLMResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str
    provider: ProviderName
    model: str  # the model id that was requested
    model_version: str | None = None  # the version string the provider reports, if any
    input_tokens: int | None = None
    output_tokens: int | None = None
    latency_s: float = 0.0
    cached: bool = False
    created_at: str = ""  # UTC ISO timestamp of the original (uncached) call
    max_tokens: int | None = None  # token budget of the request that produced it (set by callers)


class LLMError(RuntimeError):
    """A provider call failed after all retries."""
