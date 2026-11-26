from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Mapping
from urllib.parse import urlsplit

from dotenv import load_dotenv


APP_ROOT = Path(__file__).resolve().parents[2]


class ConfigurationError(Exception):
    pass


class ProviderName(StrEnum):
    OPENAI = "openai"
    OLLAMA = "ollama"


@dataclass(frozen=True, slots=True)
class Settings:
    provider: ProviderName
    openai_api_key: str = field(default="", repr=False)
    openai_model: str = ""
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = ""

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> "Settings":
        if environ is None:
            load_dotenv(APP_ROOT / ".env", override=False)
            environ = os.environ

        raw_provider = environ.get("LLM_PROVIDER", "").strip().lower()
        try:
            provider = ProviderName(raw_provider)
        except ValueError as exc:
            raise ConfigurationError(
                "LLM_PROVIDER must be either 'openai' or 'ollama'."
            ) from exc

        settings = cls(
            provider=provider,
            openai_api_key=environ.get("OPENAI_API_KEY", "").strip(),
            openai_model=environ.get("OPENAI_MODEL", "").strip(),
            ollama_base_url=environ.get(
                "OLLAMA_BASE_URL", "http://localhost:11434"
            ).strip().rstrip("/"),
            ollama_model=environ.get("OLLAMA_MODEL", "").strip(),
        )
        settings.validate_selected_provider()
        return settings

    def validate_selected_provider(self) -> None:
        if self.provider is ProviderName.OPENAI:
            missing = [
                name
                for name, value in (
                    ("OPENAI_API_KEY", self.openai_api_key),
                    ("OPENAI_MODEL", self.openai_model),
                )
                if not value
            ]
            if missing:
                raise ConfigurationError(
                    f"OpenAI is selected, but {', '.join(missing)} is not configured."
                )
            return

        if not self.ollama_model:
            raise ConfigurationError(
                "Ollama is selected, but OLLAMA_MODEL is not configured."
            )
        parsed = urlsplit(self.ollama_base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ConfigurationError(
                "OLLAMA_BASE_URL must be a valid http:// or https:// URL."
            )

    def configured_models(self) -> tuple[tuple[ProviderName, str], ...]:
        """Return safe, selectable models without exposing provider credentials."""
        configured: list[tuple[ProviderName, str]] = []
        for provider, model in (
            (ProviderName.OPENAI, self.openai_model),
            (ProviderName.OLLAMA, self.ollama_model),
        ):
            candidate = Settings(
                provider=provider,
                openai_api_key=self.openai_api_key,
                openai_model=self.openai_model,
                ollama_base_url=self.ollama_base_url,
                ollama_model=self.ollama_model,
            )
            try:
                candidate.validate_selected_provider()
            except ConfigurationError:
                continue
            configured.append((provider, model))
        return tuple(configured)

