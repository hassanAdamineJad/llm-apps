import pytest

from website_brochure.llm import OllamaGenerator, OpenAIGenerator, create_generator
from website_brochure.settings import ConfigurationError, ProviderName, Settings


def test_openai_validates_only_openai_settings() -> None:
    settings = Settings.from_env(
        {
            "LLM_PROVIDER": "openai",
            "OPENAI_API_KEY": "test-key",
            "OPENAI_MODEL": "test-model",
            "OLLAMA_BASE_URL": "not a url",
            "OLLAMA_MODEL": "",
        }
    )

    assert settings.provider is ProviderName.OPENAI


def test_ollama_does_not_require_openai_key() -> None:
    settings = Settings.from_env(
        {
            "LLM_PROVIDER": "ollama",
            "OPENAI_API_KEY": "",
            "OPENAI_MODEL": "",
            "OLLAMA_BASE_URL": "http://localhost:11434",
            "OLLAMA_MODEL": "llama3.2:3b",
        }
    )

    assert settings.provider is ProviderName.OLLAMA


@pytest.mark.parametrize("provider", ["", "bedrock", "OPEN AI"])
def test_unknown_provider_is_rejected(provider: str) -> None:
    with pytest.raises(ConfigurationError, match="LLM_PROVIDER"):
        Settings.from_env({"LLM_PROVIDER": provider})


def test_selected_provider_reports_missing_values() -> None:
    with pytest.raises(ConfigurationError, match="OPENAI_API_KEY, OPENAI_MODEL"):
        Settings.from_env({"LLM_PROVIDER": "openai"})


def test_generator_factory_follows_selected_provider() -> None:
    openai = Settings.from_env(
        {
            "LLM_PROVIDER": "openai",
            "OPENAI_API_KEY": "test-key",
            "OPENAI_MODEL": "test-model",
        }
    )
    ollama = Settings.from_env(
        {
            "LLM_PROVIDER": "ollama",
            "OLLAMA_BASE_URL": "http://localhost:11434",
            "OLLAMA_MODEL": "test-model",
        }
    )

    assert isinstance(create_generator(openai), OpenAIGenerator)
    assert isinstance(create_generator(ollama), OllamaGenerator)

