# Deployment: Hugging Face (backend) + Vercel (frontend) + Qdrant Cloud

Main branch: `main` (deploy branch — the former `deploy/hf-backend-test` test branch was squash-merged and deleted)

## 1) Hugging Face Space (backend)

1. Create a **Gradio SDK Space** (owner: your HF account/org). Note the repo as `username/space-name`.
2. Add Space **Variables/Secrets** (Settings → Variables and secrets):
   - `DATABASE_URL` (required) — prod Postgres/Neon URL
   - `JWT_SECRET_KEY` (required) — new strong secret
   - `ALLOWED_ORIGINS` — e.g. `https://<vercel-app>.vercel.app,https://<username>-<space>.hf.space`
   - `ENVIRONMENT=production`, `DEBUG=false`
   - `QDRANT_URL`, `QDRANT_API_KEY`, `RAG_COLLECTION=todo_documents` (when Qdrant Cloud is ready)
   - `EMBEDDING_PROVIDER=openrouter` — hosted Nemotron embeddings (2048-dim; no model weights on the Space)
   - AI provider keys as needed (`AI_PROVIDER`, `OPENROUTER_API_KEY`, etc.; `OPENROUTER_API_KEY` also serves embeddings)
3. **Manual first deploy (simple):**
   ```bash
   # from repo root
   git subtree push --prefix backend https://huggingface.co/spaces/<username>/<space> main
   ```
   Or clone the Space and copy `backend/*` into it (include `README.md` with HF YAML, `Dockerfile`, app code).
4. **CI/CD (GitHub Actions):** add repo secrets
   - `HF_TOKEN` — Hugging Face token with **write** access
   - `HF_SPACE_REPO` — `username/space-name`
   Workflow: `.github/workflows/deploy-backend-hf-space.yml` (pushes on `main` changes under `backend/`, or manual dispatch).

**Gotchas**
- App startup **requires a working `DATABASE_URL`** (lifespan tests DB and creates tables). Space will fail to boot until DB secret is set.
- Port **7860**, bind `0.0.0.0`. HF YAML is in `backend/README.md`.
- Uploads/RAG local files are **ephemeral** on Spaces; Qdrant is external.

## 2) Qdrant Cloud

Free tier (single node, 1 GB) is enough for this app.

1. Sign in at https://cloud.qdrant.io → **Create cluster** → region (nearest you) → **Free** plan.
2. **Access → API keys** → **Create key** → type **Database** (no expiration) → copy it.
3. Copy the cluster **HTTPS URL** (Access → Overview / connection info).
4. On the HF Space (Settings → Variables and secrets) set:
   - `QDRANT_URL=<cluster https url>`
   - `QDRANT_API_KEY=<database key>` (secret)
   - `RAG_COLLECTION=todo_documents` (optional; it's the default)
   - `EMBEDDING_PROVIDER=openrouter`
5. Restart the Space. The backend auto-creates collection `todo_documents` (2048-dim COSINE with payload indexes) on first RAG call — verify it appears in the Qdrant Cloud dashboard after you upload a document.

> Free-tier clusters **suspend after ~1 week idle** and are deleted after ~4 weeks of inactivity; re-runs boot automatically on access within that window. Vectors persist across suspend.

Qdrant **local Docker** stays the dev default (`QDRANT_URL=http://localhost:6333`, no key) — see `docker-compose.yml`.

## 3) Vercel (frontend)

1. Import repo, set **Root Directory** to `frontend`.
2. Set `NEXT_PUBLIC_BACKEND_URL=https://<username>-<space>.hf.space` (before build).
3. Ensure backend `ALLOWED_ORIGINS` includes the Vercel domain.

## Local dev

- Backend: `backend/.venv` + `uvicorn main:app --reload` (or docker compose)
- Frontend: `cd frontend && npm run dev` (rewrites `/api` to `NEXT_PUBLIC_BACKEND_URL`, default localhost:8000)
- Embeddings default to **local ONNX** (`EMBEDDING_PROVIDER=onnx`, 384-dim) — one-time setup: `python scripts/fetch_embeddings_model.py`. Set `EMBEDDING_PROVIDER=openrouter` in `.env` to use the same hosted model as prod (2048-dim; needs `OPENROUTER_API_KEY`).
- Local vectors and Cloud vectors are separate collections in separate databases — never mixed.
