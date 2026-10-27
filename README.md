# Todo_App

**TodoFlow** — a full-stack task-management application with JWT authentication, statistics dashboards, an AI chat assistant, and RAG chat over your own uploaded documents, built with FastAPI and Next.js for developers who want a production-shaped reference project to review, run, and contribute to.

## Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Architecture](#architecture)
- [Quickstart](#quickstart)
- [Usage](#usage)
- [Configuration](#configuration)
- [Testing & Linting](#testing--linting)
- [Troubleshooting](#troubleshooting)
- [Project Structure](#project-structure)
- [Contributing](#contributing)
- [License](#license)

## Features

- **Authentication** — register, login, token refresh, and revoke flows with JWT (HS256) and Argon2id password hashing.
- **Task management** — full CRUD plus status/priority/due-date filters, text search, pagination, and a one-click completion toggle.
- **Statistics** — per-user totals, active/completed/overdue counts, priority breakdown, and completion rate.
- **Dashboard** — filter tabs (all/pending/completed), search, sorting, recent activity, and an inline task form.
- **AI chat assistant** — LLM function-calling over task tools (`add_task`, `list_tasks`, `complete_task`, `delete_task`, `update_task`), embedded as a widget on every main page; replies gracefully with a "not configured" message when no AI provider key is set.
- **RAG document chat** — upload PDF/TXT/MD/DOCX (≤ 10 MB), chunked and embedded with a local ONNX MiniLM-L6-v2 model, indexed per-user in Qdrant, with grounded answers and `{file_name, score}` sources. The full-screen `/chat` workspace offers a paperclip-based native file picker with a **Universal ⇄ This chat** scope chip, per-document keep-toggle and delete, and overlay drawers for grouped history and the document registry.
- **MCP server** — eight task tools exposed over stdio for MCP-compatible clients
  (`backend/src/mcp/server.py`, setup in `backend/docs/mcp.md`).
- **Security middleware** — rate limiting, security headers, CORS controls, input validation, trusted-host checks, and custom exception handlers.
- **UI** — light/dark/system themes, animated transitions, and an accessibility panel (font scaling, high contrast, reduced motion).

## Tech Stack

### Backend

| Layer | Technology |
| --- | --- |
| Framework | FastAPI ≥ 0.115 (Python 3.11) |
| ORM | SQLModel ≥ 0.0.18 + SQLAlchemy ≥ 2.0.35 |
| Database | PostgreSQL 16 (required — SQLite is explicitly rejected) |
| Auth | `python-jose` (JWT HS256), `argon2-cffi` (Argon2id) |
| AI / RAG | LangChain, `langchain-openai`, `langchain-google-genai`, `langchain-qdrant`, `qdrant-client`, `pypdf`, `unstructured`, `onnxruntime`, `tokenizers` |
| Agents / Tools | `mcp` (Model Context Protocol) |
| Tooling | pytest, black, ruff, mypy |

### Frontend

| Layer | Technology |
| --- | --- |
| Framework | Next.js 16.1.1 (App Router) + React 19.2.3 |
| Language | TypeScript 5.9 |
| Styling | Tailwind CSS 4.1, `cva`, `tailwind-merge` |
| Forms & validation | react-hook-form, zod |
| HTTP / state | axios, React contexts |
| Motion & icons | framer-motion, lucide-react, Heroicons |

## Architecture

```
Browser
  │
  ▼
Next.js frontend (:3000)          — auth context, route guards, SSR pages
  │  axios /api/*  +  next.config rewrite
  ▼
FastAPI backend (:8000)           — routers, security middleware, JWT deps
  │
  ├──► PostgreSQL / Neon          — users, tasks, chat sessions (SQLModel)
  ├──► Qdrant (:6333)             — per-user document vectors (384-d MiniLM)
  └──► AI provider                — openai | gemini | openrouter via LangChain (optional)
```

- Routers are mounted under `/api` in `backend/main.py`; OpenAPI docs are served at `/api/docs`.
- RAG pipeline: upload → extract (pypdf/text) → chunk (1000/200) → ONNX embed → Qdrant upsert with `metadata.user_id`; chat retrieves the top-5 chunks filtered by the caller's user id **and** an SQL-computed allow-list of active, in-scope documents (universal, or chat-scoped and bound to the session) before answering from a grounded prompt.
- Frontend route protection lives in `frontend/src/proxy.ts` (middleware) plus `ProtectedRoute` components.
- Tables are created automatically at startup; there is no migration directory yet.

## Quickstart

### Prerequisites

- Docker + docker-compose
- Python 3.11+
- Node.js 20+

### 1. Clone

```bash
git clone https://github.com/Mhammadkhan17/Todo_App.git
cd Todo_App
```

### 2. Start PostgreSQL

```bash
docker-compose up -d postgres
```

### 3. Configure the backend

Copy the template and fill in your real values (works with any PostgreSQL, e.g. [Neon](https://neon.com)):

```bash
cp .env.example .env
# edit .env → set DATABASE_URL (your Neon connection string) and JWT_SECRET_KEY
```

The backend loads `.env` from the repo root automatically at startup.

### 4. Run the backend

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

API docs: <http://localhost:8000/api/docs> · Health check: <http://localhost:8000/health>

### 5. Run the frontend

```bash
cd ../frontend   # from backend/
npm install
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000 npm run dev
```

App: <http://localhost:3000>

### 6. Enable RAG (optional)

```bash
# vector store
docker compose up -d qdrant

# local embedding model (~90 MB ONNX weights, tokenizer committed)
backend/.venv/bin/python scripts/fetch_embeddings_model.py

# .env: pick one provider
#   AI_PROVIDER=openrouter  +  OPENROUTER_API_KEY=...   (free tier works)
#   AI_PROVIDER=gemini      +  GEMINI_API_KEY=...
#   AI_PROVIDER=openai      +  OPENAI_API_KEY=...
```

Without an AI provider key, RAG endpoints still index and search documents but chat returns a graceful "not configured" reply. Without the fetched model, upload indexing fails and the two embedding tests skip.

> **Note:** the full Docker dev stack (`docker-compose build backend`) currently fails because of a build-target mismatch. Running the two apps locally as above is the supported path today.

## Usage

### API surface

All application routes are prefixed with `/api`. Routes marked **Bearer** require `Authorization: Bearer <access_token>`.

| Method | Endpoint | Purpose | Auth |
| --- | --- | --- | --- |
| POST | `/api/register` | Create an account | Public |
| POST | `/api/login` | OAuth2 form login → tokens | Public |
| POST | `/api/token` | JSON login → tokens | Public |
| POST | `/api/refresh` | Refresh an access token | Refresh token |
| POST | `/api/revoke` | Revoke tokens (logout) | Bearer |
| GET | `/api/me` | Current user profile | Bearer |
| GET/PUT/DELETE | `/api/{user_id}` | Read / update / delete a user | Bearer (self or admin) |
| GET | `/api/{user_id}/stats` | Task statistics | Bearer |
| GET | `/api/{user_id}/tasks` | List tasks (`status_filter`, `priority`, `due_date_from/to`, `search`, `page`, `size`) | Bearer |
| POST | `/api/{user_id}/tasks` | Create a task | Bearer |
| GET/PUT/DELETE | `/api/{user_id}/tasks/{task_id}` | Read / update / delete a task | Bearer |
| PATCH | `/api/{user_id}/tasks/{task_id}/complete` | Toggle completion | Bearer |
| POST | `/api/chat` | AI assistant (LLM + tool calls) | Bearer |
| GET | `/api/chat/conversations` | List conversations | Bearer |
| POST | `/api/rag/chat` | Grounded RAG answer with sources (task commands share this route; `document_ids` binds pending chat-scoped docs) | Bearer |
| POST | `/api/rag/upload-and-index` | Multipart upload → extract, chunk, embed, index (form: `scope` = `universal`\|`chat`, optional `session_id`) | Bearer |
| GET | `/api/rag/search?query=` | Similarity search over the caller's kept documents only | Bearer |
| GET | `/api/rag/sessions` | List chat sessions | Bearer |
| POST | `/api/rag/sessions` | Create a chat session | Bearer |
| GET | `/api/rag/sessions/{id}/messages` | Messages of one session (owner only) | Bearer |
| GET | `/api/rag/documents` | List the caller's indexed documents | Bearer |
| PATCH | `/api/rag/documents/{id}` | Keep-toggle: `is_active` false = kept in library, excluded from retrieval | Bearer |
| DELETE | `/api/rag/documents/{id}` | Delete one document (chunks, stored file, row) | Bearer |
| DELETE | `/api/rag/reset-index` | Clear the caller's chunks and document rows | Bearer |
| GET | `/health` | Health check | Public |

### Example: create a task

```bash
# 1. Register and log in
TOKEN=$(curl -s -X POST http://localhost:8000/api/token \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","password":"secret-pass"}' | jq -r .access_token)

USER_ID=$(curl -s http://localhost:8000/api/me \
  -H "Authorization: Bearer $TOKEN" | jq -r .id)

# 2. Create a task
curl -s -X POST "http://localhost:8000/api/$USER_ID/tasks" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"Review pull requests","priority":"HIGH","status":"ACTIVE"}'
```

### AI chat and MCP

Chat requests to `POST /api/chat` are executed by `backend/src/agents/todo_agent.py`,
which calls the shared task service. The stdio MCP server at
`backend/src/mcp/server.py` exposes the same operations to MCP-compatible clients.
See `backend/docs/mcp.md` for client configuration. Without an AI provider key,
the chat endpoint returns a graceful "not configured" reply.

### RAG document chat

End-to-end example against a running backend (see Quickstart step 6 for setup):

```bash
# 1. Log in
TOKEN=$(curl -s -X POST http://localhost:8000/api/token \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","password":"secret-pass"}' | jq -r .access_token)

# 2. Upload a document → extract, chunk, embed, index
printf 'project kickoff notes: budget is 42 dollars\n' > /tmp/notes.txt
curl -F "files=@/tmp/notes.txt" -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/rag/upload-and-index
#   → {"success":true,"indexed_count":1,...}

# 3. Similarity search (caller's corpus only)
curl -s "http://localhost:8000/api/rag/search?query=budget" \
  -H "Authorization: Bearer $TOKEN"
#   → results[0].metadata.file_name == "notes.txt"

# 4. Grounded chat with sources
curl -s -X POST http://localhost:8000/api/rag/chat \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"message":"what is in my notes about the budget?"}'
#   → answer + sources[0].metadata.file_name == "notes.txt"
```

In the UI: **`/chat`** → attach files with the composer's paperclip (choose **All_Chats** or **This_Chat** with the scope chip — chat-scoped uploads bind to the conversation on your first message) → ask a question; the reply carries a `Sources [n]` chip. The clock icon opens grouped conversation history (Today / Yesterday / Last 7 days / Earlier); the file icon opens the document registry with status and scope badges, a keep-toggle, and per-row delete. Each user only ever retrieves their own documents (`metadata.user_id` filter plus the per-session allow-list).

## Configuration

Set these in `.env` (copy `.env.example` to `.env` and fill it in), as shell environment variables, or via docker-compose `environment:` blocks. The backend resolves them with `os.getenv`.

> `docker-compose.yml` also provisions **Qdrant** and **Redis** services. Qdrant backs RAG document search; Redis is not consumed by application code yet, so you can ignore it when running locally.

| Variable | Purpose | Example |
| --- | --- | --- |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://todo_user:todo_password@localhost:5432/todo_app` |
| `JWT_SECRET_KEY` | Signing key for access/refresh tokens | *(generate a random string)* |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | Access-token lifetime | `30` |
| `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | Refresh-token lifetime | `7` |
| `ENVIRONMENT` / `DEBUG` | Runtime mode | `development` / `true` |
| `HOST` / `PORT` | Backend bind address | `0.0.0.0` / `8000` |
| `ALLOWED_ORIGINS` | CORS allow-list | `http://localhost:3000` |
| `RATE_LIMIT_ENABLED` | Toggle rate limiting | `true` |
| `SECURITY_HEADERS_ENABLED` | Toggle security headers | `true` |
| `AI_PROVIDER` | `openai`, `gemini`, or `openrouter` | `openrouter` |
| `GEMINI_API_KEY` / `OPENAI_API_KEY` / `OPENROUTER_API_KEY` | Provider credentials | *(optional — chat degrades gracefully without them)* |
| `GEMINI_MODEL` / `OPENAI_MODEL` / `OPENROUTER_MODEL` | Model selection | `nvidia/nemotron-3.5-lightning:free` |
| `QDRANT_URL` | Qdrant server URL | `http://localhost:6333` (compose backend: `http://qdrant:6333`) |
| `RAG_COLLECTION` | Qdrant collection name | `todo_documents` |
| `ALLOWED_DOCUMENT_PATH` | Base dir allowed for `POST /api/rag/index-local-files` | `/app/documents/` |
| `NEXT_PUBLIC_BACKEND_URL` | Frontend → API base URL | `http://localhost:8000` |

## Testing & Linting

### Backend

```bash
cd backend
pytest tests/ -v --tb=short     # 85 tests: auth, tasks, security, health, RAG (unit + route)
```

> Two embedding tests skip until the model is fetched (`scripts/fetch_embeddings_model.py`) and `onnxruntime`/`tokenizers` are installed.

> Tests boot the FastAPI app, which checks for a reachable PostgreSQL. Start Postgres first (`docker-compose up -d postgres`) or point `DATABASE_URL` at a test database.

```bash
./scripts/lint.sh                # black --check, ruff, mypy (via docker-compose)
# or directly:
cd backend && black --check src/ && ruff check src/ && mypy src/ --ignore-missing-imports
```

### Frontend

```bash
cd frontend
npm run lint
```

## Troubleshooting

Every row below is a known, documented issue — check here before opening one.

| Symptom | Cause | Fix |
| --- | --- | --- |
| Backend refuses to start, or `pytest` errors immediately | No reachable PostgreSQL (the app checks at startup) | `docker-compose up -d postgres`, or point `DATABASE_URL` at any reachable database (e.g. Neon) |
| `docker-compose build backend` fails | Compose targets `development`, but `backend/Dockerfile` only defines `builder` and `production` stages | Run the two apps locally per the [Quickstart](#quickstart) — that is the supported path |
| `scripts/dev-start.sh` errors mentioning `adminer` | The script references an undefined `adminer` service | Start services individually (e.g. `docker-compose up -d postgres`) instead |
| `scripts/test.sh` fails on missing directories | It runs `tests/integration/` and `tests/security/`, which do not exist yet | Run `pytest tests/ -v` directly |
| Chat replies "not configured" | No AI provider credentials set | Set `AI_PROVIDER` plus `GEMINI_API_KEY`, `OPENAI_API_KEY`, or `OPENROUTER_API_KEY` (see [Configuration](#configuration)) |
| Embedding tests skip / upload indexing fails with a missing model | ONNX weights not fetched (or `onnxruntime`/`tokenizers` not installed) | `backend/.venv/bin/python scripts/fetch_embeddings_model.py` and `pip install -r backend/requirements.txt` |
| Upload succeeds but chat answers ignore the file | No AI provider key, so chat returns the "not configured" reply | Set an `AI_PROVIDER` + key (Quickstart step 6) |
| Frontend password-reset flow errors | The frontend calls `/api/auth/request-password-reset` and `/api/auth/reset-password`, which have no backend routes yet | Avoid the reset flow for now |
| Frontend cannot reach the API | Wrong base URL | Set `NEXT_PUBLIC_BACKEND_URL=http://localhost:8000` when starting the frontend |

## Project Structure

```
Todo_App/
├── backend/                  # FastAPI API
│   ├── main.py               # App entrypoint: routers, middleware, lifespan
│   ├── requirements.txt      # Python dependencies
│   ├── models/               # ONNX embedding model (tokenizer committed, weights gitignored)
│   ├── ruff.toml             # ruff config (FastAPI Depends exemptions)
│   ├── src/
│   │   ├── api/              # tasks, users, chat routers + api/v1/rag.py
│   │   ├── auth/             # auth router, JWT service, password hashing
│   │   ├── agents/           # LLM agent + task tool functions
│   │   ├── llm/              # provider resolver (openai | gemini | openrouter)
│   │   ├── mcp/              # MCP stdio server (5 todo tools)
│   │   ├── models/           # SQLModel models (User, Task, RAG)
│   │   ├── database/         # engine, sessions, table setup
│   │   ├── security/         # middleware, CORS, validation, config
│   │   ├── rag/              # chain, chatbot, ingestion, embeddings, Qdrant store
│   │   └── schemas/          # Pydantic request/response schemas
│   └── tests/                # pytest suite (85 tests, tests/rag/ for the RAG subsystem)
├── frontend/                 # Next.js app
│   └── src/
│       ├── app/              # routes: auth, dashboard, tasks, stats, chat, settings
│       ├── components/       # auth, chat, layout, tasks, rag, ui
│       ├── contexts/         # AuthContext, ThemeContext
│       ├── hooks/            # useAuth, useTasks
│       └── lib/              # axios client, API helpers
├── scripts/                  # setup, dev start/stop, test, lint, fetch_embeddings_model helpers
├── docker-compose.yml        # dev: postgres, backend, frontend, qdrant (v1.19.2), redis
└── docker-compose.prod.yml   # production build targets
```

## Contributing

Contributions are welcome — not sure where to start? Open an issue.

1. Fork the repository and create a feature branch: `git checkout -b feature/my-change`
2. Set up the project following the [Quickstart](#quickstart)
3. Make your changes with focused commits
4. Add or update tests where it makes sense (`pytest tests/ -v`)
5. Run linters (`black` / `ruff` / `mypy` for backend, `npm run lint` for frontend)
6. Open a pull request describing the change and its motivation

For larger changes, open an issue first to discuss the approach. Bug reports and feature requests are welcome via [GitHub Issues](https://github.com/Mhammadkhan17/Todo_App/issues).

## License

Released under the [MIT License](LICENSE) — free to use, modify, and distribute with attribution. See [`LICENSE`](LICENSE) for the full text.
