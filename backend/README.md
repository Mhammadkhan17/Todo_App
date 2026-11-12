---
title: Todo Backend
emoji: ✅
colorFrom: blue
colorTo: green
sdk: gradio
sdk_version: 5.49.1
app_file: main.py
pinned: false
---

# Todo Application Backend

FastAPI backend (auth, tasks, chat, RAG) wrapped with **Gradio** for Hugging Face Spaces free tier.

## Runtime

- **SDK:** Gradio (`gr.mount_gradio_app` over FastAPI)
- **App:** `main.py` (`app` exposed for Gradio/ASGI)
- **Health:** `GET /health` and `GET /api/v1/health` (keep-alive ping)

## Required Space Secrets / Variables

Set these in **Space Settings → Variables and secrets**:

| Name | Required | Notes |
|---|---|---|
| `DATABASE_URL` | After first boot | Prod Postgres/Neon URL. Backend can **boot in bootstrap mode** without it, but DB-backed endpoints won't work until set. |
| `JWT_SECRET_KEY` | Yes (for auth) | Strong random secret (different from dev) |
| `ALLOWED_ORIGINS` | Yes (for browser access) | Comma-separated origins, e.g. `https://<app>.vercel.app,https://<username>-<space>.hf.space`. App boots without it, but browser CORS is blocked until set. |
| `ENVIRONMENT` | Recommended | `production` |
| `DEBUG` | Recommended | `false` |
| `QDRANT_URL` | For RAG | Qdrant Cloud cluster HTTPS URL (see "Qdrant Cloud" in the app repo's `docs/deployment-hf-vercel-qdrant.md`) |
| `QDRANT_API_KEY` | For RAG | Qdrant Cloud **database** API key (no expiration) |
| `RAG_COLLECTION` | No | Default `todo_documents` |
| `EMBEDDING_PROVIDER` | For RAG | `openrouter` = hosted NVIDIA Nemotron-3 (2048-dim, free) — **set this on the Space**; `onnx` = local MiniLM (384-dim, default, needs model weights) |
| `OPENROUTER_EMBED_MODEL` | No | Default `nvidia/nemotron-3-embed-1b:free` |
| `AI_PROVIDER` | For chat | `openrouter` / `openai` / `gemini` |
| `OPENROUTER_API_KEY` / provider key | For chat | As needed by provider; `OPENROUTER_API_KEY` is also required for RAG when `EMBEDDING_PROVIDER=openrouter` |
| `USE_HTTPS` | No | Usually `false` behind HF proxy |
| `CORS_ENABLED` | No | Default `true` |
| `PIP_ROOT_USER_ACTION` | No | Set to `ignore` to suppress HF build warning: "Running pip as the 'root' user..." |
| `PIP_DISABLE_PIP_VERSION_CHECK` | No | Set to `1` to suppress pip upgrade notices in build logs |

> Never commit secrets. Rotate any dev keys before production use.

## API

- Admin/Gateway UI: `/` (Gradio)
- Docs: `/api/docs`
- Health: `/health`, `/api/v1/health`
- Auth: `/api/register`, `/api/token`, `/api/me`
- Tasks: `/api/{user_id}/tasks`
- Chat: `/api/chat`
- RAG: `/api/rag/*`

## What to deploy (backend only)

The HF Space should contain **only the `backend/` directory contents** (this repo is deployed via subtree split / copying `backend/*` to the Space root). Keep `tests/` out of the Space; `.spaceignore` helps reduce uploaded build context/caches (`.git`, `.venv`, `__pycache__`, `data/`, `logs`, archived Docker files).

## Notes

- `Dockerfile`/`.dockerignore` are archived as `*.hf-docker.bak` (HF Docker build not used on free Gradio tier).
- Heavy deps (LangChain/RAG) increase build time and cold-start risk on free CPU. ONNX (`onnxruntime`, `tokenizers`, model weights) is only needed for local `EMBEDDING_PROVIDER=onnx` dev; the Space runs `EMBEDDING_PROVIDER=openrouter` and never loads it.
- **Storage:** your **Neon Postgres** is cloud DB storage and is fine. The “ephemeral” issue is only **local filesystem** used by RAG uploads (`backend/data/uploads/` / `ALLOWED_DOCUMENT_PATH`) and any temp files on the Space — those are lost on restart/rebuild. Qdrant vectors also belong in **Qdrant Cloud** (external), not local Qdrant.
- Qdrant is external: create a Qdrant Cloud cluster and set `QDRANT_URL` + `QDRANT_API_KEY` (collection `todo_documents` is auto-created on first use, 2048-dim when `EMBEDDING_PROVIDER=openrouter`).

## HF launch note
If HF Gradio runtime expects `demo` to be a Gradio Blocks instance, set `demo = admin_panel` and ensure the Space serves the FastAPI-mounted app; this repo currently exports `demo = app` (mounted ASGI) to preserve `/api/*` routes.
