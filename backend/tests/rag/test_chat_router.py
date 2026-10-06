import asyncio

import pytest

from src.api.chat_router import process_with_openai_and_mcp

PROVIDER_VARS = [
    "AI_PROVIDER",
    "OPENAI_API_KEY",
    "GEMINI_API_KEY",
    "OPENROUTER_API_KEY",
]


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for var in PROVIDER_VARS:
        monkeypatch.delenv(var, raising=False)


def test_missing_key_returns_graceful_mock(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "openrouter")
    result = asyncio.run(process_with_openai_and_mcp("1", "hello"))
    assert "OPENROUTER API key is not configured" in result["response"]
    assert result["tool_calls"] == []


def test_unknown_provider_is_caught_as_error(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "bogus")
    result = asyncio.run(process_with_openai_and_mcp("1", "hello"))
    assert "Unknown AI_PROVIDER" in result["response"]
