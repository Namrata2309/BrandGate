"""Small OpenAI-compatible chat-completions adapter (Groq/OpenRouter-compatible).

Only the backend should use this module. API keys are read from environment
variables and must never be sent to the browser or logged.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

import httpx


@dataclass(frozen=True)
class LLMSettings:
    api_key: str
    base_url: str
    model: str
    timeout_seconds: float = 35.0
    max_tokens: int = 1_400

    @property
    def configured(self) -> bool:
        return bool(self.api_key.strip() and self.base_url.strip() and self.model.strip())

    @classmethod
    def from_environment(cls) -> "LLMSettings":
        return cls(
            api_key=os.getenv("LLM_API_KEY", "").strip(),
            base_url=os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1").strip().rstrip("/"),
            model=os.getenv("LLM_MODEL", "").strip(),
            timeout_seconds=_positive_float(os.getenv("LLM_TIMEOUT_SECONDS", "35"), 35.0),
            max_tokens=_positive_int(os.getenv("LLM_MAX_TOKENS", "1400"), 1400),
        )


def _positive_float(value: str, fallback: float) -> float:
    try:
        parsed = float(value)
        return parsed if parsed > 0 else fallback
    except (TypeError, ValueError):
        return fallback


def _positive_int(value: str, fallback: int) -> int:
    try:
        parsed = int(value)
        return parsed if parsed > 0 else fallback
    except (TypeError, ValueError):
        return fallback


class LLMProviderError(Exception):
    """Safe, user-facing provider error; intentionally excludes raw provider body."""

    def __init__(self, code: str, safe_message: str):
        super().__init__(safe_message)
        self.code = code
        self.safe_message = safe_message


class OpenAICompatibleProvider:
    """One adapter for providers exposing POST /chat/completions."""

    def __init__(self, settings: LLMSettings | None = None):
        self.settings = settings or LLMSettings.from_environment()

    @property
    def configured(self) -> bool:
        return self.settings.configured

    async def complete_json(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        if not self.configured:
            raise LLMProviderError(
                "not_configured",
                "LLM is not configured. Set LLM_API_KEY and LLM_MODEL in backend/.env.",
            )

        endpoint = f"{self.settings.base_url}/chat/completions"
        payload = {
            "model": self.settings.model,
            "temperature": 0.1,
            "max_tokens": self.settings.max_tokens,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        headers = {
            "Authorization": f"Bearer {self.settings.api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(self.settings.timeout_seconds)
            ) as client:
                response = await client.post(endpoint, json=payload, headers=headers)
        except httpx.TimeoutException as exc:
            raise LLMProviderError(
                "provider_unavailable",
                "The AI provider timed out. Local findings are still available; try again later.",
            ) from exc
        except httpx.RequestError as exc:
            raise LLMProviderError(
                "provider_unavailable",
                "The AI provider could not be reached. Check the connection and try again.",
            ) from exc

        if response.status_code == 429:
            raise LLMProviderError(
                "rate_limited",
                "The AI provider rate limit or quota was reached. Local findings are still available; retry later.",
            )
        if response.status_code in (401, 403):
            raise LLMProviderError(
                "authentication_failed",
                "The AI provider rejected the credentials or access. Check the backend configuration.",
            )
        if response.status_code >= 500:
            raise LLMProviderError(
                "provider_unavailable",
                "The AI provider is temporarily unavailable. Local findings are still available.",
            )
        if response.status_code < 200 or response.status_code >= 300:
            raise LLMProviderError(
                "provider_error",
                f"The AI provider rejected the request (HTTP {response.status_code}). Check the selected model and provider settings.",
            )

        try:
            body = response.json()
            content = body["choices"][0]["message"]["content"]
            parsed = parse_json_object(content)
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise LLMProviderError(
                "invalid_response",
                "The AI provider returned an unreadable response. Local findings are still available.",
            ) from exc

        return parsed


def parse_json_object(content: Any) -> dict[str, Any]:
    """Parse a JSON object returned by the model, tolerating a code fence only."""
    if not isinstance(content, str):
        raise ValueError("Model content is not a string")
    text = content.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if len(lines) >= 3 and lines[-1].strip().startswith("```"):
            text = "\n".join(lines[1:-1]).strip()
            if text.casefold().startswith("json"):
                text = text[4:].strip()
    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        raise ValueError("Model response must be a JSON object")
    return parsed

