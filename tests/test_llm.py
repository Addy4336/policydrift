from pathlib import Path

import httpx
import pytest

from policydrift.llm import LLMClient, LLMError, LLMRequest, ResponseCache
from policydrift.llm.limiter import RateLimiter
from policydrift.llm.providers import PROVIDERS


def _req(**changes: object) -> LLMRequest:
    base = LLMRequest(provider="groq", model="m", prompt="hello")
    return base.model_copy(update=changes)


def _groq_ok(text: str = "hi") -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "model": "m-0001",
            "choices": [{"message": {"content": text}}],
            "usage": {"prompt_tokens": 3, "completion_tokens": 1},
        },
    )


def _client(tmp_path: Path, handler: httpx.MockTransport, **kw: object) -> LLMClient:
    sleeps: list[float] = []
    client = LLMClient(
        ResponseCache(tmp_path / "c.sqlite"),
        {"groq": "k", "gemini": "k"},
        {"groq": 100, "gemini": 100},
        http=httpx.Client(transport=handler),
        sleep=sleeps.append,
        **kw,  # type: ignore[arg-type]
    )
    client.sleeps = sleeps  # type: ignore[attr-defined]
    return client


def test_cache_key_ignores_purpose_but_not_content() -> None:
    assert _req(purpose="a").cache_key() == _req(purpose="b").cache_key()
    assert _req().cache_key() != _req(prompt="other").cache_key()
    assert _req().cache_key() != _req(temperature=0.7).cache_key()
    assert _req().cache_key() != _req(model="n").cache_key()


def test_identical_request_is_served_from_cache(tmp_path: Path) -> None:
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return _groq_ok()

    client = _client(tmp_path, httpx.MockTransport(handler))
    first = client.complete(_req())
    second = client.complete(_req(purpose="different label"))
    assert len(calls) == 1 and client.calls_made == 1
    assert not first.cached and second.cached
    assert second.text == "hi" and second.model_version == "m-0001"
    assert (second.input_tokens, second.output_tokens) == (3, 1)


def test_cache_survives_a_new_client(tmp_path: Path) -> None:
    client = _client(tmp_path, httpx.MockTransport(lambda r: _groq_ok()))
    client.complete(_req())

    def boom(request: httpx.Request) -> httpx.Response:
        raise AssertionError("should not reach the network")

    again = _client(tmp_path, httpx.MockTransport(boom))
    assert again.complete(_req()).cached


def test_retries_on_429_and_5xx_then_succeeds(tmp_path: Path) -> None:
    replies = iter([httpx.Response(429), httpx.Response(503), _groq_ok("done")])
    client = _client(tmp_path, httpx.MockTransport(lambda r: next(replies)))
    assert client.complete(_req()).text == "done"
    assert len(client.sleeps) == 2  # type: ignore[attr-defined]


def test_retry_after_header_is_honoured(tmp_path: Path) -> None:
    replies = iter([httpx.Response(429, headers={"retry-after": "7"}), _groq_ok()])
    client = _client(tmp_path, httpx.MockTransport(lambda r: next(replies)))
    client.complete(_req())
    assert client.sleeps == [7.0]  # type: ignore[attr-defined]


def test_client_errors_are_not_retried_and_failures_are_not_cached(tmp_path: Path) -> None:
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return httpx.Response(400, text="bad request")

    client = _client(tmp_path, httpx.MockTransport(handler))
    with pytest.raises(LLMError, match="HTTP 400"):
        client.complete(_req())
    assert len(calls) == 1
    with pytest.raises(LLMError):
        client.complete(_req())
    assert len(calls) == 2


def test_gives_up_after_max_attempts(tmp_path: Path) -> None:
    client = _client(tmp_path, httpx.MockTransport(lambda r: httpx.Response(503)), max_attempts=3)
    with pytest.raises(LLMError, match="after 3 attempts"):
        client.complete(_req())


def test_missing_key_fails_before_any_request(tmp_path: Path) -> None:
    client = LLMClient(
        ResponseCache(tmp_path / "c.sqlite"),
        {"groq": ""},
        {"groq": 10},
        http=httpx.Client(transport=httpx.MockTransport(lambda r: _groq_ok())),
    )
    with pytest.raises(LLMError, match="GROQ_API_KEY"):
        client.complete(_req())


def test_rate_limiter_blocks_the_request_over_the_limit() -> None:
    now = [0.0]
    slept: list[float] = []

    def sleep(seconds: float) -> None:
        slept.append(seconds)
        now[0] += seconds

    limiter = RateLimiter(2, clock=lambda: now[0], sleep=sleep)
    limiter.wait()
    limiter.wait()
    assert slept == []
    limiter.wait()
    assert len(slept) == 1 and 59.9 < slept[0] < 60.1


def test_provider_payloads_keep_keys_out_of_urls_and_parse_replies() -> None:
    req = _req(system="be brief", seed=1, json_mode=True)
    groq = PROVIDERS["groq"].build(req, "SECRET")
    assert "SECRET" not in groq.url and groq.headers["authorization"] == "Bearer SECRET"
    assert groq.body["messages"][0] == {"role": "system", "content": "be brief"}
    assert groq.body["response_format"] == {"type": "json_object"}

    gem = PROVIDERS["gemini"].build(req.model_copy(update={"provider": "gemini"}), "SECRET")
    assert "SECRET" not in gem.url and gem.headers["x-goog-api-key"] == "SECRET"
    assert gem.body["generationConfig"]["responseMimeType"] == "application/json"
    parsed = PROVIDERS["gemini"].parse(
        {
            "candidates": [{"content": {"parts": [{"text": "a"}, {"text": "b"}]}}],
            "usageMetadata": {"promptTokenCount": 5, "candidatesTokenCount": 2},
            "modelVersion": "v9",
        }
    )
    assert (parsed.text, parsed.input_tokens, parsed.output_tokens, parsed.model_version) == (
        "ab",
        5,
        2,
        "v9",
    )
