import json

import httpx
import pytest

from website_brochure.fetcher import PageContent
from website_brochure.llm import OllamaGenerator, OpenAIGenerator, ProviderError
from website_brochure.models import BrochureCategory


PAGE = PageContent(
    source_url="https://example.com/program",
    title="Northstar Learning Studio",
    text=(
        "Northstar runs practical product workshops for working teams. "
        "The program uses guided exercises for discovery and prioritization. "
        "Organizations may request a program outline through the inquiry form."
    ),
)

MODEL_OUTPUT = {
    "status": "ready",
    "factual_summary": "Northstar runs practical product workshops for working teams.",
    "brochure": {
        "headline": "Practical workshops for product teams",
        "introduction": "Guided exercises help working teams practice discovery and prioritization together.",
        "sections": [
            {
                "heading": "Team practice",
                "body": "The program gives product teams guided, practical exercises.",
            },
            {
                "heading": "Program focus",
                "body": "Workshop material covers product discovery and prioritization.",
            },
        ],
        "call_to_action": "Request a program outline through the inquiry form.",
    },
    "feedback": None,
}


def _install_mock_transport(
    monkeypatch: pytest.MonkeyPatch, handler
) -> None:
    real_async_client = httpx.AsyncClient
    transport = httpx.MockTransport(handler)

    def client_factory(*args, **kwargs):
        return real_async_client(*args, transport=transport, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", client_factory)


@pytest.mark.asyncio
async def test_openai_generation_uses_responses_schema_and_category(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen_payload = None

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal seen_payload
        seen_payload = json.loads(request.content)
        assert request.url == "https://api.openai.com/v1/responses"
        assert request.headers["Authorization"] == "Bearer test-key"
        return httpx.Response(
            200,
            json={
                "output": [
                    {
                        "type": "message",
                        "content": [
                            {"type": "output_text", "text": json.dumps(MODEL_OUTPUT)}
                        ],
                    }
                ]
            },
        )

    _install_mock_transport(monkeypatch, handler)
    generator = OpenAIGenerator("test-key", "test-model")

    result = await generator.generate(PAGE, BrochureCategory.SPOTLIGHT)

    assert result.status == "ready"
    assert seen_payload is not None
    assert seen_payload["text"]["format"]["strict"] is True
    assert "Product or Service Spotlight" in seen_payload["input"][1]["content"][0]["text"]


@pytest.mark.asyncio
async def test_ollama_generation_needs_no_openai_key_and_sends_category(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen_payload = None

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal seen_payload
        seen_payload = json.loads(request.content)
        assert request.url == "http://localhost:11434/api/chat"
        assert "Authorization" not in request.headers
        return httpx.Response(
            200,
            json={"message": {"content": json.dumps(MODEL_OUTPUT)}},
        )

    _install_mock_transport(monkeypatch, handler)
    generator = OllamaGenerator("http://localhost:11434", "llama3.2:3b")

    result = await generator.generate(PAGE, BrochureCategory.EVENT)

    assert result.status == "ready"
    assert seen_payload is not None
    assert seen_payload["model"] == "llama3.2:3b"
    assert "Event or Program Overview" in seen_payload["messages"][1]["content"]


@pytest.mark.asyncio
async def test_unavailable_ollama_explains_how_to_recover(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    _install_mock_transport(monkeypatch, handler)

    with pytest.raises(ProviderError, match="Confirm it is running and the base URL"):
        await OllamaGenerator("http://localhost:11434", "missing-model").generate(
            PAGE, BrochureCategory.BUSINESS
        )


@pytest.mark.asyncio
async def test_missing_ollama_model_explains_pull_requirement(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"error": "model not found"})

    _install_mock_transport(monkeypatch, handler)

    with pytest.raises(ProviderError, match="model has been pulled"):
        await OllamaGenerator("http://localhost:11434", "missing-model").generate(
            PAGE, BrochureCategory.BUSINESS
        )
