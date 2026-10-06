"""Single source of truth for AI provider configuration (openai | gemini | openrouter)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field

GEMINI_BASE_URL_DEFAULT = "https://generativelanguage.googleapis.com/v1beta/openai/"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEV_PLACEHOLDER_KEY = "sk-dummy-key-for-development"


@dataclass(frozen=True)
class LLMConfig:
    provider: str
    key_env_name: str
    api_key: str
    model: str
    base_url: str | None = None
    default_headers: dict[str, str] = field(default_factory=dict)


def resolve_llm() -> LLMConfig:
    provider = os.getenv("AI_PROVIDER", "openai").lower()

    if provider == "gemini":
        return LLMConfig(
            provider="gemini",
            key_env_name="GEMINI_API_KEY",
            api_key=os.getenv("GEMINI_API_KEY", ""),
            model=os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
            base_url=os.getenv("GEMINI_BASE_URL", GEMINI_BASE_URL_DEFAULT),
        )

    if provider == "openrouter":
        headers: dict[str, str] = {"X-Title": os.getenv("OPENROUTER_TITLE", "TodoFlow")}
        referer = os.getenv("OPENROUTER_REFERER")
        if referer:
            headers["HTTP-Referer"] = referer
        return LLMConfig(
            provider="openrouter",
            key_env_name="OPENROUTER_API_KEY",
            api_key=os.getenv("OPENROUTER_API_KEY", ""),
            model=os.getenv(
                "OPENROUTER_MODEL", "nvidia/nemotron-3-ultra-550b-a55b:free"
            ),
            base_url=OPENROUTER_BASE_URL,
            default_headers=headers,
        )

    if provider == "openai":
        return LLMConfig(
            provider="openai",
            key_env_name="OPENAI_API_KEY",
            api_key=os.getenv("OPENAI_API_KEY", ""),
            model=os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"),
            base_url=None,
        )

    raise ValueError(
        f"Unknown AI_PROVIDER: {provider!r} (expected openai, gemini, or openrouter)"
    )


def make_llm(temperature: float = 0.3):
    """Build a ChatOpenAI-compatible client for the configured provider.

    Raises ValueError when the key is missing or still the dev placeholder, so
    callers can fail fast before touching the vector store.
    """
    cfg = resolve_llm()
    if not cfg.api_key or cfg.api_key == DEV_PLACEHOLDER_KEY:
        raise ValueError(
            f"{cfg.key_env_name} must be set (and not the dev placeholder) "
            f"to use AI provider '{cfg.provider}'"
        )

    from langchain_openai import ChatOpenAI

    kwargs: dict = {
        "model": cfg.model,
        "api_key": cfg.api_key,
        "temperature": temperature,
    }
    if cfg.base_url:
        kwargs["base_url"] = cfg.base_url
    if cfg.default_headers:
        kwargs["default_headers"] = cfg.default_headers
    return ChatOpenAI(**kwargs)
