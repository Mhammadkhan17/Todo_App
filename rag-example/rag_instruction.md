# RAG Instruction

**Reference:** [`rag_implementation.md`](./rag_implementation.md) — full annotated walkthrough of a working RAG system (code blocks + logic for ingest, retrieve, LLM config, streaming, test seams). Use it for concrete patterns; this file is only the checklist.

## Goal

A service that: **ingests** a document corpus into Qdrant → **retrieves** top-k chunks per query → **generates** a streamed, grounded answer via an LLM.

## Packages

```text
fastapi
uvicorn
python-dotenv
qdrant-client            # vector DB client
langchain-core           # chains, prompts, retriever interfaces
langchain-qdrant         # QdrantVectorStore
langchain-text-splitters # RecursiveCharacterTextSplitter
langchain-openai         # ChatOpenAI — works against any OpenAI-compatible API
# Embeddings (pick ONE approach):
sentence-transformers    #   simple, or
onnxruntime + tokenizers #   offline/local (pattern in reference §3)
pytest
```

## Setup

1. **Qdrant (Docker, local):**
   ```bash
   docker run -d -p 6333:6333 -v $(pwd)/qdrant_storage:/qdrant/storage qdrant/qdrant
   verify: curl http://localhost:6333/collections
   ```
2. **Env (`.env`, never commit):** LLM API key + provider base URL (e.g. OpenRouter). No other secrets needed for RAG.

## Build (outcomes, not steps)

1. **Ingest (CLI script):** load corpus → split into ~1000-char chunks (~200 overlap) → embed → upsert into one Qdrant collection (384-dim cosine if MiniLM) carrying `source` + chapter/page metadata; support incremental re-runs via content hashes.
2. **Retrieve:** embed the query with the **same model used at index time** → top-k (k≈5) similarity search, optionally filtered by metadata → join chunk texts into one context string.
3. **Generate:** prompt = instructions + retrieved context + question; low temperature (≈0.3); instruct the model to ground answers in the context and admit when it has none.
4. **API:** one `POST` endpoint that builds the chain per request and returns a **streaming** response (`text/plain` chunks); validate config *before* the stream starts and return a structured error (JSON 500) on build failure.
5. **Tests:** make the chain accept an injected retriever/LLM so the suite runs with zero infra (in-memory retriever + echo LLM pattern, reference §10).

## Porting to a new domain

`rag_implementation.md` is domain-shaped — keep its *patterns*, swap these four things:

1. **Loader/chunking** — replace the MDX `DirectoryLoader(**/*.mdx)` with your corpus's loader (PDF/HTML/DB); treat 1000/200 as a starting default, tune per content type.
2. **Metadata filter** — keep one filterable payload field (like `chapter_id`) but redefine it for the domain (folder, doc type, date…).
3. **Prompt** — keep the grounding rules (quote the source; admit when context has no answer), rewrite the persona/questions for the domain.
4. **Models** — any OpenAI-compatible endpoint + **one** embedding model used at both index and query time.

## Rules

- One embedding model everywhere — never mix index-time and query-time models.
- Fail fast: check API key before loading models or touching the DB.
- Vectors and Qdrant data stay local/gitignored; secrets never in git.
