"""The one place that talks to LLM providers: cached, rate-limited, with retries."""

from __future__ import annotations

import os
import time
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from pathlib import Path

import httpx
import yaml

from policydrift.db import read_env_file
from policydrift.llm.cache import ResponseCache
from policydrift.llm.limiter import RateLimiter
from policydrift.llm.providers import PROVIDERS
from policydrift.llm.types import LLMError, LLMRequest, LLMResponse

KEY_VARS = {"gemini": "GEMINI_API_KEY", "groq": "GROQ_API_KEY"}
RETRYABLE = {429, 500, 502, 503, 504}


class LLMClient:
    def __init__(
        self,
        cache: ResponseCache,
        api_keys: Mapping[str, str],
        rpm: Mapping[str, int],
        http: httpx.Client | None = None,
        max_attempts: int = 5,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._cache = cache
        self._keys = dict(api_keys)
        self._http = http or httpx.Client(timeout=120.0)
        self._max_attempts = max_attempts
        self._sleep = sleep
        self._limiters = {p: RateLimiter(n, clock=clock, sleep=sleep) for p, n in rpm.items()}
        self.calls_made = 0  # uncached provider calls, for budgeting

    def is_cached(self, request: LLMRequest) -> bool:
        return self._cache.get(request) is not None

    def complete(self, request: LLMRequest) -> LLMResponse:
        hit = self._cache.get(request)
        if hit is not None:
            return hit
        key = self._keys.get(request.provider)
        if not key:
            raise LLMError(f"no API key for {request.provider}; set {KEY_VARS[request.provider]}")
        limiter = self._limiters.get(request.provider)
        provider = PROVIDERS[request.provider]
        call = provider.build(request, key)
        last = "no attempt made"
        for attempt in range(self._max_attempts):
            if limiter:
                limiter.wait()
            started = time.monotonic()
            try:
                reply = self._http.post(call.url, headers=call.headers, json=call.body)
            except httpx.TransportError as exc:
                last = f"{type(exc).__name__}"
            else:
                if reply.status_code == 200:
                    parsed = provider.parse(reply.json())
                    if not parsed.text.strip():
                        raise LLMError(f"{request.provider} returned an empty completion")
                    response = LLMResponse(
                        text=parsed.text,
                        provider=request.provider,
                        model=request.model,
                        model_version=parsed.model_version,
                        input_tokens=parsed.input_tokens,
                        output_tokens=parsed.output_tokens,
                        latency_s=round(time.monotonic() - started, 3),
                        created_at=datetime.now(UTC).isoformat(timespec="seconds"),
                    )
                    self.calls_made += 1
                    self._cache.put(request, response)
                    return response
                last = f"HTTP {reply.status_code}"
                if reply.status_code not in RETRYABLE:
                    raise LLMError(f"{request.provider} failed: {last}: {reply.text[:200]}")
                retry_after = reply.headers.get("retry-after")
                if retry_after and retry_after.replace(".", "", 1).isdigit():
                    self._sleep(min(float(retry_after), 120.0))
                    continue
            self._sleep(min(2.0**attempt, 60.0))
        raise LLMError(f"{request.provider} failed after {self._max_attempts} attempts: {last}")


def load_models(path: Path) -> dict[str, object]:
    with path.open(encoding="utf-8") as f:
        loaded: dict[str, object] = yaml.safe_load(f)
    return loaded


def client_from_root(root: Path, http: httpx.Client | None = None) -> LLMClient:
    """Build a client from ``configs/models.yaml``, ``.env`` and the cache under ``.cache/``."""
    config = load_models(root / "configs" / "models.yaml")
    rpm_raw = config["requests_per_minute"]
    assert isinstance(rpm_raw, dict)
    env = read_env_file(root / ".env")
    keys = {provider: os.environ.get(var) or env.get(var, "") for provider, var in KEY_VARS.items()}
    cache = ResponseCache(root / ".cache" / "llm.sqlite")
    return LLMClient(cache, keys, {str(k): int(v) for k, v in rpm_raw.items()}, http=http)
