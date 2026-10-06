# RAG Subsystem Design — User-Uploaded Documents over Qdrant

**Date:** 2026-10-06
**Status:** Approved (section-by-section, in chat)
**Reference implementation:** `rag-example/` (previous project's RAG: `rag_implementation.md` walkthrough, `rag_instruction.md` checklist)

## 1. Intent

Turn TodoFlow's stubbed RAG stack into a working subsystem: users upload documents (PDF/TXT/MD/DOCX), the backend chunks and embeds them into a local Qdrant vector store, and the `/chat` page answers questions grounded in the user's own documents with visible sources.

Today the plumbing exists end-to-end but is fake: `backend/src/rag/ingest.py` and `chatbot.py` are placeholders (canned responses, `index_documents` always returns `True`), `POST /api/rag/upload-and-index` expects JSON `{file_urls}` while the frontend sends multipart `FormData` **with no `Authorization` header** (every `/rag` endpoint sits behind `HTTPBearer` — so uploads 401 today), and `POST /api/rag/chat`'s `document_query` branch returns an echo string.

Success = the existing `/chat` page and `DocumentUploader` work against real retrieval with no *contract-shape* changes (the auth header and `.doc` removal in §7 are functional fixes, not contract changes), users cannot retrieve each other's documents, and the test suite runs with zero infrastructure (no Qdrant, no ONNX, no LLM key).

## 2. Decisions (recorded)

| # | Question | Decision |
|---|---|---|
| 1 | Corpus | User-uploaded documents (not repo docs, not hybrid task+docs) |
| 2 | Vector store | Qdrant (already provisioned in `docker-compose.yml`) |
| 3 | Embeddings | Local ONNX MiniLM-L6-v2, 384-dim (Approach A: literal port of `rag-example`) |
| 4 | DOCX loader | `python-docx` requested; **`docx2txt` already in `requirements.txt` and will be used instead** (zero new deps) unless implementation reveals a gap |
| 5 | Legacy `.doc` | Dropped — no dependency reads the old binary format; remove from uploader accept list |
| 6 | Chat response style | Keep existing non-streaming JSON contract (no SSE, no frontend reader rewrite) |
| 7 | Endpoint scope | All of them: `chat`, `upload-and-index`, `search`, `documents`, `reset-index`, `index-local-files` |
| 8 | Approach | **A** — port `rag-example` architecture (`embeddings.py`, `store.py`, `ingest.py`, `chain.py`) |
| 9 | LLM providers | Add **OpenRouter** as a third `AI_PROVIDER`, used by *both* the RAG chain and the existing task-chat assistant |
| 10 | Qdrant auth | **None locally** (dev/test on localhost); optional `QDRANT_API_KEY` env read by the backend so cloud in production is env-only |
| 11 | Qdrant container | Refresh the stale service in `docker-compose.yml` (see §6) |
| 12 | Retrieval scope | Per-user via `user_id` payload filter (the `chapter_id` pattern, re-scoped) |
| 13 | Task intent branch | `detect_intent()` and the `task_management` branch stay as-is; only `document_query` gets RAG |

## 3. Architecture & data flow

```
UPLOAD                                    CHAT (document_query intent)
──────                                    ────────────────────────────
FormData files                            POST /api/rag/chat {message}
  │                                         │ resolve_llm() — fail fast on key
  ▼                                         ▼
upload-and-index (multipart)              create_rag_chain(user_id)
  │ validate ext (pdf/txt/md/docx) +10MB     │ retriever: k=5, filter user_id
  │ save uploads/{user_id}/{document_id}{ext}│ prompt: grounded tutor (quote the
  │ sha256 → dedup vs Document.hash          │ file; admit when context is silent)
  │ extract (pypdf | docx2txt | utf-8)       ▼
  │ Document: uploaded→processing→indexed   embed query (LocalEmbeddings, ONNX)
  │ split 1000/200 (RecursiveCharacter)       │ Qdrant search (user_id filter)
  │ embed (LocalEmbeddings)                  ▼
  ▼ upsert batches of 64                   context string + prompt → LLM
Qdrant collection "todo_documents"           │
  payload: {user_id, document_id,           ▼
            filename, chunk_index, text}   JSON {response, sources:[{content,
  point id: uuid5(document_id, chunk_index)}           metadata}], session_id}
```

New/changed backend files:

| File | Role |
|---|---|
| `backend/src/rag/embeddings.py` | `LocalEmbeddings` — ONNX MiniLM-L6-v2, masked mean-pool + L2 normalize (port of example §3); fail-fast with pointer to fetch script if weights absent |
| `backend/src/rag/store.py` | Lazy singletons (client/embedder/vectorstore), `ensure_collection` (384-dim cosine, payload indexes on `user_id` and `document_id`, hard-fail on dim mismatch) |
| `backend/src/rag/ingest.py` | Real `DocumentIngestor` (replaces placeholder): extract → split → embed → upsert; purge-before-re-embed by `document_id`; batched writes (64); sha256 dedup; injectable embedder/client for tests |
| `backend/src/rag/chain.py` | `create_rag_chain(user_id, retriever=None, llm=None)`, `_search_kwargs`, grounded prompt, sources assembly — port of example §4/§6 with injection seams |
| `backend/src/rag/chatbot.py` | Replaced/thinned: its public entry (`generate_response`, `search_similar`) delegates to `chain.py` so `rag.py`'s imports keep working |
| `backend/src/llm/provider.py` | `resolve_llm() → LLMConfig(api_key, base_url, model, headers)` — shared by RAG and task-chat |
| `scripts/fetch_embeddings_model.py` | Downloads the vendored ONNX model (tokenizer/config committed; 87MB weights gitignored) — fixes the fresh-clone footgun documented in `rag_implementation.md` §3 |
| `backend/src/api/v1/rag.py` | Endpoint changes per §5 |

## 4. Components

### 4.1 Embeddings (`embeddings.py`)

Port of the example: vendored `tokenizer.json` → ONNX forward → masked mean pooling → L2 normalize → 384-d unit vectors. `embed_query` and `embed_documents` use the identical pipeline (mandatory). Model lives at `backend/models/all-MiniLM-L6-v2/`; `tokenizer.json`/`config.json` committed, `onnx/` weights gitignored; `LocalEmbeddings.__init__` raises a clear error naming `scripts/fetch_embeddings_model.py` when weights are missing.

### 4.2 Vector store (`store.py`)

- Collection `todo_documents` (env `RAG_COLLECTION`), 384-dim, `Distance.COSINE`.
- Payload keyword indexes on `user_id` and `document_id`.
- Lazy process-wide singletons (example §4.1); `QdrantClient(url=QDRANT_URL, api_key=os.getenv("QDRANT_API_KEY") or None)` — unset locally, settable for Qdrant Cloud.
- Dim mismatch on existing collection → hard error (example §2.2).

### 4.3 Ingestion (`ingest.py`)

**Ownership:** the ingestor owns the full per-file lifecycle — dedup, `Document`-row create/update, status transitions, extraction, embedding, upsert. Both `upload-and-index` and `index-local-files` endpoints call it and stay thin (no divergent row-creation paths — the current local-files endpoint creates rows itself; that moves into the ingestor).

**Row identity rule (critical for purge/dedup/reset to compose):** one `Document` row per `(user_id, original_filename)`.

| Upload scenario | Action |
|---|---|
| New `(user, filename)` | Create row (new `document_id`) → extract → embed → `indexed` |
| Same `(user, filename)`, same hash, `status="indexed"` | Skip — no re-embed (dedup short-circuit) |
| Same `(user, filename)`, same hash, status ≠ `indexed` (e.g. after reset) | Re-ingest: purge points by `document_id`, re-embed → `indexed` |
| Same `(user, filename)`, different hash (changed file) | Update row **in place** (keep `document_id`), purge points by `document_id`, re-embed with new hash |
| Same filename, genuinely different file | Overwrites the previous one — accepted trade-off (§10) |

This is what makes "purge by `document_id`" safe: the id survives file versions, so no orphaned points and no stale chunks stay retrievable.

Per-file pipeline:
- **Storage:** `backend/data/uploads/{user_id}/{document_id}{ext}` (id-based disk name avoids same-name clobbers; `mkdir -p` before write).
- **Extraction:** `pypdf` (PDF), `docx2txt` (DOCX), UTF-8 decode with `autodetect` fallback (TXT/MD). Empty extraction → `status="failed"` with reason in `document_metadata`.
- **Chunking:** `RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)`.
- **Point IDs:** `uuid5(document_id + chunk_index)` — idempotent re-upserts.
- **Changed file:** delete points with `document_id` filter, then upsert (fixes example §2.7 stale-points caveat).
- **Payload:** `{user_id, document_id, filename, chunk_index, text}`.
- **Writes:** batches of 64; injectable `embedder` and Qdrant client constructor args for tests.

### 4.4 Chain (`chain.py`)

- `_search_kwargs(user_id)` → `{"k": 5, "filter": must <user_id field> == <id>}`. **Verify the payload key** the installed `langchain-qdrant` writes (`user_id` flat vs `metadata.user_id`) against one stored point during implementation; a wrong key fails closed (empty results), so a route test must assert the filter key and value, not just "some filter exists".
- Prompt: retrieved context first; quote the document and name the file when it answers; explicitly state the context doesn't cover the question when it doesn't; short questions → short answers; never invent document content.
- Sources = retrieval output (not LLM-generated): `[{content, metadata: {file_name, score}}]`, returned even for "not in my documents" answers. **Key names are dictated by the UI**: `ChatInterface.formatSourceMetadata` renders `file_name` as the bold title (fallback `source`) and dumps every *other* key as a raw `key: value` chip — so use `file_name`, not `filename`, and keep the rest minimal (`score`, rounded; `chunk_index` only if the chip is wanted). Note: scores require a with-score search API (`similarity_search_with_score`-style) — the plain retriever returns scoreless `Document`s; structure the chain accordingly.
- Sources are also persisted verbatim into `ChatMessage.sources` (JSON) — shape above must stay JSON-serializable.
- Precedence: injected `retriever` > injected `llm` > defaults; LLM key check runs before ONNX/Qdrant work (fail fast).

### 4.5 LLM provider (`backend/src/llm/provider.py`)

| `AI_PROVIDER` | Key env | Base URL | Model env (default) |
|---|---|---|---|
| `openai` (default) | `OPENAI_API_KEY` | OpenAI default | `OPENAI_MODEL` (`gpt-3.5-turbo`) |
| `gemini` | `GEMINI_API_KEY` | `GEMINI_BASE_URL` (existing default) | `GEMINI_MODEL` (`gemini-2.0-flash`) |
| `openrouter` | `OPENROUTER_API_KEY` | `https://openrouter.ai/api/v1` | `OPENROUTER_MODEL` (`nvidia/nemotron-3-ultra-550b-a55b:free`) |

- Missing key → `ValueError` naming the env var (routes convert to `500 {detail}`).
- Optional `OPENROUTER_REFERER` → `HTTP-Referer`/`X-Title` attribution headers; no hardcoded URLs.
- `chat_router.py` replaces its inline provider block (lines ~97–117) with the resolver — openai/gemini behavior unchanged; openrouter becomes available to the task assistant.
- RAG wraps the same config in `ChatOpenAI(..., temperature=0.3)`.
- One `AI_PROVIDER=openrouter` switches both RAG and task-chat.

## 5. API surface & error handling

| Endpoint | Change |
|---|---|
| `POST /rag/upload-and-index` | JSON `{file_urls}` → multipart `files: list[UploadFile]`; response stays `DocumentIndexResponse {success, message, indexed_count}`; row/embedding work delegated to the ingestor (§4.3) |
| `POST /rag/chat` | Contract untouched; `document_query` branch → real chain; task branch + session persistence unchanged |
| `GET /rag/search?query&k` | Real retrieval, **user-scoped** — requires changing the existing `search_similar(query, k)` call chain to accept `current_user.id` (it takes no `user_id` today, so "user-scoped" would otherwise be silently false). Returns `{results: [{content, metadata}], query}` |
| `GET /rag/documents` | Untouched (already lists user's `Document` rows) |
| `DELETE /rag/reset-index` | **Per-user:** delete that user's points, set their docs to `status="uploaded"` (re-upload then re-indexes because dedup only skips `indexed`); drop the `@admin.com` gate; fix the local-variable `ingestor` reassignment bug |
| `POST /rag/index-local-files` | Real: keep `ALLOWED_DOCUMENT_PATH` guard → shared ingestor; real `mime_type` via `mimetypes` (replaces hardcoded octet-stream) |
| Sessions endpoints | Untouched |

Seam prerequisite: `rag.py` currently instantiates `chatbot = RAGChatbot()` / `ingestor = DocumentIngestor()` as module globals (lines 50–51). Replace with `Depends(...)` provider functions (chatbot/chain-factory + ingestor) so tests can `dependency_overrides` them; all constructors stay side-effect-free (no Qdrant connection, no ONNX load at import — the example's lazy-singleton rule).

Answer-path ownership: exactly one path generates answers — `chain.py`. `chatbot.py` becomes a pure delegation facade (`generate_response`/`search_similar` → chain) with no logic of its own, so `rag.py`'s existing imports keep working without a parallel second implementation.

Error contract:
- Unsupported extension / >10MB → `400 {detail}` (uploader already enforces both client-side); **batch where no file passes validation → `400 {detail}`**, no rows created.
- Per-file extraction failure → that row `status="failed"`; siblings still index; `indexed_count` = successes, `message` notes failures.
- Missing LLM key / Qdrant unreachable at chat build time → `500 {detail}` (API/debug contract — note the current `ChatInterface`/`DocumentUploader` do **not** read `detail`; they surface generic failure messages. `{detail}` is for curl/tests, not for UI rendering).
- Mid-DB-write surprises → existing exception handlers.
- `ensure_collection` lazy on first store use — empty Qdrant works on first run.

UI coverage: only `upload-and-index` and `chat` have frontend consumers. `search`, `reset-index`, `index-local-files` are API-only (curl/tests) — keep their response shapes stable, don't go looking for UI to update.

## 6. Qdrant container (docker-compose refresh)

Current service (`docker-compose.yml:113–130`) is broken in two ways: `QDRANT_API_KEY` is not the env var Qdrant reads (actual: `QDRANT__API_KEY`), so it runs unauthenticated while appearing configured; and the `wget` healthcheck fails on modern distroless qdrant images (no shell). Refresh:

- Pin an image tag (no `:latest`).
- Remove the ineffective `QDRANT_API_KEY` env (local = no auth, per decision #10).
- Replace healthcheck with a working approach or drop it.
- Keep `container_name: todo_app_qdrant`, `qdrant_data` volume, ports 6333/6334, `todo_network`.
- New env documented in `.env.example`: `QDRANT_URL=http://localhost:6333`, `RAG_COLLECTION=todo_documents`, optional `QDRANT_API_KEY` (cloud only).
- Note: `docker` CLI was unreachable from the WSL session during design (Docker Desktop WSL integration off) — starting containers is a manual/user step until enabled.

## 7. Configuration & dependencies

`.env.example` additions: `AI_PROVIDER` comment gains `openrouter`; `OPENROUTER_API_KEY`, `OPENROUTER_MODEL`, `OPENROUTER_REFERER`, `QDRANT_URL`, `RAG_COLLECTION`, optional `QDRANT_API_KEY`, `ALLOWED_DOCUMENT_PATH` (already referenced in code, undocumented).

`requirements.txt` additions: `langchain-qdrant` (Approach A imports `QdrantVectorStore` — **not currently in requirements**), `onnxruntime`, `tokenizers`, `numpy`, `langchain-text-splitters` (splitters may already arrive transitively via `langchain` — verify, don't add twice). Existing: `qdrant-client`, `langchain`, `langchain-openai`, `langchain-community`, `pypdf`, `docx2txt`.

`.gitignore` additions: `backend/data/uploads/`, `backend/models/**/onnx/` (weights), keep tokenizer/config committed.

Frontend (`DocumentUploader.tsx`) — three small fixes, no contract-shape changes:
1. **Attach `Authorization: Bearer ${token}`** (via `useAuth`, as `ChatInterface` already does) — without this every upload 401s against `HTTPBearer`-protected endpoints. Blocker.
2. Remove `.doc` from the dropzone accept list, the extension filter, and the format legend (backend rejects it anyway, decision #5).
3. Align the extension filter with the accept list while there: `['pdf','txt','md','markdown','docx']` (`.markdown` is currently accepted by dropzone but rejected by the client-side filter — pre-existing dead branch).

Docs: update `README.md` Known Limitations ("RAG is scaffolded … not finished") and add a `CHANGELOG.md` entry — both currently claim RAG doesn't work.

## 8. Testing

New `backend/tests/rag/` (alongside existing conftest/auth/tasks/security suites):

- `in_memory.py` — `InMemoryRetriever` filtered by `user_id`.
- `test_chain.py` — echo-LLM: retrieved text reaches prompt; `_search_kwargs` shape (`k=5`, **filter field name AND value** — catches the flat-vs-`metadata.` payload-key mistake, §4.4); sources shape uses `file_name`; missing-key fail-fast; full injected path needs no env/network/ONNX/Qdrant.
- `test_ingest.py` — fake embedder + fake Qdrant client: extraction per type (tiny fixtures), sha256 dedup skip, **row-identity matrix from §4.3** (new file / unchanged re-upload / status-after-reset re-upload / changed file keeps `document_id` and purges old points first), deterministic point IDs, payload fields, `failed` status path, all-invalid batch → no rows.
- `test_rag_routes.py` — via the `Depends` seams introduced in §5 (`app.dependency_overrides`): multipart upload returns `indexed_count`, chat returns `ChatResponse` shape, **missing Bearer → 401**, reset-index scoped to current user, 400 bad extension, 400 empty-valid batch.
- Embeddings unit test gated `skipif` weights absent.

Test-DB note: existing `conftest.py` creates `User.metadata`/`Task.metadata` explicitly — SQLModel shares one `MetaData` across models and importing `main` registers the RAG tables, so they likely get created transitively; **verify** (not assume) when writing `test_rag_routes.py` — extend `create_all` if rows come back missing.

Run: `cd backend && python -m pytest tests/rag` + existing suite.

## 9. Out of scope

- Streaming responses (decision #6) — revisit only if latency complaints.
- Frontend changes beyond the three `DocumentUploader` fixes in §7 (no chat-UI rework).
- Redis, background-task indexing (noted upgrade if large PDFs are slow), reranking, hybrid BM25, embeddings-as-a-service.
- Task-intent branch changes; MCP server; auth flows.
- Deploying Qdrant Cloud (env-only switch is the extent of production prep).

## 10. Accepted risks & verify-during-implementation

| Item | Status |
|---|---|
| `detect_intent()` keyword misrouting is now user-visible with real RAG (e.g. "What does my task list look like?" ties → `document_query`; "add task per the checklist document" → `task_management`). Ties currently fall to `document_query`, which favors RAG. | **Accepted** — decision #13 keeps `detect_intent` unchanged; revisit only on user complaints |
| Same `(user, filename)` with different content overwrites the previous document | **Accepted** — §4.3 row-identity rule; simplest correct semantics for local use |
| Concurrent uploads of the same file race on row upsert/dedup | **Accepted** — local single-user dev; no locking in MVP |
| Two chat endpoints coexist: `POST /api/chat` (task assistant / CompactChatWidget, function-calling) and `POST /api/rag/chat` (/chat page, RAG). Only shared piece is `provider.py` resolution — do **not** consolidate them. | **Intentional** (decision #9) |
| Payload filter key shape (`user_id` vs `metadata.user_id`) depends on installed `langchain-qdrant` version | **Verify** during implementation (§4.4) + assert in `test_chain.py` |
| RAG tables present in test DB (shared SQLModel `MetaData`) | **Verify** in `test_rag_routes.py` (§8) |
| `docker` CLI unreachable from WSL during design (Docker Desktop WSL integration off) — starting/refreshing the Qdrant container is a manual step until enabled | **Environmental** |
