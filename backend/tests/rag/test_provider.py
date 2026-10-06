import pytest

from src.llm.provider import LLMConfig, make_llm, resolve_llm

PROVIDER_VARS = [
    "AI_PROVIDER",
    "OPENAI_API_KEY",
    "OPENAI_MODEL",
    "GEMINI_API_KEY",
    "GEMINI_MODEL",
    "GEMINI_BASE_URL",
    "OPENROUTER_API_KEY",
    "OPENROUTER_MODEL",
    "OPENROUTER_REFERER",
]


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for var in PROVIDER_VARS:
        monkeypatch.delenv(var, raising=False)


def test_defaults_to_openai():
    cfg = resolve_llm()
    assert cfg == LLMConfig("openai", "OPENAI_API_KEY", "", "gpt-3.5-turbo", None, {})


def test_openai_env_overrides(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-4o-mini")
    cfg = resolve_llm()
    assert (cfg.api_key, cfg.model) == ("sk-test", "gpt-4o-mini")


def test_gemini_defaults(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "gemini")
    cfg = resolve_llm()
    assert cfg.model == "gemini-2.0-flash"
    assert cfg.base_url.endswith("/v1beta/openai/")
    assert cfg.key_env_name == "GEMINI_API_KEY"


def test_gemini_env_overrides(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-2.5-flash")
    monkeypatch.setenv("GEMINI_BASE_URL", "http://localhost:9999/")
    monkeypatch.setenv("GEMINI_API_KEY", "g-key")
    cfg = resolve_llm()
    assert (cfg.model, cfg.base_url, cfg.api_key) == (
        "gemini-2.5-flash",
        "http://localhost:9999/",
        "g-key",
    )


def test_openrouter_defaults(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "openrouter")
    cfg = resolve_llm()
    assert cfg.base_url == "https://openrouter.ai/api/v1"
    assert cfg.model == "nvidia/nemotron-3-ultra-550b-a55b:free"
    assert cfg.default_headers["X-Title"] == "TodoFlow"
    assert "HTTP-Referer" not in cfg.default_headers


def test_openrouter_referer_header(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "openrouter")
    monkeypatch.setenv("OPENROUTER_REFERER", "http://localhost:3000")
    assert resolve_llm().default_headers["HTTP-Referer"] == "http://localhost:3000"


def test_unknown_provider_raises(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "bogus")
    with pytest.raises(ValueError, match="Unknown AI_PROVIDER"):
        resolve_llm()


def test_make_llm_missing_key_raises(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "openrouter")
    with pytest.raises(ValueError, match="OPENROUTER_API_KEY"):
        make_llm()


def test_make_llm_placeholder_key_raises(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-dummy-key-for-development")
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        make_llm()


def test_make_llm_builds_client(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "openrouter")
    monkeypatch.setenv("OPENROUTER_API_KEY", "or-key")
    llm = make_llm(temperature=0.1)
    assert llm.model_name == "nvidia/nemotron-3-ultra-550b-a55b:free"
    assert llm.temperature == 0.1
