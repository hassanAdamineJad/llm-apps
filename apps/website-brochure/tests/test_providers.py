import json

import httpx
import pytest

from website_brochure.fetcher import PageContent
from website_brochure.llm import (
    OllamaGenerator,
    OpenAIGenerator,
    ProviderError,
    _TokenUsage,
    _estimate_openai_cost_usd,
    _extract_ollama_usage,
    _extract_openai_usage,
)
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


def test_extracts_provider_token_usage() -> None:
    openai_usage = _extract_openai_usage(
        {
            "usage": {
                "input_tokens": 120,
                "output_tokens": 45,
                "total_tokens": 165,
                "input_tokens_details": {"cached_tokens": 60},
            }
        }
    )
    ollama_usage = _extract_ollama_usage(
        {
            "prompt_eval_count": 80,
            "prompt_eval_cached_count": 20,
            "eval_count": 30,
        }
    )

    assert (openai_usage.input_tokens, openai_usage.output_tokens) == (120, 45)
    assert openai_usage.total_tokens == 165
    assert openai_usage.cached_input_tokens == 60
    assert (ollama_usage.input_tokens, ollama_usage.output_tokens) == (80, 30)
    assert ollama_usage.total_tokens == 110
    assert ollama_usage.cached_input_tokens == 20


@pytest.mark.parametrize(
    ("extractor", "body"),
    [
        (_extract_openai_usage, {}),
        (_extract_openai_usage, {"usage": {"input_tokens": "unknown"}}),
        (_extract_ollama_usage, {}),
        (_extract_ollama_usage, {"prompt_eval_count": 20}),
    ],
)
def test_unavailable_usage_is_not_estimated(extractor, body) -> None:
    usage = extractor(body)

    if body == {"prompt_eval_count": 20}:
        assert usage.input_tokens == 20
    else:
        assert usage.input_tokens is None
    assert usage.output_tokens is None
    assert usage.total_tokens is None
    assert usage.cached_input_tokens is None


@pytest.mark.parametrize(
    ("model", "usage", "expected_cost"),
    [
        (
            "gpt-4.1-mini",
            _TokenUsage(
                input_tokens=1_000,
                output_tokens=500,
                total_tokens=1_500,
                cached_input_tokens=200,
            ),
            0.00114,
        ),
        (
            "gpt-4.1-mini",
            _TokenUsage(
                input_tokens=1_000,
                output_tokens=500,
                total_tokens=1_500,
                cached_input_tokens=0,
            ),
            0.0012,
        ),
        (
            "unpriced-model",
            _TokenUsage(
                input_tokens=1_000,
                output_tokens=500,
                total_tokens=1_500,
                cached_input_tokens=0,
            ),
            None,
        ),
        (
            "gpt-4.1-mini",
            _TokenUsage(input_tokens=1_000, cached_input_tokens=0),
            None,
        ),
        (
            "gpt-4.1-mini",
            _TokenUsage(input_tokens=1_000, output_tokens=500),
            None,
        ),
    ],
)
def test_openai_cost_estimate_requires_pricing_and_usage(
    model, usage, expected_cost
) -> None:
    assert _estimate_openai_cost_usd(model, usage) == expected_cost


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
                "usage": {
                    "input_tokens": 120,
                    "output_tokens": 45,
                    "total_tokens": 165,
                    "input_tokens_details": {"cached_tokens": 60},
                },
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
    generator = OpenAIGenerator("test-key", "gpt-4.1-mini")

    result = await generator.generate(PAGE, BrochureCategory.SPOTLIGHT)

    assert result.content.status == "ready"
    assert result.metrics.input_tokens == 120
    assert result.metrics.output_tokens == 45
    assert result.metrics.total_tokens == 165
    assert result.metrics.cached_input_tokens == 60
    assert result.metrics.cache_hit_ratio == 0.5
    assert result.metrics.estimated_cost_usd == 0.000102
    assert result.metrics.success is True
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
            json={
                "message": {"content": json.dumps(MODEL_OUTPUT)},
                "prompt_eval_count": 80,
                "prompt_eval_cached_count": 0,
                "eval_count": 30,
            },
        )

    _install_mock_transport(monkeypatch, handler)
    generator = OllamaGenerator("http://localhost:11434", "llama3.2:3b")

    result = await generator.generate(PAGE, BrochureCategory.EVENT)

    assert result.content.status == "ready"
    assert result.metrics.input_tokens == 80
    assert result.metrics.output_tokens == 30
    assert result.metrics.total_tokens == 110
    assert result.metrics.cached_input_tokens == 0
    assert result.metrics.cache_hit_ratio == 0.0
    assert result.metrics.estimated_cost_usd is None
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
