import pytest
from langchain_core.documents import Document

from src.rag.chain import (
    PROMPT_TEMPLATE,
    _search_kwargs,
    create_rag_chain,
    hits_to_sources,
)
from src.rag.chatbot import RAGChatbot
from tests.rag.in_memory import EchoLLM, InMemoryStore

ALL_PROVIDER_VARS = [
    "AI_PROVIDER",
    "OPENAI_API_KEY",
    "GEMINI_API_KEY",
    "OPENROUTER_API_KEY",
]


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for var in ALL_PROVIDER_VARS:
        monkeypatch.delenv(var, raising=False)


def _docs():
    return [
        Document(
            page_content="the office budget is 42 dollars",
            metadata={"user_id": "1", "file_name": "budget.txt"},
        ),
        Document(
            page_content="quarterly plan overview",
            metadata={"user_id": "2", "file_name": "plan.txt"},
        ),
    ]


def test_search_kwargs_filters_by_user():
    kwargs = _search_kwargs("7")
    assert kwargs["k"] == 5
    condition = kwargs["filter"].must[0]
    assert condition.key == "metadata.user_id"
    assert condition.match.value == "7"


def test_missing_llm_key_fails_before_store(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "openrouter")

    def _boom(*args, **kwargs):
        raise AssertionError("store must not be touched before the llm check")

    monkeypatch.setattr("src.rag.chain.get_vectorstore", _boom)
    with pytest.raises(ValueError, match="OPENROUTER_API_KEY"):
        create_rag_chain("1")


def test_chain_answers_and_returns_sources():
    store = InMemoryStore(_docs())
    chain = create_rag_chain(
        "1", store=store, llm=EchoLLM(reply="The budget is 42 dollars.")
    )
    out = chain("what is the budget?")
    assert out["response"] == "The budget is 42 dollars."
    assert out["sources"][0]["metadata"]["file_name"] == "budget.txt"
    assert 0.0 < out["sources"][0]["metadata"]["score"] <= 1.0


def test_chain_only_sees_own_documents():
    store = InMemoryStore(_docs())
    echo = EchoLLM()
    chain = create_rag_chain("1", store=store, llm=echo)
    out = chain("quarterly plan overview")
    assert out["sources"] == []  # user 2's document is filtered out
    prompt = echo.prompts[-1][0].content
    assert "(no documents found)" in prompt


def test_prompt_grounding_template():
    assert "{context}" in PROMPT_TEMPLATE and "{question}" in PROMPT_TEMPLATE
    assert "ONLY the context" in PROMPT_TEMPLATE


def test_hits_to_sources_maps_file_name_and_score():
    doc = Document(
        page_content="x", metadata={"user_id": "1", "filename": "stored.txt"}
    )
    sources = hits_to_sources([(doc, 0.87654)])
    assert sources[0]["metadata"] == {"file_name": "stored.txt", "score": 0.8765}


def test_chatbot_facade_caches_chain_and_delegates():
    store = InMemoryStore(_docs())
    calls = []

    def factory(user_id, **kwargs):
        calls.append((user_id, kwargs))
        return create_rag_chain(user_id, store=store, llm=EchoLLM(reply="hi"))

    bot = RAGChatbot(store=store, chain_factory=factory)
    first = bot.generate_response("budget", "1")
    second = bot.generate_response("budget", "1")
    assert first["response"] == second["response"] == "hi"
    assert len(calls) == 1  # cached per user


def test_chatbot_search_similar_shape():
    bot = RAGChatbot(store=InMemoryStore(_docs()))
    results = bot.search_similar("budget", "1")
    assert results[0]["metadata"]["file_name"] == "budget.txt"
    assert isinstance(results[0]["content"], str)
