# TodoFlow MCP Implementation Checklist

> Implementation tracker for `plan/MCP_IMPLEMENTATION_PLAN.md`. Check off each step as it completes.

---

## Phase 1: MVP (stdio MCP server)

### Task 1: Fix authentication session isolation

- [x] Step 1: Confirm the failing baseline (`test_login_user` fails with 401)
- [x] Step 2: Add injectable session path to `AuthService.authenticate_user`
- [x] Step 3: Pass request session into both login endpoints
- [x] Step 4: Run auth and task tests — all pass
- [x] Step 5: Commit `fix(auth): use request session for login authentication`

### Task 2: Create the shared TaskService

- [x] Step 1: Add `db_session` fixture to conftest + create `tests/helpers.py` + test package inits
- [x] Step 2: Write failing service tests (7 tests)
- [x] Step 3: Run tests to verify they fail (ModuleNotFoundError)
- [x] Step 4: Implement `TaskService` and `src/services/__init__.py`
- [x] Step 5: Run service tests — all seven pass
- [x] Step 6: Commit `feat(tasks): add shared TaskService with user-scoped CRUD`

### Task 3: Refactor REST endpoints onto TaskService

- [x] Step 1: Confirm current REST tests pass after Task 1
- [x] Step 2: Replace router logic with `TaskService` calls
- [x] Step 3: Add regression test for soft delete
- [x] Step 4: Run REST and service tests — all pass
- [x] Step 5: Commit `refactor(tasks): route REST handlers through TaskService`

### Task 4: Implement MCP identity resolution

- [x] Step 1: Write failing identity tests (4 tests)
- [x] Step 2: Run tests to verify they fail (ModuleNotFoundError)
- [x] Step 3: Implement `src/mcp/identity.py` with `resolve_user_id()`
- [x] Step 4: Run identity tests — four pass
- [x] Step 5: Commit `feat(mcp): resolve user identity from env or verified token`

### Task 5: Build the MCP server and read-only tools

- [x] Step 1: Pin `mcp>=2.3,<3` in requirements.txt
- [x] Step 2: Write failing read-only tool tests (3 tests)
- [x] Step 3: Run tests to verify they fail (ModuleNotFoundError)
- [x] Step 4: Implement `src/mcp/server.py` skeleton + `todo_list_tasks`, `todo_get_task`, `todo_summary`
- [x] Step 5: Run read-only tool tests — three pass
- [x] Step 6: Commit `feat(mcp): add MCPServer with read-only task tools`

### Task 6: Add MCP mutation tools

- [x] Step 1: Write failing mutation tests (3 tests)
- [x] Step 2: Run tests to verify they fail (unknown tools)
- [x] Step 3: Add `todo_create_task`, `todo_update_task`, `todo_complete_task`, `todo_reopen_task`, `todo_delete_task`
- [x] Step 4: Run MCP tests — all six pass
- [x] Step 5: Commit `feat(mcp): add task mutation tools with destructive annotation`

> Note: error-path tests use `pytest.raises(ToolError)` because MCP SDK 2.x raises from `call_tool` instead of returning `is_error=True`.

### Task 7: Add the stdio entrypoint and integration documentation

- [x] Step 1: Add `main()` entrypoint and `src/mcp/__init__.py`
- [x] Step 2: Verify module imports without errors
- [x] Step 3: Verify process starts and waits for stdio (timeout exit 124)
- [x] Step 4: Test with MCP Inspector — eight tools listed
- [x] Step 5: Create `backend/docs/mcp.md` with client configuration
- [x] Step 6: Commit `feat(mcp): add stdio entrypoint and client documentation`

> Note: `__init__.py` uses a lazy `__getattr__` export so `python -m src.mcp.server` does not double-import the module (runpy warning).

### Task 8: Remove the legacy MCP draft and update documentation

- [x] Step 1: Confirm nothing imports `todo_mcp_server`
- [x] Step 2: Delete `backend/src/mcp/todo_mcp_server.py`
- [x] Step 3: Replace chatbot tool bodies with `TaskService` adapters
- [x] Step 4: Update README claims (feature bullet + AI chat/MCP section)
- [x] Step 5: Run full backend test suite — only 3 known security failures remain
- [x] Step 6: Run ruff lint on changed files — no errors
- [x] Step 7: Commit `refactor(mcp): remove legacy draft and route chat tools through TaskService`

---

## Acceptance Criteria (MVP)

- [x] `python -m src.mcp.server` starts and waits for stdio input
- [x] MCP Inspector lists exactly eight tools
- [x] No tool schema contains `user_id`
- [x] `todo_create_task` creates a task for the `MCP_USER_ID` user
- [x] `todo_update_task` updates title without `AttributeError`
- [x] `todo_complete_task` and `todo_reopen_task` are idempotent
- [x] `todo_delete_task` permanently deletes and is annotated destructive
- [x] Cross-user access returns an MCP tool error
- [x] REST endpoints keep same URLs, bodies, and response models
- [x] REST delete remains a soft delete
- [x] Chatbot's five tool calls use `TaskService` and `update_task` works
- [x] No production code imports `todo_mcp_server.py`
- [x] `pytest tests/test_auth.py tests/test_tasks.py tests/services tests/mcp -q` passes
- [x] `ruff check` passes on all files created or modified

> Notes: acceptance coverage lives in `tests/mcp/test_server.py` (MCP_USER_ID binding, idempotent complete/reopen, cross-user errors, destructive/read-only annotations) and `tests/test_todo_agent_tools.py` (five chat tools on TaskService). Ruff required sorting/typing autofixes plus `# noqa: BLE001` on intentional broad catches; `src/auth/jwt_service.py` still has pre-existing lint errors but the plan never modifies it.

---

## Phase 2 Backlog (post-MVP)

### 8.1 Streamable HTTP with per-user JWT

- [x] Add `backend/src/mcp/http.py`
- [x] Implement `JWTTokenVerifier` with `verify_token`
- [x] Build server with `token_verifier` and `AuthSettings`
- [x] Expose `streamable_http_app()` on separate ASGI process or mount at `/mcp`
- [x] Tests: valid token, expired token, cross-user isolation

> Notes: runs as a separate process (`python -m src.mcp.http`, port 8001) rather than
> mounted in the REST app, per the risk-register mitigation. `create_server()` gained
> keyword-only `token_verifier`/`auth` kwargs (stdio passes neither). The entrypoint
> clears `MCP_USER_ID` so HTTP identity can only come from the token subject.
> `AuthSettings(validate_token_resource=False)` is pinned because our JWTs carry no
> RFC 8707 resource claim (SDK 3.0 would otherwise start rejecting them).
> Tests drive the ASGI app in-process via `httpx2.ASGITransport` and the SDK's
> `streamable_http_client`; the app lifespan must run inside the test's task
> (pytest-asyncio fixture teardown is a different task, which anyio rejects).

### 8.2 MCP resources and prompts

- [x] Resources: `todo://tasks/active`, `todo://tasks/completed`, `todo://tasks/{task_id}`
- [x] Prompts: `daily_review`, `prioritize_my_day`, `weekly_plan`
- [x] Reuse `TaskService`; read-only only

> Notes: implemented in `src/mcp/server.py` inside `create_server()` via
> `@mcp.resource`/`@mcp.prompt`; a `read()` helper maps `TodoException`/`ToolError`
> to `ResourceError` (anticipated-failure path, no traceback leak to client).
> Template params are cast by the SDK's `validate_call`, so `task_id: int` works;
> cross-user reads raise `ResourceError("Task with ID N not found")` surfaced to
> the client as `MCPError`. Identity still comes only from `resolve_user_id()`.
> Shared `mcp_server` fixture + `payload`/`mcp_user` helpers moved from
> `test_server.py` to `tests/mcp/conftest.py`; 7 new tests in
> `test_resources_prompts.py`. Full suite: 117 passed + 3 known security failures.

### 8.3 RAG tools

- [x] `todo_search_documents(query, limit)` backed by `src/rag/store.py`
- [x] `todo_ask_documents(question)` backed by `src/rag/chatbot.py`
- [x] Enforce per-user document scoping

> Notes: both tools run inside `run()` with identity from `resolve_user_id()`
> and the `/api/rag`-equivalent SQL allow-list (`active_document_ids`: active
> `Document` rows for this user) passed as `document_ids` — the vector store
> then double-filters on `metadata.user_id`. `RAGChatbot` is imported lazily
> (stdio startup stays light) and built per call, mirroring REST's
> `get_chatbot()`; `create_server(..., rag=...)` lets tests inject a fake
> (`InMemoryStore` + `EchoLLM` chain). Store/LLM failures are wrapped in
> `ToolError` so the model sees the message instead of a generic crash.
> The `mcp_server` fixture gained an overridable `mcp_rag` dependency; tool
> count is now 10 (`test_http.py` assertion updated 8 → 10).
> Full suite: 120 passed + 3 known security failures.

### 8.4 Evaluation suite

- [x] Seed deterministic database with five tasks
- [x] Create ten read-only evaluation questions with verifiable answers
- [x] Run through MCP Inspector or scripted `ClientSession`
- [x] Store as `backend/tests/mcp/evaluations.xml`

> Notes: `evaluations.xml` is the question bank (tool + args + dot-path
> expected value per case, seed documented in its header comment; due dates
> fixed at 2000/2099 so overdue counts never drift). `test_evaluations.py`
> loads it at import, re-seeds the five tasks per case (the autouse
> `_clean_tasks` fixture wipes tasks between cases), and runs each through a
> scripted `Client` — the plan's ClientSession alternative. All ten pass.
> Full suite: 130 passed + 3 known security failures.

### 8.5 Chat as an MCP client

- [x] Measure latency of in-process vs MCP ClientSession
- [x] Replace `call_mcp_tool()` only if external MCP compatibility is required

> Notes: `scripts/mcp_latency_benchmark.py` measures three paths (100 iters,
> 50 tasks): A direct `call_mcp_tool` median **2.92 ms**, B in-process
> `Client(create_server(...))` (a real `ClientSession`) median **3.62 ms** —
> protocol overhead **+0.69 ms/call (1.2×)** — C stdio subprocess median
> **1352.80 ms**. C needs Postgres (subprocess `database_engine` rejects
> SQLite) so it ran against the remote dev DB, where a raw
> `TaskService.list` alone costs ~1361 ms and a pooled `SELECT 1` ~910 ms:
> C's latency is remote-DB round-trips, not MCP transport (rerun with a local
> `DATABASE_URL` to isolate it). Decision: **keep `call_mcp_tool()`
> in-process** — no external MCP consumer exists today; revisit only if
> external MCP compatibility becomes a requirement. Numbers and rationale in
> `backend/docs/mcp.md`.
