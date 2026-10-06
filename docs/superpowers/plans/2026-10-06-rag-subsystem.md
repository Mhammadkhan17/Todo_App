# RAG Subsystem Implementation Plan

**Date:** 2026-10-06
**Spec (source of truth):** `docs/superpowers/specs/2026-10-06-rag-subsystem-design.md`
**Status:** Ready for review

## TL;DR

11 tasks, ordered so every task ends green and committed:

1. Unblock the pre-existing broken test suite (2 test-only fixes) + baseline commits
2. `src/llm/provider.py` — single AI provider resolver (openai / gemini / openrouter) + tests
3. `chat_router.py` → use the resolver (behavior-identical) + tests
4. Config: requirements, `.env.example`, `.gitignore`, `docker-compose.yml`
5. Model fetch script (ONNX MiniLM-L6-v2) + `src/rag/embeddings.py` + tests
6. `src/rag/store.py` — Qdrant client/embedder/vectorstore singletons + tests
7. `src/rag/ingest.py` — extract → chunk → embed → upsert (+ test harness fakes) + tests
8. `src/rag/chain.py` + `chatbot.py` facade — grounded answer with sources + tests
9. `src/api/v1/rag.py` — real multipart upload, per-user search/reset, session seam wiring + tests
10. Frontend `DocumentUploader` — Bearer auth, drop `.doc` + lint
11. Docs (README/CHANGELOG) + manual E2E checklist with the now-running Docker stack

## Global constraints

**Commands** (never `pip install` into the system Python; never `scripts/lint.sh` — it requires docker CLI inside the script):

```bash
# backend tests
cd backend && .venv/bin/python -m pytest tests -q
# backend lint/format
cd backend && .venv/bin/python -m ruff check src tests && .venv/bin/python -m black --check src tests
# frontend
cd frontend && npm run lint
# model weights (run yourself when ready — see install policy below)
backend/.venv/bin/python scripts/fetch_embeddings_model.py
```

**Install/download policy (user-run, plan never executes these):**

- The plan only *declares* dependencies in `backend/requirements.txt` and *creates* `scripts/fetch_embeddings_model.py`. You run the installs/fetches yourself:
  ```bash
  backend/.venv/bin/pip install -r backend/requirements.txt   # onnxruntime, tokenizers, langchain-qdrant, numpy
  backend/.venv/bin/python scripts/fetch_embeddings_model.py  # ~90 MB ONNX weights from Hugging Face
  ```
- Embedding tests **skip** until both are done; everything else (including all route tests) runs offline without them.
- AI key: you will add `AI_PROVIDER=openrouter` and `OPENROUTER_API_KEY=<your free key>` to `.env` yourself; the plan only adds the `.env.example` template and compose pass-through. Without the key, live chat returns the graceful "API key not configured" mock (tests don't need it).
- Docker image builds (`docker compose up --build`) install requirements inside the container — run compose commands only with your go-ahead.

**Rules:**

- `str(current_user.id)` for **every** `user_id` written to a DB row, Qdrant payload, or filter (`User.id` is `int`; `Document/ChatSession/ChatMessage.user_id` are `str`).
- `onnxruntime` / `tokenizers` imported only inside functions (lazy) so the rest of the app/tests run without them.
- Spec §10 is the accepted-risk register; this plan adds no new decisions.
- Commit per task (`git add <paths> && git commit -m "..."`). Repo currently has **zero commits**; `git add -A` for the baseline is safe (`.env`, `.venv`, `node_modules`, `.agents/`, `CHANGELOG.md` are gitignored). CHANGELOG edits are local-only by design.

**Verified facts the code blocks rely on** (all confirmed against the installed venv / live services):

- `langchain-qdrant 1.1.0`: `QdrantVectorStore(client, collection_name, embedding)`; `similarity_search_with_score(query, k, filter) -> list[tuple[Document, float]]`; filter must be `qdrant_client.models.Filter` with key `metadata.user_id`; payload shape `{page_content, metadata:{...}}`; `add_documents(docs, ids=...)` forwards `ids` to `add_texts` (confirmed in `langchain_core 1.6.6` source); `delete()` accepts ids only → purge-by-filter via `client.delete(collection, points_selector=models.FilterSelector(filter=...))`; point IDs must be UUID → `uuid.uuid5(uuid.UUID(document_id), str(chunk_index))`.
- `QdrantClient(":memory:")` works offline; `create_payload_index` on memory is a no-op warning; `count()` works.
- HF repo `qdrant/all-MiniLM-L6-v2-onnx` files: `tokenizer.json`, `config.json`, `vocab.txt`, `model.onnx` (single file, no `.onnx_data`), `special_tokens_map.json`, `tokenizer_config.json`.
- `ChatOpenAI(model=, api_key=, base_url=, temperature=, default_headers=)` constructs offline.
- `main.py:139` adds `TrustedHostMiddleware` when `ENVIRONMENT == "development"` (root `.env` sets it) → TestClient's `testserver` host gets `400 "Invalid host header"`.
- `backend/src/database/session.py` `get_session` wraps `database_engine.get_session()` → prod-identical; tests override only `get_session`.
- `AuthService.authenticate_user` uses `database_engine.get_session()` directly → **bypasses** the test override (root cause of pre-existing login failures). Worked around in test fixtures by minting JWTs with `JWTService.create_access_token` (the `/login` path needs the real Neon DB).
- Docker Desktop is now running; compose services are startable for E2E.

**Pre-existing issues — NOT fixed by this plan** (documented, not regressed):

- `tests/test_auth.py` login tests, `tests/test_tasks.py` (5), `tests/test_security.py` (3) fail after the Task-1 fixes because login/`/api/token` bypass the overridden session. Out of scope (auth flows are spec §9).
- Baseline numbers: before Task 1 → `15 failed, 9 passed`; after Task 1 → `10 failed, 14 passed`. Final verification = same 10 pre-existing failures, zero new ones, all `tests/rag/` green (45 tests).

## File structure

```
backend/
  src/llm/provider.py                    NEW  LLMConfig, resolve_llm(), make_llm()
  src/rag/embeddings.py                  NEW  OnnxMiniLMEmbeddings (ONNX MiniLM-L6-v2)
  src/rag/store.py                       NEW  client/embedder/vectorstore singletons, ensure_collection
  src/rag/ingest.py                      NEW  DocumentIngestor (replaces placeholder)
  src/rag/chain.py                       NEW  create_rag_chain, filters, sources, prompt
  src/rag/chatbot.py                     EDIT RAGChatbot facade (store/chain seams)
  src/api/chat_router.py                 EDIT provider block → resolve_llm()
  src/api/v1/rag.py                      EDIT seams, multipart upload, per-user search/reset, Depends(get_session)
  models/all-MiniLM-L6-v2/               NEW  tokenizer.json, config.json, vocab.txt (committed)
  models/all-MiniLM-L6-v2/onnx/          NEW  model.onnx (gitignored)
  data/uploads/                          NEW  per-user storage (gitignored)
  tests/conftest.py                      EDIT StaticPool + testserver host allow
  tests/rag/__init__.py                  NEW
  tests/rag/conftest.py                  NEW  RAG tables, store reset, auth fixtures, qdrant/db fixtures
  tests/rag/in_memory.py                 NEW  FakeEmbedder, InMemoryStore, EchoLLM
  tests/rag/test_{provider,chat_router,embeddings,store,ingest,chain,rag_routes}.py  NEW
  requirements.txt                       EDIT add langchain-qdrant, numpy, onnxruntime, tokenizers
scripts/fetch_embeddings_model.py        NEW  download weights from HF
frontend/src/components/rag/DocumentUploader.tsx  EDIT Bearer auth, drop .doc
docker-compose.yml                       EDIT qdrant pin + backend RAG env
.env.example                             EDIT AI + RAG sections
.gitignore                               EDIT uploads/ + onnx/
README.md, CHANGELOG.md                  EDIT status/limitations (CHANGELOG is gitignored/local)
```

---

## Task 1 — Test-infra unblock + baseline commits

**Why first:** every later task verifies with pytest; the suite is currently 15F/9P for reasons unrelated to RAG.

**Files:** `backend/tests/conftest.py`, new `backend/tests/rag/{__init__.py,conftest.py}`

### Step 1 — baseline commit (pre-fix state)

```bash
git add -A && git commit -m "chore: baseline snapshot before RAG subsystem work"
```

### Step 2 — fix `tests/conftest.py` (test-only, two root causes)

Add import and replace the engine line:

```python
from sqlalchemy.pool import StaticPool
```

```python
@pytest.fixture(scope="session")
def test_db():
    """Create a test database."""
    # SingletonThreadPool gives each thread its own empty :memory: DB;
    # StaticPool shares one connection so the app thread sees the same tables.
    test_engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
```

After `from main import app`, add the host allow-patch (dev TrustedHostMiddleware rejects `testserver`):

```python
def _allow_testclient_host() -> None:
    from fastapi.middleware.trustedhost import TrustedHostMiddleware

    for middleware in app.user_middleware:
        if getattr(middleware, "cls", None) is TrustedHostMiddleware:
            options = getattr(middleware, "kwargs", None) or getattr(middleware, "options", None)
            if options is not None:
                options["allowed_hosts"] = ["testserver", "localhost", "127.0.0.1", "0.0.0.0"]


_allow_testclient_host()
```

### Step 3 — new `backend/tests/rag/__init__.py` (empty) and `backend/tests/rag/conftest.py`

```python
"""Shared fixtures for RAG tests: DB tables, in-memory Qdrant, auth helpers."""
import pytest
from qdrant_client import QdrantClient
from sqlmodel import Session, SQLModel

from src.auth.jwt_service import JWTService

import src.models.rag  # noqa: F401  register Document/ChatSession/ChatMessage on SQLModel.metadata

# (execution note: `from src.rag.store import reset_singletons` + the autouse
#  _reset_store_singletons fixture are added in Task 6, when store.py exists)


@pytest.fixture(scope="session", autouse=True)
def _rag_tables(test_db):
    SQLModel.metadata.create_all(bind=test_db)


# added in Task 6 (needs src/rag/store.py to exist):
@pytest.fixture(autouse=True)
def _reset_store_singletons():
    reset_singletons()
    yield
    reset_singletons()


@pytest.fixture
def qdrant_client():
    return QdrantClient(":memory:")


@pytest.fixture
def db_session(test_db):
    # sqlmodel.Session (adds .exec); plain sqlalchemy sessionmaker lacks it
    session = Session(bind=test_db)
    yield session
    session.close()


def _register(client, *, username, email, password="testpassword123", full_name="Test User"):
    response = client.post(
        "/api/register",
        json={
            "email": email,
            "username": username,
            "password": password,
            "full_name": full_name,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _bearer(user: dict) -> dict:
    # /api/token goes through AuthService.authenticate_user, which uses the real
    # engine (test-override bypass) — mint the token directly instead.
    token = JWTService.create_access_token(
        {"sub": user["username"], "user_id": user["id"], "email": user["email"]}
    )["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def make_user(client):
    def _make(username: str, email: str) -> dict:
        return _bearer(_register(client, username=username, email=email))

    return _make


@pytest.fixture
def auth_headers(make_user):
    return make_user("testuser", "test@example.com")


@pytest.fixture
def other_user_headers(make_user):
    return make_user("otheruser", "other@example.com")
```

### Step 4 — commit

```bash
git add backend/tests && git commit -m "test: share in-memory SQLite across threads and allow testserver host"
```

### Verification

```bash
cd backend && .venv/bin/python -m pytest tests -q
```

Expected: `10 failed, 14 passed` — the 10 failures are the documented pre-existing auth/tasks/security set (login bypass + unrelated assertions). Any other failure means stop and diagnose.

---

## Task 2 — `src/llm/provider.py`

**Files:** `backend/src/llm/__init__.py` (empty), `backend/src/llm/provider.py`, `backend/tests/rag/test_provider.py`

### Step 1 — `backend/src/llm/provider.py`

```python
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
            model=os.getenv("OPENROUTER_MODEL", "nvidia/nemotron-3-ultra-550b-a55b:free"),
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

    raise ValueError(f"Unknown AI_PROVIDER: {provider!r} (expected openai, gemini, or openrouter)")


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

    kwargs: dict = {"model": cfg.model, "api_key": cfg.api_key, "temperature": temperature}
    if cfg.base_url:
        kwargs["base_url"] = cfg.base_url
    if cfg.default_headers:
        kwargs["default_headers"] = cfg.default_headers
    return ChatOpenAI(**kwargs)
```

### Step 2 — `backend/tests/rag/test_provider.py`

```python
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
    assert (cfg.model, cfg.base_url, cfg.api_key) == ("gemini-2.5-flash", "http://localhost:9999/", "g-key")


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
```

### Verification + commit

```bash
cd backend && .venv/bin/python -m pytest tests/rag/test_provider.py -q   # 10 passed
cd backend && .venv/bin/python -m ruff check src/llm tests/rag && .venv/bin/python -m black src/llm tests/rag
git add backend/src/llm backend/tests/rag && git commit -m "feat: AI provider resolver (openai/gemini/openrouter) with fail-fast llm factory"
```

---

## Task 3 — `chat_router.py` uses the resolver

**Why:** duplicated provider logic (spec §5); behavior must stay identical so task-chat tests don't regress.

**Files:** `backend/src/api/chat_router.py`, `backend/tests/rag/test_chat_router.py`

### Step 1 — add import (after `from dotenv import load_dotenv`)

```python
from ..llm.provider import resolve_llm
```

### Step 2 — replace lines 96–117 (the provider if/else + mock guard + client construction)

Old block starts `ai_provider = os.getenv("AI_PROVIDER", "openai").lower()` and ends `client = openai.OpenAI(api_key=api_key, base_url=base_url)`. New:

```python
        cfg = resolve_llm()
        ai_provider, api_key, model = cfg.provider, cfg.api_key, cfg.model

        if not api_key or api_key == "sk-dummy-key-for-development":
            # Return a mock response if using dummy API key
            return {
                "response": f"Chatbot is working! However, {ai_provider.upper()} API key is not configured. Please set a valid API key in environment variables.",
                "tool_calls": [],
                "results": []
            }

        # Initialize OpenAI-compatible client
        client = openai.OpenAI(api_key=api_key, base_url=cfg.base_url, default_headers=cfg.default_headers or None)
```

Local variables `ai_provider`, `api_key`, `model` keep the rest of the function (lines 230, 267: `model=model`) untouched. Unknown `AI_PROVIDER` now raises inside `resolve_llm()` → caught by the function's existing `except Exception` → error response (asserted below).

### Step 3 — `backend/tests/rag/test_chat_router.py`

```python
import asyncio

import pytest

from src.api.chat_router import process_with_openai_and_mcp

PROVIDER_VARS = ["AI_PROVIDER", "OPENAI_API_KEY", "GEMINI_API_KEY", "OPENROUTER_API_KEY"]


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for var in PROVIDER_VARS:
        monkeypatch.delenv(var, raising=False)


def test_missing_key_returns_graceful_mock(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "openrouter")
    result = asyncio.run(process_with_openai_and_mcp("1", "hello"))
    assert "OPENROUTER_API_KEY" in result["response"]
    assert result["tool_calls"] == []


def test_unknown_provider_is_caught_as_error(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "bogus")
    result = asyncio.run(process_with_openai_and_mcp("1", "hello"))
    assert "Unknown AI_PROVIDER" in result["response"]
```

### Verification + commit

```bash
cd backend && .venv/bin/python -m pytest tests/rag/test_chat_router.py -q   # 2 passed
git add backend/src/api/chat_router.py backend/tests/rag && git commit -m "refactor: chat_router reads provider config from src/llm/provider"
```

---

## Task 4 — Config: requirements, env, gitignore, compose

**Files:** `backend/requirements.txt`, `.env.example`, `.gitignore`, `docker-compose.yml`

### Step 1 — `backend/requirements.txt`

In the `# RAG Dependencies` section add (keep `unstructured` etc. as-is):

```
langchain-qdrant>=1.1.0,<2.0
numpy>=1.26.0
onnxruntime>=1.19.0
tokenizers>=0.20.0
```

(`langchain-text-splitters` ships transitively with `langchain` — do not add.)

**User step (not run by the plan):** `backend/.venv/bin/pip install -r backend/requirements.txt` — installs `onnxruntime 1.30.0` + `tokenizers 0.23.2` (wheels for Python 3.14 verified via dry-run), ~34 MB.

### Step 2 — `.env.example`, after line 60 (`OPENAI_MODEL=gpt-4o-mini`)

```
OPENROUTER_API_KEY=
OPENROUTER_MODEL=nvidia/nemotron-3-ultra-550b-a55b:free
OPENROUTER_REFERER=http://localhost:3000

# RAG / Qdrant (in Docker use QDRANT_URL=http://qdrant:6333)
QDRANT_URL=http://localhost:6333
RAG_COLLECTION=todo_documents
ALLOWED_DOCUMENT_PATH=/app/documents/
```

### Step 3 — `.gitignore`, append

```
# RAG local artifacts
backend/data/uploads/
backend/models/**/onnx/
```

### Step 4 — `docker-compose.yml`

Replace the `qdrant` service (pin the verified-stable tag; drop the inert healthcheck — distroless image has no `wget` — and the inert `QDRANT_API_KEY` server env; the *client* still honors `QDRANT_URL`/`QDRANT_API_KEY` from its own env for Qdrant Cloud):

```yaml
  # Qdrant Vector Database for RAG
  qdrant:
    image: qdrant/qdrant:v1.19.2
    container_name: todo_app_qdrant
    restart: unless-stopped
    volumes:
      - qdrant_data:/qdrant/storage
    ports:
      - "6333:6333"
      - "6334:6334"
    networks:
      - todo_network
```

In the `backend` service `environment:` block, after `OPENAI_API_KEY` add:

```yaml
      - OPENROUTER_API_KEY=${OPENROUTER_API_KEY:-}
      - OPENROUTER_MODEL=${OPENROUTER_MODEL:-nvidia/nemotron-3-ultra-550b-a55b:free}
      - OPENROUTER_REFERER=${OPENROUTER_REFERER:-http://localhost:3000}
      - QDRANT_URL=${QDRANT_URL:-http://qdrant:6333}
      - RAG_COLLECTION=${RAG_COLLECTION:-todo_documents}
      - ALLOWED_DOCUMENT_PATH=${ALLOWED_DOCUMENT_PATH:-/app/documents/}
```

### Verification + commit

```bash
backend/.venv/bin/python -c "import yaml; yaml.safe_load(open('docker-compose.yml')); print('compose yaml ok')"
grep -n "qdrant/qdrant:v1.19.2" docker-compose.yml
grep -n "OPENROUTER_API_KEY" .env.example backend/requirements.txt | head -2  # env only; requirements has onnxruntime instead
grep -n "onnxruntime" backend/requirements.txt
git add backend/requirements.txt .env.example .gitignore docker-compose.yml && git commit -m "chore: RAG dependencies, env template, compose qdrant pin"
```

---

## Task 5 — Model fetch script + `embeddings.py`

**Files:** `scripts/fetch_embeddings_model.py` (new), `backend/models/all-MiniLM-L6-v2/{tokenizer.json,config.json,vocab.txt}` (downloaded), `backend/src/rag/embeddings.py`, `backend/tests/rag/test_embeddings.py`

### Step 1 — `scripts/fetch_embeddings_model.py`

```python
#!/usr/bin/env python3
"""Download the ONNX MiniLM-L6-v2 embedding model from Hugging Face.

Weights (model.onnx, ~90MB) are gitignored; tokenizer/config are committed.
Run from anywhere:  backend/.venv/bin/python scripts/fetch_embeddings_model.py [--force]
"""
import argparse
import sys
import urllib.error
import urllib.request
from pathlib import Path

HF_BASE = "https://huggingface.co/qdrant/all-MiniLM-L6-v2-onnx/resolve/main"
MODEL_DIR = Path(__file__).resolve().parents[1] / "backend" / "models" / "all-MiniLM-L6-v2"
REQUIRED = ["tokenizer.json", "config.json", "vocab.txt", "model.onnx"]
OPTIONAL = ["model.onnx_data"]


def download(name: str, dest: Path, *, force: bool) -> bool:
    if dest.exists() and not force:
        print(f"  = {name} already present")
        return True
    url = f"{HF_BASE}/{name}"
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        print(f"  -> {url}")
        urllib.request.urlretrieve(url, dest)
        print(f"  ok {name} ({dest.stat().st_size // 1024} KB)")
        return True
    except urllib.error.HTTPError as exc:
        if exc.code == 404 and name in OPTIONAL:
            print(f"  - {name} not in repo, skipping")
            return True
        print(f"  ! failed: {name}: {exc}", file=sys.stderr)
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="re-download even if present")
    args = parser.parse_args()

    print(f"Model dir: {MODEL_DIR}")
    ok = all(download(name, MODEL_DIR / ("onnx" if name.startswith("model.") else name),
                      force=args.force)
              for name in REQUIRED)
    for name in OPTIONAL:
        download(name, MODEL_DIR / "onnx" / name, force=args.force)
    if not ok:
        print("Download failed.", file=sys.stderr)
        return 1
    print("Done. Weights ready.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

**User step (not run by the plan):** fetch the weights when ready —

```bash
backend/.venv/bin/python scripts/fetch_embeddings_model.py
ls -la backend/models/all-MiniLM-L6-v2/ backend/models/all-MiniLM-L6-v2/onnx/
```

Expected after fetch: `tokenizer.json`, `config.json`, `vocab.txt` at root; `onnx/model.onnx` ~90 MB. Until then the two model-dependent tests below skip.

### Step 2 — `backend/src/rag/embeddings.py`

```python
"""Local ONNX MiniLM-L6-v2 embeddings (Approach A: port of rag-example)."""
from __future__ import annotations

import json
from pathlib import Path

from langchain_core.embeddings import Embeddings

MODEL_DIR = Path(__file__).resolve().parents[2] / "models" / "all-MiniLM-L6-v2"
EMBEDDING_DIM = 384
MAX_TOKENS = 256


def mean_pool(token_embeddings, attention_mask):
    """Attention-masked mean of token embeddings. numpy arrays: (B, L, D), (B, L)."""
    import numpy as np

    mask = attention_mask.astype(np.float32)[:, :, None]
    summed = (token_embeddings.astype(np.float32) * mask).sum(axis=1)
    counts = mask.sum(axis=1).clip(min=1e-9)
    return summed / counts


def l2_normalize(embeddings):
    import numpy as np

    norms = np.linalg.norm(embeddings, axis=1, keepdims=True).clip(min=1e-9)
    return embeddings / norms


class OnnxMiniLMEmbeddings(Embeddings):
    def __init__(self, model_dir: Path = MODEL_DIR, max_tokens: int = MAX_TOKENS):
        try:
            import onnxruntime
            from tokenizers import Tokenizer
        except ImportError as exc:
            raise ImportError(
                "RAG embedding deps missing — install backend/requirements.txt "
                "(onnxruntime, tokenizers)"
            ) from exc

        onnx_path = model_dir / "onnx" / "model.onnx"
        if not onnx_path.exists():
            raise FileNotFoundError(
                f"{onnx_path} not found — run scripts/fetch_embeddings_model.py first"
            )

        config = json.loads((model_dir / "config.json").read_text())
        pad_id = config.get("pad_token_id", 0)

        self._tokenizer = Tokenizer.from_file(str(model_dir / "tokenizer.json"))
        self._tokenizer.enable_truncation(max_length=max_tokens)
        self._tokenizer.enable_padding(pad_id=pad_id)
        self._session = onnxruntime.InferenceSession(
            str(onnx_path), providers=["CPUExecutionProvider"]
        )
        self._input_names = {i.name for i in self._session.get_inputs()}

    def _encode(self, texts: list[str]):
        import numpy as np

        encodings = self._tokenizer.encode_batch(texts)
        input_ids = np.array([e.ids for e in encodings], dtype=np.int64)
        attention_mask = np.array([e.attention_mask for e in encodings], dtype=np.int64)
        feed: dict = {"input_ids": input_ids, "attention_mask": attention_mask}
        if "token_type_ids" in self._input_names:
            feed["token_type_ids"] = np.zeros_like(input_ids)
        token_embeddings = self._session.run(None, feed)[0]
        return l2_normalize(mean_pool(token_embeddings, attention_mask))

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        return self._encode(texts).tolist()

    def embed_query(self, text: str) -> list[float]:
        return self._encode([text])[0].tolist()
```

### Step 3 — `backend/tests/rag/test_embeddings.py`

```python
import pytest

from src.rag.embeddings import EMBEDDING_DIM, MODEL_DIR, OnnxMiniLMEmbeddings, l2_normalize, mean_pool


def _model_ready() -> bool:
    """Weights fetched AND embedding deps installed (both are user-run steps)."""
    if not (MODEL_DIR / "onnx" / "model.onnx").exists():
        return False
    try:
        import onnxruntime  # noqa: F401
        from tokenizers import Tokenizer  # noqa: F401
    except ImportError:
        return False
    return True


MODEL_READY = _model_ready()


def test_mean_pool_masks_padding():
    import numpy as np

    token = np.array([[[1.0, 0.0], [3.0, 2.0], [100.0, 100.0]]])
    mask = np.array([[1, 1, 0]])
    pooled = mean_pool(token, mask)
    assert pooled.shape == (1, 2)
    np.testing.assert_allclose(pooled, [[2.0, 1.0]])


def test_l2_normalize_unit_length():
    import numpy as np

    out = l2_normalize(np.array([[3.0, 4.0]]))
    np.testing.assert_allclose(np.linalg.norm(out, axis=1), [1.0], rtol=1e-6)


@pytest.mark.skipif(not (MODEL_DIR / "tokenizer.json").exists(), reason="model files not fetched yet")
def test_model_dir_layout():
    assert (MODEL_DIR / "tokenizer.json").exists()
    assert (MODEL_DIR / "config.json").exists()


@pytest.mark.skipif(not MODEL_READY, reason="run pip install -r requirements + fetch_embeddings_model.py first")
def test_real_embedding_shape_and_determinism():
    emb = OnnxMiniLMEmbeddings()
    v1 = emb.embed_query("buy groceries tomorrow")
    v2 = emb.embed_query("buy groceries tomorrow")
    assert len(v1) == EMBEDDING_DIM
    assert v1 == v2
    assert abs(sum(x * x for x in v1) - 1.0) < 1e-4
```

### Verification + commit

```bash
cd backend && .venv/bin/python -m pytest tests/rag/test_embeddings.py -q
#   before your install/fetch: 2 passed, 2 skipped — after both: 4 passed
git add scripts/fetch_embeddings_model.py backend/src/rag/embeddings.py backend/tests/rag
git commit -m "feat: ONNX MiniLM-L6-v2 embeddings with HF fetch script"
# after you run the fetch script, commit the small model files (onnx/ is gitignored):
git add backend/models && git commit -m "chore: add embedding tokenizer/config files"
```

---

## Task 6 — `store.py`

**Files:** `backend/src/rag/store.py`, `backend/tests/rag/test_store.py`

### Step 1 — `backend/src/rag/store.py`

```python
"""Qdrant client, embedder, and vectorstore singletons."""
from __future__ import annotations

import os
from functools import lru_cache

from qdrant_client import QdrantClient

DEFAULT_QDRANT_URL = "http://localhost:6333"
DEFAULT_COLLECTION = "todo_documents"
EMBEDDING_DIM = 384
PAYLOAD_INDEX_FIELDS = ("metadata.user_id", "metadata.document_id")


def qdrant_url() -> str:
    return os.getenv("QDRANT_URL", DEFAULT_QDRANT_URL)


def collection_name() -> str:
    return os.getenv("RAG_COLLECTION", DEFAULT_COLLECTION)


@lru_cache(maxsize=1)
def get_client() -> QdrantClient:
    api_key = os.getenv("QDRANT_API_KEY") or None
    if api_key:
        return QdrantClient(url=qdrant_url(), api_key=api_key, timeout=30)
    return QdrantClient(url=qdrant_url(), timeout=30)


@lru_cache(maxsize=1)
def get_embedder():
    from .embeddings import OnnxMiniLMEmbeddings

    return OnnxMiniLMEmbeddings()


def ensure_collection(client: QdrantClient | None = None) -> None:
    from qdrant_client import models

    client = client or get_client()
    name = collection_name()
    if client.collection_exists(name):
        return
    client.create_collection(
        name,
        vectors_config=models.VectorParams(size=EMBEDDING_DIM, distance=models.Distance.COSINE),
    )
    for field in PAYLOAD_INDEX_FIELDS:
        client.create_payload_index(
            name, field_name=field, field_schema=models.PayloadSchemaType.KEYWORD
        )


@lru_cache(maxsize=1)
def get_vectorstore():
    from langchain_qdrant import QdrantVectorStore

    ensure_collection()
    return QdrantVectorStore(
        client=get_client(),
        collection_name=collection_name(),
        embedding=get_embedder(),
    )


def reset_singletons() -> None:
    get_client.cache_clear()
    get_embedder.cache_clear()
    get_vectorstore.cache_clear()
```

### Step 2 — `backend/tests/rag/test_store.py`

```python
from langchain_core.documents import Document
from langchain_qdrant import QdrantVectorStore
from qdrant_client import models

from src.rag import store
from tests.rag.in_memory import FakeEmbedder


def test_defaults():
    assert store.qdrant_url() == "http://localhost:6333"
    assert store.collection_name() == "todo_documents"


def test_env_overrides(monkeypatch):
    monkeypatch.setenv("QDRANT_URL", "http://qdrant:6333")
    monkeypatch.setenv("RAG_COLLECTION", "custom_col")
    assert store.qdrant_url() == "http://qdrant:6333"
    assert store.collection_name() == "custom_col"


def test_ensure_collection_creates_and_is_idempotent(qdrant_client):
    store.ensure_collection(client=qdrant_client)
    store.ensure_collection(client=qdrant_client)  # no error on second call
    info = qdrant_client.get_collection(store.collection_name())
    assert info.config.params.vectors.size == store.EMBEDDING_DIM


def test_vectorstore_roundtrip(qdrant_client):
    store.ensure_collection(client=qdrant_client)
    vs = QdrantVectorStore(
        client=qdrant_client,
        collection_name=store.collection_name(),
        embedding=FakeEmbedder(),
    )
    vs.add_documents(
        [Document(page_content="alpha text", metadata={"user_id": "1", "file_name": "a.txt"})],
        ids=["11111111-1111-1111-1111-111111111111"],
    )
    hits = vs.similarity_search_with_score(
        "alpha text",
        k=5,
        filter=models.Filter(
            must=[models.FieldCondition(key="metadata.user_id", match=models.MatchValue(value="1"))]
        ),
    )
    assert len(hits) == 1
    assert hits[0][0].page_content == "alpha text"
    assert hits[0][1] > 0.0
```

This task also creates `tests/rag/in_memory.py` (extended in Task 7):

```python
"""Deterministic fakes for RAG tests: no ONNX, no Qdrant server, no LLM."""
import zlib

from langchain_core.embeddings import Embeddings

DIM = 384


class FakeEmbedder(Embeddings):
    """Bag-of-words 384-d embedder: overlapping words -> non-zero cosine."""

    def _embed_one(self, text: str) -> list[float]:
        vec = [0.0] * DIM
        for token in text.lower().split():
            vec[zlib.crc32(token.encode()) % DIM] += 1.0
        norm = sum(v * v for v in vec) ** 0.5
        return [v / norm for v in vec] if norm else vec

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed_one(text)
```

### Verification + commit

```bash
cd backend && .venv/bin/python -m pytest tests/rag/test_store.py -q   # 4 passed
git add backend/src/rag/store.py backend/tests/rag && git commit -m "feat: Qdrant store singletons with collection bootstrap"
```

---

## Task 7 — `ingest.py` (+ test harness completion)

**Files:** `backend/src/rag/ingest.py` (replace placeholder), `backend/tests/rag/in_memory.py` (extend), `backend/tests/rag/test_ingest.py`

### Step 1 — `backend/src/rag/ingest.py`

```python
"""Document ingestion: extract -> split -> embed -> upsert, owning Document-row lifecycle."""
from __future__ import annotations

import hashlib
import mimetypes
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Sequence

from langchain_core.documents import Document as LangchainDocument
from sqlmodel import Session, select

from ..models.rag import Document
from .store import collection_name, ensure_collection

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md", ".markdown", ".docx"}
TEXT_EXTENSIONS = {".txt", ".md", ".markdown"}
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
UPLOAD_BATCH = 64
UPLOADS_DIR = Path(__file__).resolve().parents[2] / "data" / "uploads"


@dataclass
class IngestResult:
    indexed: int = 0
    skipped: int = 0
    failed: int = 0
    errors: list[str] = field(default_factory=list)


def extract_text(filename: str, content: bytes, file_path: Path) -> str:
    ext = Path(filename).suffix.lower()
    if ext == ".pdf":
        from pypdf import PdfReader

        reader = PdfReader(BytesIO(content))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    if ext == ".docx":
        import docx2txt

        return docx2txt.process(str(file_path)) or ""
    if content.startswith((b"\xff\xfe", b"\xfe\xff")):
        return content.decode("utf-16")
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError:
        return content.decode("latin-1")


def _split(text: str) -> list[str]:
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
    return [chunk for chunk in splitter.split_text(text) if chunk.strip()]


class DocumentIngestor:
    def __init__(self, *, client=None, embedder=None, uploads_dir: Path = UPLOADS_DIR):
        self._client = client
        self._embedder = embedder
        self._uploads_dir = Path(uploads_dir)

    # -- seams ---------------------------------------------------------
    def _qdrant(self):
        if self._client is None:
            from .store import get_client

            self._client = get_client()
        return self._client

    def _embedding(self):
        if self._embedder is None:
            from .store import get_embedder

            self._embedder = get_embedder()
        return self._embedder

    def _vectorstore(self):
        from langchain_qdrant import QdrantVectorStore

        ensure_collection(client=self._qdrant())
        return QdrantVectorStore(
            client=self._qdrant(),
            collection_name=collection_name(),
            embedding=self._embedding(),
        )

    # -- public API ----------------------------------------------------
    def ingest_upload(
        self, db: Session, user_id: str, files: Sequence[tuple[str, bytes]]
    ) -> IngestResult:
        user_id = str(user_id)
        result = IngestResult()
        self._uploads_dir.mkdir(parents=True, exist_ok=True)
        user_dir = self._uploads_dir / user_id
        user_dir.mkdir(parents=True, exist_ok=True)

        for filename, content in files:
            ext = Path(filename).suffix.lower()
            if ext not in ALLOWED_EXTENSIONS:
                result.failed += 1
                result.errors.append(f"{filename}: unsupported extension")
                continue

            document_id = str(uuid.uuid4())
            file_path = user_dir / f"{document_id}{ext}"
            file_path.write_bytes(content)
            try:
                self._index_one(
                    db, user_id=user_id, document_id=document_id,
                    filename=filename, original_filename=filename,
                    file_path=file_path, content=content, result=result,
                )
            except Exception as exc:  # noqa: BLE001 - one bad file must not sink the batch
                result.failed += 1
                result.errors.append(f"{filename}: {exc}")
                failed_row = db.exec(
                    select(Document)
                    .where(Document.user_id == user_id)
                    .where(Document.original_filename == filename)
                ).first()
                if failed_row is not None:
                    failed_row.status = "failed"
                    db.add(failed_row)
                    db.commit()
        return result

    def ingest_paths(self, db: Session, user_id: str, paths: Sequence[str]) -> IngestResult:
        user_id = str(user_id)
        result = IngestResult()
        for raw in paths:
            path = Path(raw)
            try:
                content = path.read_bytes()
            except OSError as exc:
                result.failed += 1
                result.errors.append(f"{raw}: {exc}")
                continue
            document_id = str(uuid.uuid4())
            try:
                self._index_one(
                    db, user_id=user_id, document_id=document_id,
                    filename=path.name, original_filename=path.name,
                    file_path=path, content=content, result=result,
                )
            except Exception as exc:  # noqa: BLE001
                result.failed += 1
                result.errors.append(f"{raw}: {exc}")
        return result

    def reset_user(self, db: Session, user_id: str) -> int:
        from qdrant_client import models

        user_id = str(user_id)
        client = self._qdrant()
        name = collection_name()
        deleted = 0
        if client.collection_exists(name):
            points, _ = client.scroll(
                collection_name=name,
                scroll_filter=models.Filter(
                    must=[models.FieldCondition(
                        key="metadata.user_id", match=models.MatchValue(value=user_id))]
                ),
                limit=10000,
                with_payload=False,
                with_vectors=False,
            )
            if points:
                client.delete(
                    collection_name=name,
                    points_selector=models.FilterSelector(
                        filter=models.Filter(
                            must=[models.FieldCondition(
                                key="metadata.user_id",
                                match=models.MatchValue(value=user_id))]
                        )
                    ),
                )
                deleted = len(points)

        rows = db.exec(
            select(Document).where(Document.user_id == user_id)
        ).all()
        for row in rows:
            db.delete(row)
        db.commit()
        return deleted

    # -- internals -----------------------------------------------------
    def _index_one(
        self, db, *, user_id, document_id, filename, original_filename,
        file_path, content, result,
    ) -> None:
        new_hash = hashlib.sha256(content).hexdigest()
        existing = db.exec(
            select(Document)
            .where(Document.user_id == user_id)
            .where(Document.original_filename == original_filename)
        ).first()
        if existing is not None:
            # Compare against the STORED hash before mutating the row
            if existing.status == "indexed" and existing.hash == new_hash:
                result.skipped += 1
                return
            row = existing
            document_id = existing.id
        else:
            row = Document(id=document_id, user_id=user_id, original_filename=original_filename)

        row.filename = Path(file_path).name
        row.file_path = str(file_path)
        row.file_size = len(content)
        row.mime_type = mimetypes.guess_type(original_filename)[0] or "application/octet-stream"
        row.hash = new_hash
        row.status = "processing"
        row.document_metadata = {"original_filename": original_filename}
        db.add(row)
        db.commit()

        text = extract_text(original_filename, content, file_path)
        chunks = _split(text)
        if not chunks:
            row.status = "failed"
            db.add(row)
            db.commit()
            result.failed += 1
            result.errors.append(f"{original_filename}: no extractable text")
            return

        from qdrant_client import models

        client = self._qdrant()
        name = collection_name()
        if client.collection_exists(name):
            client.delete(
                collection_name=name,
                points_selector=models.FilterSelector(
                    filter=models.Filter(
                        must=[models.FieldCondition(
                            key="metadata.document_id",
                            match=models.MatchValue(value=document_id))]
                    )
                ),
            )

        docs = []
        ids = []
        for index, chunk in enumerate(chunks):
            metadata = {
                "user_id": user_id,
                "document_id": document_id,
                "file_name": original_filename,
                "filename": Path(file_path).name,
                "chunk_index": index,
                "mime_type": row.mime_type,
            }
            docs.append(LangchainDocument(page_content=chunk, metadata=metadata))
            ids.append(str(uuid.uuid5(uuid.UUID(document_id), str(index))))

        store = self._vectorstore()
        for start in range(0, len(docs), UPLOAD_BATCH):
            store.add_documents(
                docs[start:start + UPLOAD_BATCH], ids=ids[start:start + UPLOAD_BATCH]
            )

        row.status = "indexed"
        row.indexed_at = datetime.now(timezone.utc)
        row.document_metadata = {"original_filename": original_filename, "chunks": len(chunks)}
        db.add(row)
        db.commit()
        result.indexed += 1
```

### Step 2 — extend `backend/tests/rag/in_memory.py`

Append:

```python
from types import SimpleNamespace

from langchain_core.documents import Document


class InMemoryStore:
    """Duck-typed QdrantVectorStore stand-in with the same search API."""

    def __init__(self, docs: list[Document] | None = None):
        self._docs: list[tuple[Document, str]] = []
        for doc in docs or []:
            self.add(doc)

    def add(self, doc: Document) -> None:
        self._docs.append((doc, str(len(self._docs))))

    def similarity_search_with_score(self, query: str, k: int = 5, filter=None):
        from qdrant_client import models

        query_lower = query.lower()
        scored = []
        for doc, _point_id in self._docs:
            if filter is not None:
                wanted = {
                    c.match.value
                    for c in filter.must
                    if c.key == "metadata.user_id" and isinstance(c.match, models.MatchValue)
                }
                if wanted and str(doc.metadata.get("user_id")) not in wanted:
                    continue
            overlap = len(set(query_lower.split()) & set(doc.page_content.lower().split()))
            score = 1.0 if overlap else 0.0
            if overlap:
                scored.append((doc, score))
        return scored[:k]


class EchoLLM:
    """Records prompts; returns a fixed reply (never touches the network)."""

    def __init__(self, reply: str = "OK"):
        self.reply = reply
        self.prompts: list = []

    def invoke(self, messages) -> SimpleNamespace:
        self.prompts.append(messages)
        return SimpleNamespace(content=self.reply)
```

### Step 3 — `backend/tests/rag/test_ingest.py`

```python
import zipfile
from pathlib import Path

import pytest

from src.rag.ingest import ALLOWED_EXTENSIONS, DocumentIngestor, extract_text
from tests.rag.in_memory import FakeEmbedder

# Valid minimal PDF with correct xref offsets (verified against installed pypdf 6.19.0)
MINI_PDF = (
    b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
    b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
    b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
    b"/Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n"
    b"4 0 obj\n<< /Length 46 >>\nstream\nBT /F1 24 Tf 72 720 Td (Hello RAG world) Tj ET\n"
    b"endstream\nendobj\n5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\n"
    b"endobj\nxref\n0 6\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n"
    b"0000000115 00000 n \n0000000241 00000 n \n0000000337 00000 n \n"
    b"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n407\n%%EOF\n"
)


def make_docx(text: str) -> bytes:
    document_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body><w:p><w:r><w:t>{text}</w:t></w:r></w:p></w:body></w:document>"
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/word/document.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
        "</Types>"
    )
    rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
        "</Relationships>"
    )
    buffer = __import__("io").BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        zf.writestr("[Content_Types].xml", content_types)
        zf.writestr("_rels/.rels", rels)
        zf.writestr("word/document.xml", document_xml)
    return buffer.getvalue()


@pytest.fixture
def ingestor(qdrant_client, tmp_path):
    return DocumentIngestor(
        client=qdrant_client, embedder=FakeEmbedder(), uploads_dir=tmp_path / "uploads"
    )


def _count(client) -> int:
    from src.rag.store import collection_name

    return client.count(collection_name()).count


def test_txt_upload_indexes_row_and_points(ingestor, qdrant_client, db_session):
    result = ingestor.ingest_upload(db_session, "1", [("notes.txt", b"alpha beta gamma")])
    assert (result.indexed, result.failed) == (1, 0)
    assert _count(qdrant_client) >= 1
    from sqlmodel import select
    from src.models.rag import Document

    row = db_session.exec(select(Document).where(Document.user_id == "1")).one()
    assert row.status == "indexed"
    assert row.hash and len(row.hash) == 64
    assert row.indexed_at is not None


def test_duplicate_upload_skips(ingestor, qdrant_client, db_session):
    payload = b"same content every time"
    ingestor.ingest_upload(db_session, "1", [("a.txt", payload)])
    before = _count(qdrant_client)
    result = ingestor.ingest_upload(db_session, "1", [("a.txt", payload)])
    assert result.skipped == 1 and result.indexed == 0
    assert _count(qdrant_client) == before


def test_changed_content_reindexes(ingestor, db_session):
    ingestor.ingest_upload(db_session, "1", [("a.txt", b"version one")])
    result = ingestor.ingest_upload(db_session, "1", [("a.txt", b"version two changed")])
    assert result.indexed == 1


def test_unsupported_extension_fails(ingestor, db_session):
    result = ingestor.ingest_upload(db_session, "1", [("malware.exe", b"MZ")])
    assert result.failed == 1 and "unsupported extension" in result.errors[0]
    assert result.indexed == 0


def test_pdf_text_extracted(ingestor, db_session, qdrant_client):
    result = ingestor.ingest_upload(db_session, "1", [("doc.pdf", MINI_PDF)])
    assert result.indexed == 1
    from src.rag.store import collection_name

    points, _ = qdrant_client.scroll(collection_name(), limit=10, with_payload=True)
    assert any("Hello RAG world" in p.payload["page_content"] for p in points)


def test_docx_text_extracted(ingestor, db_session):
    result = ingestor.ingest_upload(
        db_session, "1", [("brief.docx", make_docx("quarterly plan overview"))]
    )
    assert result.indexed == 1
    assert not [e for e in result.errors]


def test_empty_text_marks_failed(ingestor, db_session):
    result = ingestor.ingest_upload(db_session, "1", [("empty.txt", b"")])
    assert result.failed == 1
    assert "no extractable text" in result.errors[0]


def test_reset_user_only_clears_own_data(ingestor, qdrant_client, db_session):
    ingestor.ingest_upload(db_session, "1", [("one.txt", b"users one document")])
    ingestor.ingest_upload(db_session, "2", [("two.txt", b"users two document")])
    before = _count(qdrant_client)
    deleted = ingestor.reset_user(db_session, "1")
    assert deleted >= 1
    assert _count(qdrant_client) == before - deleted

    from qdrant_client import models
    from src.rag.store import collection_name

    points, _ = qdrant_client.scroll(
        collection_name(),
        scroll_filter=models.Filter(
            must=[models.FieldCondition(key="metadata.user_id",
                                        match=models.MatchValue(value="2"))]
        ),
        limit=10,
    )
    assert len(points) >= 1
    from sqlmodel import select
    from src.models.rag import Document

    remaining = db_session.exec(select(Document)).all()
    assert {r.user_id for r in remaining} == {"2"}


def test_allowed_extensions_contract():
    assert ALLOWED_EXTENSIONS == {".pdf", ".txt", ".md", ".markdown", ".docx"}
    assert extract_text("a.txt", "héllo".encode(), Path("a.txt")) == "héllo"
```

### Verification + commit

```bash
cd backend && .venv/bin/python -m pytest tests/rag/test_ingest.py tests/rag/test_store.py -q   # 13 passed
git add backend/src/rag/ingest.py backend/tests/rag && git commit -m "feat: real document ingestion into Qdrant with row lifecycle"
```

---

## Task 8 — `chain.py` + `chatbot.py` facade

**Files:** `backend/src/rag/chain.py` (new), `backend/src/rag/chatbot.py` (replace placeholder), `backend/tests/rag/test_chain.py`

### Step 1 — `backend/src/rag/chain.py`

```python
"""Retrieval-augmented answer chain: filtered search -> grounded prompt -> sources."""
from __future__ import annotations

from typing import Callable

from langchain_core.messages import HumanMessage

from ..llm.provider import make_llm
from .store import get_vectorstore  # cheap: embedder/vectorstore stay lazy behind lru_cache

DEFAULT_K = 5
PROMPT_TEMPLATE = """You are TodoFlow's study assistant. Answer the user's question using ONLY the context below, and cite the source file names you used. If the answer is not in the context, say you don't know based on their documents.

Context:
{context}

Question: {question}"""


def _search_kwargs(user_id: str, k: int = DEFAULT_K) -> dict:
    from qdrant_client import models

    return {
        "k": k,
        "filter": models.Filter(
            must=[
                models.FieldCondition(
                    key="metadata.user_id",
                    match=models.MatchValue(value=str(user_id)),
                )
            ]
        ),
    }


def _source_metadata(doc, score: float) -> dict:
    metadata = doc.metadata or {}
    file_name = metadata.get("file_name") or metadata.get("filename") or "unknown"
    return {"file_name": file_name, "score": round(float(score), 4)}


def hits_to_sources(hits) -> list[dict]:
    return [
        {"content": doc.page_content, "metadata": _source_metadata(doc, score)}
        for doc, score in hits
    ]


def create_rag_chain(user_id: str, *, store=None, llm=None) -> Callable[[str], dict]:
    """Build `question -> {"response", "sources"}` for one user.

    Fails fast on a missing LLM key BEFORE touching the vector store.
    """
    if llm is None:
        llm = make_llm()
    store = store or get_vectorstore()

    kwargs = _search_kwargs(str(user_id))

    def _run(question: str) -> dict:
        hits = store.similarity_search_with_score(question, **kwargs)
        context = "\n\n".join(doc.page_content for doc, _ in hits) or "(no documents found)"
        messages = [
            HumanMessage(
                content=PROMPT_TEMPLATE.format(context=context, question=question)
            )
        ]
        answer = llm.invoke(messages)
        return {"response": answer.content, "sources": hits_to_sources(hits)}

    return _run
```

### Step 2 — replace `backend/src/rag/chatbot.py`

```python
"""RAG chatbot facade: per-user cached chains + direct similarity search."""
from __future__ import annotations

from typing import Any, Callable, Dict, List

from .chain import create_rag_chain, hits_to_sources, _search_kwargs


class RAGChatbot:
    def __init__(self, *, store=None, chain_factory=None):
        self._store = store
        self._chain_factory = chain_factory
        self._chains: Dict[str, Callable[[str], dict]] = {}

    def _chain(self, user_id: str) -> Callable[[str], dict]:
        user_id = str(user_id)
        if user_id not in self._chains:
            factory = self._chain_factory or create_rag_chain
            kwargs = {"store": self._store} if self._store is not None else {}
            self._chains[user_id] = factory(user_id, **kwargs)
        return self._chains[user_id]

    def generate_response(self, query: str, user_id: str) -> Dict[str, Any]:
        return self._chain(user_id)(query)

    def search_similar(self, query: str, user_id: str, k: int = 5) -> List[Dict[str, Any]]:
        if self._store is None:
            from .store import get_vectorstore

            self._store = get_vectorstore()
        hits = self._store.similarity_search_with_score(query, **_search_kwargs(user_id, k))
        return hits_to_sources(hits)
```

(`src/rag/__init__.py` stays as-is — both names already exported.)

### Step 3 — `backend/tests/rag/test_chain.py`

```python
import pytest

from src.rag.chain import PROMPT_TEMPLATE, _search_kwargs, create_rag_chain, hits_to_sources
from src.rag.chatbot import RAGChatbot
from langchain_core.documents import Document
from tests.rag.in_memory import EchoLLM, InMemoryStore

ALL_PROVIDER_VARS = [
    "AI_PROVIDER", "OPENAI_API_KEY", "GEMINI_API_KEY", "OPENROUTER_API_KEY",
]


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for var in ALL_PROVIDER_VARS:
        monkeypatch.delenv(var, raising=False)


def _docs():
    return [
        Document(page_content="the office budget is 42 dollars", metadata={"user_id": "1", "file_name": "budget.txt"}),
        Document(page_content="quarterly plan overview", metadata={"user_id": "2", "file_name": "plan.txt"}),
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
```

(The test relies on `chain.py` importing `get_vectorstore` at module level and calling `make_llm()` before it — both guaranteed by Step 1.)

Rest of the tests:

```python
def test_chain_answers_and_returns_sources():
    store = InMemoryStore(_docs())
    chain = create_rag_chain("1", store=store, llm=EchoLLM(reply="The budget is 42 dollars."))
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
    doc = Document(page_content="x", metadata={"user_id": "1", "filename": "stored.txt"})
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
```

### Verification + commit

```bash
cd backend && .venv/bin/python -m pytest tests/rag/test_chain.py -q   # 8 passed
git add backend/src/rag/chain.py backend/src/rag/chatbot.py backend/tests/rag && git commit -m "feat: grounded RAG chain with per-user filter and sources"
```

---

## Task 9 — `rag.py` routes

**Files:** `backend/src/api/v1/rag.py`, `backend/tests/rag/test_rag_routes.py`

Ordered edits to `backend/src/api/v1/rag.py`:

### Edit 1 — imports

Import delta (verified against the file: `re`, `datetime`, `tempfile` are unused anywhere else; `BackgroundTasks` appears only in the upload signature being replaced in Edit 6):

- Add `UploadFile, File` to the `fastapi` import and `from ...database.session import get_session`.
- Delete the `BackgroundTasks` import, the `from ...database.engine import database_engine` line, and the standalone `import tempfile`, `from datetime import datetime`, `import re` lines.
- Delete the `DocumentUploadRequest` class (unused after Edit 6).

Add after the response models (before `detect_intent`):

```python
MAX_FILE_SIZE = 10 * 1024 * 1024
ALLOWED_UPLOAD_EXTENSIONS = {".pdf", ".txt", ".md", ".markdown", ".docx"}


def get_chatbot() -> RAGChatbot:
    return RAGChatbot()


def get_ingestor() -> DocumentIngestor:
    return DocumentIngestor()
```

### Edit 2 — delete globals

Remove:

```python
# Global instances for now (in production, consider dependency injection)
chatbot = RAGChatbot()
ingestor = DocumentIngestor()
```

### Edit 3 — `/chat`

Signature:

```python
@router.post("/chat", response_model=ChatResponse)
async def chat_with_rag(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
    bot: RAGChatbot = Depends(get_chatbot),
):
```

Body changes (inside the existing `try`):

- document branch: `response = bot.generate_response(request.message, str(current_user.id))`
- storage block: replace `with database_engine.get_session() as db:` by removing that line and the extra indent of its body (the `db` param now provides the session); keep `db.commit()`.
- `ChatMessage(..., user_id=str(current_user.id), ...)` (both messages), `ChatSession(..., user_id=str(current_user.id), ...)`.

### Edit 4 — `/sessions` (POST)

```python
async def create_chat_session(
    request: CreateSessionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
```
Dedent the `with database_engine.get_session() as db:` body; `user_id=str(current_user.id)`.

### Edit 5 — `/sessions` (GET) and `/sessions/{session_id}/messages` (GET)

Add `db: Session = Depends(get_session)` param; dedent `with` bodies; `ChatSession.user_id == str(current_user.id)` in both queries.

### Edit 6 — `/upload-and-index` (full replacement)

```python
@router.post("/upload-and-index")
async def upload_and_index_documents(
    files: list[UploadFile] = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
    ingestor: DocumentIngestor = Depends(get_ingestor),
):
    """
    Upload documents and index them into the user's Qdrant collection.
    """
    try:
        payloads: list[tuple[str, bytes]] = []
        rejected = 0
        for upload in files:
            ext = os.path.splitext(upload.filename or "")[1].lower()
            if ext not in ALLOWED_UPLOAD_EXTENSIONS:
                rejected += 1
                continue
            content = await upload.read()
            if len(content) > MAX_FILE_SIZE:
                rejected += 1
                continue
            payloads.append((upload.filename or "unnamed", content))

        if not payloads:
            raise HTTPException(
                status_code=400,
                detail="No valid files. Supported: PDF, TXT, MD, DOCX (max 10MB each).",
            )

        result = ingestor.ingest_upload(db, str(current_user.id), payloads)
        return DocumentIndexResponse(
            success=result.failed == 0,
            message=(
                f"Indexed {result.indexed}, skipped {result.skipped}, "
                f"failed {result.failed}"
                + (f" ({'; '.join(result.errors[:3])})" if result.errors else "")
            ),
            indexed_count=result.indexed + result.skipped,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### Edit 7 — `/index-local-files`

Signature: add `db: Session = Depends(get_session), ingestor: DocumentIngestor = Depends(get_ingestor)`. Keep the `ALLOWED_DOCUMENT_PATH` guard. Replace the `success = ingestor.index_documents(safe_paths)` … block with:

```python
        result = ingestor.ingest_paths(db, str(current_user.id), safe_paths)
        return DocumentIndexResponse(
            success=result.failed == 0,
            message=f"Indexed {result.indexed}, failed {result.failed}",
            indexed_count=result.indexed + result.skipped,
        )
```

### Edit 8 — `/search`

```python
@router.get("/search")
async def search_documents(
    query: str,
    k: int = 5,
    current_user: User = Depends(get_current_user),
    bot: RAGChatbot = Depends(get_chatbot),
):
    """
    Search for documents similar to the query (current user's corpus only).
    """
    try:
        results = bot.search_similar(query, str(current_user.id), k=k)
        return {"results": results, "query": query}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### Edit 9 — `/documents` (GET)

Add `db: Session = Depends(get_session)`; dedent; `Document.user_id == str(current_user.id)`.

### Edit 10 — `/reset-index` (DELETE)

```python
@router.delete("/reset-index")
async def reset_rag_index(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
    ingestor: DocumentIngestor = Depends(get_ingestor),
):
    """
    Reset the current user's RAG index and document rows.
    """
    try:
        user_id = str(current_user.id)
        deleted = ingestor.reset_user(db, user_id)
        return {
            "success": True,
            "message": f"Removed {deleted} indexed chunks and document records for user {user_id}",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

(Admin gate removed per spec: users may clear only their own data — the filter enforces isolation. `ingestor.delete_collection()` placeholder method disappears with the placeholder class.)

### Sanity

```bash
cd backend && .venv/bin/python -m ruff check src/api/v1/rag.py
grep -n "database_engine\|DocumentUploadRequest\|background_tasks" src/api/v1/rag.py  # no hits
```

### `backend/tests/rag/test_rag_routes.py`

```python
from langchain_core.documents import Document as LCDocument
from langchain_qdrant import QdrantVectorStore

from main import app
from src.api.v1 import rag as rag_router
from src.rag.chain import _search_kwargs
from src.rag.ingest import DocumentIngestor
from src.rag.store import collection_name, ensure_collection
from tests.rag.in_memory import FakeEmbedder


class FakeChatbot:
    def __init__(self):
        self.responses = []

    def generate_response(self, query, user_id):
        self.responses.append((query, str(user_id)))
        return {"response": f"answer to {query}", "sources": [{"content": "c", "metadata": {"file_name": "f.txt", "score": 0.9}}]}

    def search_similar(self, query, user_id, k=5):
        return [{"content": "hit", "metadata": {"file_name": "f.txt", "score": 0.5}}]


@pytest.fixture
def fake_chatbot():
    bot = FakeChatbot()
    app.dependency_overrides[rag_router.get_chatbot] = lambda: bot
    yield bot
    app.dependency_overrides.pop(rag_router.get_chatbot, None)


def test_chat_requires_auth(client):
    response = client.post("/api/rag/chat", json={"message": "hello"})
    assert response.status_code == 401


def test_chat_task_intent_keeps_existing_branch(client, auth_headers, fake_chatbot, monkeypatch):
    monkeypatch.setattr(
        rag_router,
        "process_natural_language_command",
        lambda user_id, command: {"response": f"tasks for {user_id}"},
    )
    response = client.post(
        "/api/rag/chat",
        json={"message": "list my tasks"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert "tasks for 1" in response.json()["response"]
    assert fake_chatbot.responses == []  # RAG branch not consulted


def test_chat_document_intent_uses_chatbot(client, auth_headers, fake_chatbot):
    response = client.post(
        "/api/rag/chat",
        json={"message": "what does the report say about budgets?"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["response"].startswith("answer to")
    assert data["sources"][0]["metadata"]["file_name"] == "f.txt"
    assert fake_chatbot.responses[0][1].isdigit()  # str(user_id)


def test_upload_rejects_bad_extension(client, auth_headers):
    response = client.post(
        "/api/rag/upload-and-index",
        files=[("files", ("evil.exe", b"MZ", "application/octet-stream"))],
        headers=auth_headers,
    )
    assert response.status_code == 400


def test_upload_indexes_for_current_user(client, auth_headers, qdrant_client, tmp_path, db_session):
    app.dependency_overrides[rag_router.get_ingestor] = lambda: DocumentIngestor(
        client=qdrant_client, embedder=FakeEmbedder(), uploads_dir=tmp_path / "uploads"
    )
    try:
        response = client.post(
            "/api/rag/upload-and-index",
            files=[("files", ("notes.txt", b"important shared knowledge", "text/plain"))],
            headers=auth_headers,
        )
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["success"] is True
        assert data["indexed_count"] == 1

        from src.rag.store import collection_name

        points, _ = qdrant_client.scroll(collection_name(), limit=10, with_payload=True)
        assert points
        assert points[0].payload["metadata"]["user_id"] == "1"
        assert points[0].payload["metadata"]["file_name"] == "notes.txt"
    finally:
        app.dependency_overrides.pop(rag_router.get_ingestor, None)


class ScopedSearchBot:
    """Delegates to a real QdrantVectorStore the way RAGChatbot does."""

    def __init__(self, qdrant_client):
        self._store = QdrantVectorStore(
            client=qdrant_client, collection_name=collection_name(), embedding=FakeEmbedder()
        )

    def generate_response(self, query, user_id):
        return {"response": "n/a", "sources": []}

    def search_similar(self, query, user_id, k=5):
        hits = self._store.similarity_search_with_score(query, **_search_kwargs(user_id, k))
        return [
            {
                "content": doc.page_content,
                "metadata": {"file_name": doc.metadata.get("file_name"), "score": float(score)},
            }
            for doc, score in hits
        ]


def test_search_is_scoped_to_requesting_user(client, auth_headers, qdrant_client):
    ensure_collection(client=qdrant_client)
    store = QdrantVectorStore(
        client=qdrant_client, collection_name=collection_name(), embedding=FakeEmbedder()
    )
    store.add_documents(
        [
            LCDocument(page_content="alpha notes for user one", metadata={"user_id": "1", "file_name": "one.txt"}),
            LCDocument(page_content="alpha notes for user two", metadata={"user_id": "2", "file_name": "two.txt"}),
        ],
        ids=["aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa", "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"],
    )
    app.dependency_overrides[rag_router.get_chatbot] = lambda: ScopedSearchBot(qdrant_client)
    try:
        response = client.get("/api/rag/search", params={"query": "alpha notes"}, headers=auth_headers)
        assert response.status_code == 200
        files = [r["metadata"]["file_name"] for r in response.json()["results"]]
        assert files == ["one.txt"]
    finally:
        app.dependency_overrides.pop(rag_router.get_chatbot, None)


def test_documents_list_and_reset(client, auth_headers, qdrant_client, tmp_path):
    app.dependency_overrides[rag_router.get_ingestor] = lambda: DocumentIngestor(
        client=qdrant_client, embedder=FakeEmbedder(), uploads_dir=tmp_path / "uploads"
    )
    try:
        client.post(
            "/api/rag/upload-and-index",
            files=[("files", ("mine.txt", b"my own document text", "text/plain"))],
            headers=auth_headers,
        )
        listing = client.get("/api/rag/documents", headers=auth_headers)
        assert listing.status_code == 200
        assert len(listing.json()["documents"]) == 1

        reset = client.delete("/api/rag/reset-index", headers=auth_headers)
        assert reset.status_code == 200
        assert reset.json()["success"] is True

        assert client.get("/api/rag/documents", headers=auth_headers).json()["documents"] == []
        from src.rag.store import collection_name

        assert qdrant_client.count(collection_name()).count == 0
    finally:
        app.dependency_overrides.pop(rag_router.get_ingestor, None)


def test_session_crud_smoke(client, auth_headers):
    created = client.post("/api/rag/sessions", json={"title": "notes"}, headers=auth_headers)
    assert created.status_code == 200
    session_id = created.json()["session_id"]

    listed = client.get("/api/rag/sessions", headers=auth_headers)
    assert listed.status_code == 200
    assert any(s["id"] == session_id for s in listed.json()["sessions"])

    messages = client.get(f"/api/rag/sessions/{session_id}/messages", headers=auth_headers)
    assert messages.status_code == 200
```

**Note:** `/chat` tests exercise the storage path — the `db` param hits the overridden session, and `str(current_user.id)` keeps the str-typed `user_id` columns happy. `detect_intent("what does the report say about budgets?")` → `document_query` (`what does` ✓); `detect_intent("list my tasks")` → `task_management` ✓. The task test monkeypatches `process_natural_language_command` so it never depends on the real agent's internals (the endpoint's `except` would otherwise mask a 500).

### Execution notes (as built)

Deviations made while executing — all verified by the gates below:

1. **`backend/ruff.toml` (new):** `[lint.flake8-bugbear] extend-immutable-calls` for FastAPI's `Depends()/Query()/File()` defaults. Without it B008 flagged 23 instances in `rag.py` (baseline had 9). With it: `rag.py` ruff errors go 35 → 9 (only baseline-equivalent `BLE001`), repo-wide 483 → 406.
2. **Test snippet needed `import pytest`** (omitted from the plan's copy-paste) — added.
3. **`tests/rag/conftest.py`:** added autouse `_clear_rag_rows` (session-scoped DB is shared across test files; `len(documents) == 1` assertions need a clean table per test — users are kept), `_REGISTERED` cache so `register` runs once per session (duplicate email → 409 on later tests), and unique creds `raguser/rag@example.com` (rag tests run before `test_auth.py` alphabetically and would steal `test@example.com`, turning `test_register_user` into a new 400 failure).
4. **Root `tests/conftest.py`:** `override_get_session` now yields a `sqlmodel.Session` (routes call `.exec`, plain sessionmaker lacks it); removed dead `TestingSessionLocal`.
5. **`/index-local-files`:** `except HTTPException: raise` added before the generic handler — the in-loop `raise HTTPException(403)` for disallowed paths was previously swallowed by `except Exception` and surfaced as 500.

### Verification + commit

```bash
cd backend && .venv/bin/python -m pytest tests/rag -q          # 43 passed, 2 skipped
cd backend && .venv/bin/python -m pytest tests -q              # same 10 pre-existing failures only (57 passed)
cd backend && .venv/bin/python -m ruff check src/api/v1/rag.py tests/rag/test_rag_routes.py  # only baseline BLE001 left in rag.py; test file clean
git add backend/src/api/v1/rag.py backend/tests backend/ruff.toml docs/superpowers/plans/2026-10-06-rag-subsystem.md && git commit -m "feat: wire rag routes to real ingestor/chatbot with per-user scoping"
```

---

## Task 10 — Frontend `DocumentUploader`

**File:** `frontend/src/components/rag/DocumentUploader.tsx`

### Edits

1. Add import (after `import { toast } from 'sonner';`):

```tsx
import { useAuth } from '@/contexts/AuthContext';
```

2. Inside the component, before `onDrop`:

```tsx
  const { token, isAuthenticated } = useAuth();
```

3. Extension filter in `onDrop` — replace `['pdf', 'txt', 'md', 'docx', 'doc']` with `['pdf', 'txt', 'md', 'markdown', 'docx']`.

4. Dropzone `accept` — remove the `'application/msword': ['.doc']` entry.

5. `uploadFiles` fetch headers:

```tsx
      const response = await fetch('/api/rag/upload-and-index', {
        method: 'POST',
        body: formData,
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
```

6. Upload button disabled state:

```tsx
            disabled={files.length === 0 || isUploading || !isAuthenticated}
```

7. `supportedFormats` — remove the `.doc` row; adjust the grid class from `md:grid-cols-5` to `md:grid-cols-4`.

8. Dropzone hint text: `Supported formats: PDF, TXT, MD, DOCX (Max 10MB per file)`.

### Verification + commit

```bash
cd frontend && npm run lint
git add frontend/src/components/rag/DocumentUploader.tsx && git commit -m "fix: send Bearer token on document upload, drop legacy .doc"
```

---

## Task 11 — Docs + E2E checklist

**Files:** `README.md`, `CHANGELOG.md` (gitignored — edit anyway, no commit), optional `docs/` note.

### README edits

- Line 5 status: replace `RAG, Redis, the Docker dev stack, and migration tooling are not finished` → `Redis and migration tooling are not finished` (RAG now real).
- Line 44 table: drop the *(RAG is scaffolded …)* note; list `langchain-qdrant`, `onnxruntime`, `tokenizers` instead of `unstructured` mention if convenient (keep `unstructured` listed only if still in requirements — it is; leave the row, remove the scaffold parenthetical).
- Line 154 endpoint row: `RAG chat, sessions, document indexing *(scaffold — indexing is simulated today)*` → `RAG chat with sources, per-user document indexing (Qdrant)`.
- Line 254: `# RAG chatbot/ingest (in progress)` → `# RAG chatbot facade, ingestion, embeddings, Qdrant store`.
- Line 275 Known Limitations item 3 (scaffold paragraph) → replace with:
  - **RAG needs one-time setup** — run `backend/.venv/bin/python scripts/fetch_embeddings_model.py` to download the ONNX embedding model (~90 MB), and configure an AI provider key (`GEMINI_API_KEY` / `OPENAI_API_KEY` / `OPENROUTER_API_KEY`) for answers. Uploaded docs are isolated per user via a `user_id` filter.
- Line 287 roadmap: remove the "Finish RAG" bullet.

### CHANGELOG entry (Unreleased → Added)

```markdown
### Added

- **RAG subsystem** — real document indexing and grounded chat:
  - `POST /api/rag/upload-and-index` now accepts multipart file uploads (PDF, TXT, MD, DOCX ≤ 10 MB), extracts, chunks (1000/200), embeds with local ONNX MiniLM-L6-v2 (384-d), and upserts into Qdrant with `metadata.user_id` isolation.
  - `GET /api/rag/search` and `DELETE /api/rag/reset-index` are per-user (reset no longer admin-gated; it only clears the caller's data).
  - `POST /api/rag/chat` returns grounded answers with `{file_name, score}` sources; the task-management branch is unchanged.
  - New `src/llm/provider.py` resolves openai/gemini/openrouter for both RAG and task chat; OpenRouter is a third `AI_PROVIDER`.
  - `scripts/fetch_embeddings_model.py` downloads committed-tokenizer + gitignored-weights from Hugging Face.
  - Compose: qdrant pinned to `v1.19.2`, backend gets `QDRANT_URL`, `RAG_COLLECTION`, `OPENROUTER_*`.
```

### E2E checklist (manual, Docker now running)

**Your preconditions (run yourself — the plan does not):**

```bash
backend/.venv/bin/pip install -r backend/requirements.txt        # onnxruntime, tokenizers, ...
backend/.venv/bin/python scripts/fetch_embeddings_model.py       # ~90 MB ONNX weights
# in .env add:  AI_PROVIDER=openrouter  and  OPENROUTER_API_KEY=<your free key>
```

Compose picks `OPENROUTER_*`/`AI_PROVIDER` up from `.env` automatically (Task 4 added the pass-through).

**Steps (compose commands with your go-ahead):**

```bash
# 1. stack (backend rebuild installs the new requirements inside the container)
docker compose up -d --build qdrant postgres backend frontend
docker compose ps          # qdrant running (no healthcheck — distroless), backend healthy via /health

# 2. Qdrant reachable from host
curl -s http://localhost:6333/collections | head -c 200

# 3. backend API smoke (register user A → login → bearer → upload → search → chat)
printf 'project kickoff notes: budget is 42 dollars\n' > /tmp/notes.txt
curl -s -X POST localhost:8000/api/register -H 'Content-Type: application/json' \
  -d '{"email":"a@example.com","username":"alice","password":"password123","full_name":"Alice"}'
TOKEN_A=$(curl -s -X POST localhost:8000/api/token \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'username=alice&password=password123' | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')

curl -F "files=@/tmp/notes.txt" -H "Authorization: Bearer $TOKEN_A" \
  localhost:8000/api/rag/upload-and-index
#   → {"success":true,"indexed_count":1,...}
curl -s "localhost:8000/api/rag/search?query=budget" -H "Authorization: Bearer $TOKEN_A"
#   → results[0].metadata.file_name == "notes.txt"
curl -s -X POST localhost:8000/api/rag/chat -H "Authorization: Bearer $TOKEN_A" \
  -H 'Content-Type: application/json' \
  -d '{"message":"what is in my notes about the budget?"}'
#   → grounded answer + sources[0].metadata.file_name == "notes.txt"
#   (without OPENROUTER_API_KEY: HTTP 200 with the "API key is not configured" mock — still a pass)
```

```bash
# 4. isolation: register user B, search with B's token → no hits for A's docs

# 5. frontend: http://localhost:3000 → login → RAG page → upload notes.txt → ask question → sources chip shows notes.txt

# 6. full test suite (host machine, venv)
cd backend && .venv/bin/python -m pytest tests -q    # 10 pre-existing failures, everything in tests/rag green
cd frontend && npm run lint
```

### Verification + commit

```bash
git add README.md && git commit -m "docs: RAG subsystem status, setup, and limitations"
```

---

## Final acceptance

- [ ] `cd backend && .venv/bin/python -m pytest tests -q` → only the 10 documented pre-existing failures; `tests/rag/` fully green (45 tests; the 2 model-dependent embedding tests skip until you run the pip install + fetch, then pass).
- [ ] Lint gate (repo baseline discovered at execution: 483 default-ruff errors, 46 black-unformatted files): every file NEW to this plan is fully `ruff check` + `black --check` clean; pre-existing touched files (`chat_router.py`, `tests/conftest.py`, `src/api/v1/rag.py`, …) must have **zero new ruff violations** vs the baseline commit (`git show f776745:<file> | ruff check --stdin-filename <file> -`). Command: `cd backend && .venv/bin/python -m ruff check src tests`.
- [ ] `cd frontend && npm run lint` → clean.
- [ ] Compose parses; qdrant pinned `v1.19.2`; backend env carries `QDRANT_URL=http://qdrant:6333`.
- [ ] E2E checklist run against the live Docker stack: upload → search → chat with sources (needs your OpenRouter key; without it the graceful mock) → cross-user isolation.
- [ ] Spec coverage: §3 architecture (all six components), §4 payload/`metadata.user_id`, §5 all endpoints, §6 compose, §7 config/deps, §8 testing (unit + route tests, no network), §9/§10 untouched.
