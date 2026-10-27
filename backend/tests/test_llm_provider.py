import pytest

from app.services.llm_provider import (
    LLMProviderError,
    LLMSettings,
    OpenAICompatibleProvider,
    parse_json_object,
)


class FakeResponse:
    def __init__(self, status_code, body):
        self.status_code = status_code
        self._body = body

    def json(self):
        return self._body


class FakeAsyncClient:
    def __init__(self, response=None, **kwargs):
        self.response = response
        self.kwargs = kwargs
        self.last_request = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url, json, headers):
        self.last_request = {"url": url, "json": json, "headers": headers}
        return self.response


@pytest.mark.asyncio
async def test_provider_returns_json_object(monkeypatch):
    fake = FakeAsyncClient(FakeResponse(200, {
        "choices": [{"message": {"content": '{"summary":"ok","findings":[]}'}}]
    }))
    monkeypatch.setattr("app.services.llm_provider.httpx.AsyncClient", lambda **kwargs: fake)
    settings = LLMSettings(
        api_key="test-key",
        base_url="https://llm.test/v1",
        model="test-model",
    )
    result = await OpenAICompatibleProvider(settings).complete_json("system", "user")
    assert result == {"summary": "ok", "findings": []}
    assert fake.last_request["url"] == "https://llm.test/v1/chat/completions"
    assert fake.last_request["headers"]["Authorization"] == "Bearer test-key"


@pytest.mark.asyncio
async def test_provider_maps_rate_limit_to_safe_error(monkeypatch):
    fake = FakeAsyncClient(FakeResponse(429, {"error": {"message": "private provider body"}}))
    monkeypatch.setattr("app.services.llm_provider.httpx.AsyncClient", lambda **kwargs: fake)
    settings = LLMSettings(api_key="test-key", base_url="https://llm.test/v1", model="test-model")
    with pytest.raises(LLMProviderError) as caught:
        await OpenAICompatibleProvider(settings).complete_json("system", "user")
    assert caught.value.code == "rate_limited"
    assert "private provider body" not in str(caught.value)


def test_parse_json_object_accepts_a_json_code_fence():
    assert parse_json_object('```json\n{"findings": []}\n```') == {"findings": []}


def test_parse_json_object_rejects_array():
    with pytest.raises(ValueError):
        parse_json_object('[{"not": "an object"}]')
