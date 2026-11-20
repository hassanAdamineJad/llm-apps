from pathlib import Path

from fastapi.testclient import TestClient

from website_brochure.app import create_app
from website_brochure.fetcher import PageContent, PageFetchError, extract_readable_text, fetch_page
from website_brochure.llm import GenerationResult, ProviderError
from website_brochure.models import BrochureCategory, GeneratedContent, GenerationMetrics
from website_brochure.settings import ConfigurationError


FIXTURE = Path(__file__).parent / "fixtures" / "example_page.html"


class FakeGenerator:
    def __init__(self) -> None:
        self.seen_category: BrochureCategory | None = None

    async def generate(
        self, page: PageContent, category: BrochureCategory
    ) -> GenerationResult:
        self.seen_category = category
        assert "product discovery" in page.text
        content = GeneratedContent.model_validate(
            {
                "status": "ready",
                "factual_summary": "Northstar provides practical workshops for cross-functional product teams.",
                "brochure": {
                    "headline": "Practical learning for product teams",
                    "introduction": "Facilitated workshops give working teams realistic exercises and repeatable methods.",
                    "sections": [
                        {
                            "heading": "Relevant exercises",
                            "body": "Teams practice discovery, prioritization, and clear written decisions.",
                        },
                        {
                            "heading": "Flexible programs",
                            "body": "The source offers half-day workshops and multi-session learning series.",
                        },
                    ],
                    "call_to_action": "Request a program outline through the page inquiry form.",
                },
                "feedback": None,
            }
        )
        metrics = GenerationMetrics(
            provider="openai",
            model="test-model",
            input_tokens=120,
            output_tokens=0,
            total_tokens=120,
            cached_input_tokens=0,
            cache_hit_ratio=0.0,
            estimated_cost_usd=0.000048,
            latency_ms=1250,
            success=True,
        )
        return GenerationResult(content, metrics)


def test_ui_is_served() -> None:
    client = TestClient(create_app())

    response = client.get("/")

    assert response.status_code == 200
    assert "Website Brochure" in response.text
    assert "Create a brochure" in response.text
    assert "We’ll use the text on this page." in response.text
    assert "Example" in response.text
    assert "Source summary" in response.text
    assert "Generation metrics" in response.text
    assert "Cached tokens" in response.text
    assert "Cache hit" in response.text
    assert "Est. API cost" in response.text


def test_frontend_keeps_rendering_safe_and_appearance_changes_local() -> None:
    static_dir = Path(__file__).parents[1] / "src" / "website_brochure" / "static"
    script = (static_dir / "app.js").read_text()
    styles = (static_dir / "styles.css").read_text()

    assert "innerHTML" not in script
    assert script.count('fetch("/api/generate"') == 1
    assert "applyTheme(button.dataset.theme)" in script
    assert "applyAccent(accentColor.value)" in script
    assert "renderGenerationMetrics(data.generation_metrics)" in script
    assert "metrics.cached_input_tokens" in script
    assert "metrics.cache_hit_ratio" in script
    assert "metrics.estimated_cost_usd" in script
    assert 'value === null || value === undefined || value === ""' in script
    assert "@media (max-width: 640px)" in styles
    assert "@media print" in styles


def test_generation_with_fixture_page_and_fake_provider() -> None:
    fake_generator = FakeGenerator()

    async def fixture_fetcher(url: str) -> PageContent:
        assert url == "https://example.com/program"
        return extract_readable_text(FIXTURE.read_bytes(), url)

    app = create_app(
        page_fetcher=fixture_fetcher,
        generator_factory=lambda: fake_generator,
    )
    client = TestClient(app)

    response = client.post(
        "/api/generate",
        json={
            "website_url": "https://example.com/program",
            "category": "event_program_overview",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["source_url"] == "https://example.com/program"
    assert body["factual_summary"] != body["brochure"]["introduction"]
    assert body["brochure"]["sections"][0]["heading"] == "Relevant exercises"
    assert body["generation_metrics"] == {
        "provider": "openai",
        "model": "test-model",
        "input_tokens": 120,
        "output_tokens": 0,
        "total_tokens": 120,
        "cached_input_tokens": 0,
        "cache_hit_ratio": 0.0,
        "estimated_cost_usd": 0.000048,
        "latency_ms": 1250.0,
        "success": True,
    }
    assert fake_generator.seen_category is BrochureCategory.EVENT


def test_browser_gets_readable_configuration_error() -> None:
    def missing_configuration():
        raise ConfigurationError("LLM_PROVIDER must be either 'openai' or 'ollama'.")

    client = TestClient(create_app(generator_factory=missing_configuration))

    response = client.post(
        "/api/generate",
        json={
            "website_url": "https://example.com/",
            "category": "business_overview",
        },
    )

    assert response.status_code == 503
    assert response.json() == {
        "detail": "LLM_PROVIDER must be either 'openai' or 'ollama'."
    }


def test_invalid_url_returns_actionable_error() -> None:
    client = TestClient(create_app(generator_factory=FakeGenerator))

    response = client.post(
        "/api/generate",
        json={"website_url": "not a URL", "category": "business_overview"},
    )

    assert response.status_code == 422
    assert response.json() == {
        "detail": "Enter a valid public website URL beginning with http:// or https://."
    }


def test_blocked_destination_returns_actionable_error() -> None:
    fake_generator = FakeGenerator()
    client = TestClient(
        create_app(page_fetcher=fetch_page, generator_factory=lambda: fake_generator)
    )

    response = client.post(
        "/api/generate",
        json={"website_url": "http://127.0.0.1/private", "category": "business_overview"},
    )

    assert response.status_code == 422
    assert "local, private, link-local, or reserved" in response.json()["detail"]
    assert fake_generator.seen_category is None


def test_sparse_page_returns_javascript_guidance() -> None:
    async def sparse_fetcher(url: str) -> PageContent:
        return extract_readable_text("<html><body><div id='app'></div></body></html>", url)

    client = TestClient(
        create_app(page_fetcher=sparse_fetcher, generator_factory=FakeGenerator)
    )

    response = client.post(
        "/api/generate",
        json={"website_url": "https://example.com/sparse", "category": "business_overview"},
    )

    assert response.status_code == 422
    assert "JavaScript" in response.json()["detail"]


def test_invalid_model_response_is_safe_and_readable() -> None:
    class InvalidGenerator:
        async def generate(self, page, category):
            raise ProviderError(
                "The model returned an invalid brochure. Try again or choose a different model."
            )

    async def fixture_fetcher(url: str) -> PageContent:
        return extract_readable_text(FIXTURE.read_bytes(), url)

    client = TestClient(
        create_app(
            page_fetcher=fixture_fetcher,
            generator_factory=InvalidGenerator,
        )
    )

    response = client.post(
        "/api/generate",
        json={"website_url": "https://example.com/program", "category": "business_overview"},
    )

    assert response.status_code == 502
    assert response.json() == {
        "detail": "The model returned an invalid brochure. Try again or choose a different model."
    }


def test_request_can_be_retried_after_page_failure() -> None:
    attempts = 0
    fake_generator = FakeGenerator()

    async def flaky_fetcher(url: str) -> PageContent:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise PageFetchError("Temporary fixture failure. Correct the input and try again.")
        return extract_readable_text(FIXTURE.read_bytes(), url)

    client = TestClient(
        create_app(
            page_fetcher=flaky_fetcher,
            generator_factory=lambda: fake_generator,
        )
    )
    payload = {
        "website_url": "https://example.com/program",
        "category": "event_program_overview",
    }

    first = client.post("/api/generate", json=payload)
    second = client.post("/api/generate", json=payload)

    assert first.status_code == 422
    assert second.status_code == 200
    assert attempts == 2
    assert fake_generator.seen_category is BrochureCategory.EVENT

