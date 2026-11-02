"""Provider adapters over plain HTTPS (no vendor SDKs). API keys travel in headers, never URLs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from policydrift.llm.types import LLMRequest


@dataclass(frozen=True)
class HttpCall:
    url: str
    headers: dict[str, str]
    body: dict[str, Any]


@dataclass(frozen=True)
class ParsedReply:
    text: str
    model_version: str | None
    input_tokens: int | None
    output_tokens: int | None
    finish_reason: str | None = None


class Provider(Protocol):
    name: str

    def build(self, request: LLMRequest, api_key: str) -> HttpCall: ...

    def parse(self, payload: dict[str, Any]) -> ParsedReply: ...


class GeminiProvider:
    name = "gemini"
    base = "https://generativelanguage.googleapis.com/v1beta/models"

    def build(self, request: LLMRequest, api_key: str) -> HttpCall:
        config: dict[str, Any] = {
            "temperature": request.temperature,
            "maxOutputTokens": request.max_tokens,
        }
        if request.seed is not None:
            config["seed"] = request.seed
        if request.json_mode:
            config["responseMimeType"] = "application/json"
        body: dict[str, Any] = {
            "contents": [{"role": "user", "parts": [{"text": request.prompt}]}],
            "generationConfig": config,
        }
        if request.system:
            body["systemInstruction"] = {"parts": [{"text": request.system}]}
        return HttpCall(
            url=f"{self.base}/{request.model}:generateContent",
            headers={"x-goog-api-key": api_key, "content-type": "application/json"},
            body=body,
        )

    def parse(self, payload: dict[str, Any]) -> ParsedReply:
        candidates = payload.get("candidates") or []
        parts = (candidates[0].get("content") or {}).get("parts", []) if candidates else []
        text = "".join(p.get("text", "") for p in parts)
        usage = payload.get("usageMetadata") or {}
        return ParsedReply(
            text=text,
            model_version=payload.get("modelVersion"),
            input_tokens=usage.get("promptTokenCount"),
            output_tokens=usage.get("candidatesTokenCount"),
            finish_reason=(candidates[0].get("finishReason") if candidates else None),
        )


class GroqProvider:
    name = "groq"
    url = "https://api.groq.com/openai/v1/chat/completions"

    def build(self, request: LLMRequest, api_key: str) -> HttpCall:
        messages: list[dict[str, str]] = []
        if request.system:
            messages.append({"role": "system", "content": request.system})
        messages.append({"role": "user", "content": request.prompt})
        body: dict[str, Any] = {
            "model": request.model,
            "messages": messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }
        if request.seed is not None:
            body["seed"] = request.seed
        if request.json_mode:
            body["response_format"] = {"type": "json_object"}
        return HttpCall(
            url=self.url,
            headers={"authorization": f"Bearer {api_key}", "content-type": "application/json"},
            body=body,
        )

    def parse(self, payload: dict[str, Any]) -> ParsedReply:
        choices = payload.get("choices") or []
        text = (choices[0].get("message") or {}).get("content") or "" if choices else ""
        usage = payload.get("usage") or {}
        return ParsedReply(
            text=text,
            model_version=payload.get("model"),
            input_tokens=usage.get("prompt_tokens"),
            output_tokens=usage.get("completion_tokens"),
            finish_reason=(choices[0].get("finish_reason") if choices else None),
        )


PROVIDERS: dict[str, Provider] = {"gemini": GeminiProvider(), "groq": GroqProvider()}
