# Todo_App

**TodoFlow** — a full-stack task-management application with JWT authentication, statistics dashboards, and an AI chat assistant, built with FastAPI and Next.js for developers who want a production-shaped reference project to review, run, and contribute to.

> **Status:** production-shaped MVP — auth, tasks, statistics, dashboard, and AI chat are real and runnable today; RAG, Redis, the Docker dev stack, and migration tooling are not finished. See [Known Limitations](#known-limitations).

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
- [Known Limitations](#known-limitations)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)

## Features

- **Authentication** — register, login, token refresh, and revoke flows with JWT (HS256) and Argon2id password hashing.
- **Task management** — full CRUD plus status/priority/due-date filters, text search, pagination, and a one-click completion toggle.
- **Statistics** — per-user totals, active/completed/overdue counts, priority breakdown, and completion rate.
- **Dashboard** — filter tabs (all/pending/completed), search, sorting, recent activity, and an inline task form.
- **AI chat assistant** — LLM function-calling over task tools (`add_task`, `list_tasks`, `complete_task`, `delete_task`, `update_task`), embedded as a widget on every main page; replies gracefully with a "not configured" message when no AI provider key is set.
- **MCP server** — the same five tools exposed over stdio for use with MCP-compatible clients.
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
| AI / RAG | LangChain, `langchain-openai`, `langchain-google-genai`, `qdrant-client`, `pypdf`, `unstructured` *(RAG is scaffolded — see [Known Limitations](#known-limitations))* |
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
  ├──► PostgreSQL 16 (:5432)      — users, tasks (SQLModel)
  └──► AI provider                — Gemini or OpenAI via LangChain (optional)
```

- Routers are mounted under `/api` in `backend/main.py`; OpenAPI docs are served at `/api/docs`.
- Frontend route protection lives in `frontend/src/proxy.ts` (middleware) plus `ProtectedRoute` components.
- Tables are created automatically at startup; there is no migration directory yet (see [Known Limitations](#known-limitations)).

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

> **Note:** the full Docker dev stack (`docker-compose build backend`) currently fails because of a build-target mismatch — see [Known Limitations](#known-limitations). Running the two apps locally as above is the supported path today.

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
| * | `/api/rag/*` | RAG chat, sessions, document indexing *(scaffold — indexing is simulated today)* | Bearer |
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

Chat requests to `POST /api/chat` are executed by `backend/src/agents/todo_agent.py`, which calls the same five tools the MCP server (`backend/src/mcp/todo_mcp_server.py`) exposes over stdio. Set an AI provider (see [Configuration](#configuration)) to enable real responses; without a key the endpoint returns a graceful "not configured" reply.

## Configuration

Set these in `.env` (copy `.env.example` to `.env` and fill it in), as shell environment variables, or via docker-compose `environment:` blocks. The backend resolves them with `os.getenv`.

> `docker-compose.yml` also provisions **Qdrant** and **Redis** services. Neither is consumed by application code yet — see [Known Limitations](#known-limitations) — so you can ignore them when running locally.

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
| `AI_PROVIDER` | `gemini` or `openai` | `gemini` |
| `GEMINI_API_KEY` / `OPENAI_API_KEY` | Provider credentials | *(optional — chat degrades gracefully without them)* |
| `GEMINI_MODEL` / `OPENAI_MODEL` | Model selection | `gemini-2.5-flash` |
| `NEXT_PUBLIC_BACKEND_URL` | Frontend → API base URL | `http://localhost:8000` |

## Testing & Linting

### Backend

```bash
cd backend
pytest tests/ -v --tb=short     # 24 tests: auth, tasks, security, health
```

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
| Chat replies "not configured" | No AI provider credentials set | Set `AI_PROVIDER` plus `GEMINI_API_KEY` or `OPENAI_API_KEY` (see [Configuration](#configuration)) |
| Frontend password-reset flow errors | The frontend calls `/api/auth/request-password-reset` and `/api/auth/reset-password`, which have no backend routes yet | Avoid the reset flow for now (tracked in [Known Limitations](#known-limitations)) |
| Frontend cannot reach the API | Wrong base URL | Set `NEXT_PUBLIC_BACKEND_URL=http://localhost:8000` when starting the frontend |

## Project Structure

```
Todo_App/
├── backend/                  # FastAPI API
│   ├── main.py               # App entrypoint: routers, middleware, lifespan
│   ├── requirements.txt      # Python dependencies
│   ├── src/
│   │   ├── api/              # tasks, users, chat, and rag routers
│   │   ├── auth/             # auth router, JWT service, password hashing
│   │   ├── agents/           # LLM agent + task tool functions
│   │   ├── mcp/              # MCP stdio server (5 todo tools)
│   │   ├── models/           # SQLModel models (User, Task, RAG)
│   │   ├── database/         # engine, sessions, table setup
│   │   ├── security/         # middleware, CORS, validation, config
│   │   ├── rag/              # RAG chatbot/ingest (in progress)
│   │   └── schemas/          # Pydantic request/response schemas
│   └── tests/                # pytest suite (24 tests)
├── frontend/                 # Next.js app
│   └── src/
│       ├── app/              # routes: auth, dashboard, tasks, stats, chat, settings
│       ├── components/       # auth, chat, layout, tasks, ui
│       ├── contexts/         # AuthContext, ThemeContext
│       ├── hooks/            # useAuth, useTasks
│       └── lib/              # axios client, API helpers
├── scripts/                  # setup, dev start/stop, test, lint helpers
├── docker-compose.yml        # dev: postgres, backend, frontend, qdrant, redis
└── docker-compose.prod.yml   # production build targets
```

## Known Limitations

Tracked honestly so reviewers know exactly what is real today:

1. **Docker dev build for the backend fails** — `docker-compose.yml` uses `target: development`, but `backend/Dockerfile` only defines `builder` and `production` stages. Use the local Quickstart until the compose target or Dockerfile is fixed.
2. **`scripts/dev-start.sh` starts an undefined `adminer` service**, and **`scripts/test.sh` runs `tests/integration/` and `tests/security/`** directories that do not exist yet (use `pytest tests/` directly).
3. **RAG is a scaffold** — `backend/src/rag/` contains placeholders, and `POST /api/rag/upload-and-index` simulates indexing. Qdrant is provisioned in compose but not yet called by application code.
4. **Redis is provisioned but unused** — no backend code imports it yet.
5. **Password-reset calls in the frontend** (`/api/auth/request-password-reset`, `/api/auth/reset-password`) have no matching backend routes.
6. **No CI workflows and no screenshots** yet; Python dependencies are lower-bounded (`>=`) rather than pinned.
7. **No migration tooling in-repo** — tables are created via `create_all` at startup; Alembic is a dependency but no migration directory is committed.

## Roadmap

Natural next steps, each derived directly from the limitations above — self-contained contribution targets, with no dates promised:

- **Fix the Docker dev stack** — align the compose `target` with the Dockerfile stages, then document a one-command start.
- **Add real migrations** — commit an Alembic migration directory and move off startup `create_all`.
- **Finish RAG** — replace the simulated `/api/rag/upload-and-index` with real Qdrant ingestion and wire the existing dependencies.
- **Use Redis (or drop it)** — consume it for rate limiting / caching, or remove it from compose.
- **Implement password reset** — add the two backend routes the frontend already calls.
- **Add CI and screenshots** — lint + pytest workflows, a screenshot gallery, and pinned (`==`) Python dependencies.
- **Reconcile `scripts/test.sh`** — create the missing test directories it expects, or point it at `tests/`.

## Contributing

Contributions are welcome — not sure where to start? The [Roadmap](#roadmap) lists focused, self-contained targets.

1. Fork the repository and create a feature branch: `git checkout -b feature/my-change`
2. Set up the project following the [Quickstart](#quickstart)
3. Make your changes with focused commits
4. Add or update tests where it makes sense (`pytest tests/ -v`)
5. Run linters (`black` / `ruff` / `mypy` for backend, `npm run lint` for frontend)
6. Open a pull request describing the change and its motivation

For larger changes, open an issue first to discuss the approach. Bug reports and feature requests are welcome via [GitHub Issues](https://github.com/Mhammadkhan17/Todo_App/issues).

## License

Released under the [MIT License](LICENSE) — free to use, modify, and distribute with attribution. See [`LICENSE`](LICENSE) for the full text.
