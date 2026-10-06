# RAG Implementation — Physical AI & Humanoid Robotics Textbook

Deep-dive into how retrieval-augmented generation is implemented in this project: ingestion, embeddings, retrieval, LLM configuration, the answer chain, the API streaming path, and the test seams.

> **Source of truth for this doc:** the code as it exists today —
> `backend/local_ingest.py`, `backend/local_embeddings.py`, `backend/chain.py`, `backend/app.py`,
> `backend/tests/`, `website/src/components/RAGChatbot.tsx`, `website/src/features/ask-ai/`.
>
> **Doc-drift warning:** `AGENTS.md` references a `backend/rag/` directory and `backend/gemini_retrieve.py`
> that **do not exist** in the current tree — ingestion/retrieval actually live in
> `backend/local_ingest.py` and `backend/chain.py` as shown below. Per `CHANGELOG.md`, the project
> migrated from **Qdrant Cloud + Gemini embeddings** (the old `gemini_retrieve.py` / `backend/rag/gemini_ingest.py`
> path) to **local Qdrant + ONNX embeddings**; `local_retrieve.py` was later folded into `chain.py`
> (only an orphan `.pyc` remains in `backend/__pycache__/`). Stale references to the old layout
> survive in `AGENTS.md` and `.vercelignore` (`rag/`, `!gemini_retrieve.py`) — ignore them.

---

## 1. Architecture Overview

```
┌────────────────────────────── OFFLINE (indexing) ──────────────────────────────┐
│                                                                                │
│  website/docs/**/*.mdx ──DirectoryLoader──▶ Document[]                         │
│        │                                (1 doc per .mdx file)                  │
│        │                                              │                        │
│        │                     RecursiveCharacterTextSplitter (1000/200)         │
│        │                                              │                        │
│        │                                        chunk Document[]                │
│        │                                              │                        │
│        │            enrich metadata: chapter_id, source_path, content_hash     │
│        │                                              │                        │
│        │               LocalEmbeddings (ONNX MiniLM-L6-v2, 384-d)              │
│        │                                              │                        │
│        └──────────▶ Qdrant @ localhost:6333  collection "Physical_AI_Textbook_Local" │
│                     vectors: 384-dim COSINE + payload index on metadata.chapter_id   │
└────────────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────── ONLINE (querying) ───────────────────────────────┐
│                                                                                │
│  User highlights text in a doc page                                            │
│        │  (DocItem → useAskAiCapture → selection {text, chapterId})            │
│        ▼                                                                       │
│  RAGChatbot.tsx ──POST /api/chat {message, selected_text?, chapter_id?}──▶     │
│                                                                                │
│  app.py: chat_with_rag()                                                       │
│        │  create_rag_chain(selected_text, chapter_id)                          │
│        │        │                                                              │
│        │        ├── LLM: ChatOpenAI → OpenRouter (nemotron-3 free, temp 0.3)   │
│        │        └── Retriever: QdrantVectorStore.as_retriever(k=5,             │
│        │                     filter: metadata.chapter_id == chapter_id?)       │
│        │                                                                      │
│        ▼                                                                      │
│  LCEL chain: retriever|format_docs ─▶ prompt ─▶ llm ─▶ StrOutputParser         │
│        │                                                                      │
│        ▼                                                                      │
│  StreamingResponse(text/plain) ──chunks──▶ RAGChatbot reader loop ─▶ UI        │
└────────────────────────────────────────────────────────────────────────────────┘
```

**Pipeline in LangChain terms:** Index (`Load → Split → Embed → Store`) happens once via CLI; Retrieve + Generate happen per request inside `create_rag_chain`.

---

## 2. Ingestion — `backend/local_ingest.py`

Fully offline, incremental CLI ingestion of the Docusaurus MDX corpus into a local Qdrant instance.

### 2.1 Configuration

```python
DOCS_DIR = Path(__file__).parent.parent / "website" / "docs"   # corpus root
COLLECTION_NAME = "Physical_AI_Textbook_Local"
QDRANT_URL = "http://localhost:6333"                            # local Qdrant only
VECTOR_DIMENSIONS = 384                                         # matches MiniLM-L6-v2
```

### 2.2 Collection bootstrap + safety checks

```python
def ensure_collection(client: QdrantClient):
    collections = [c.name for c in client.get_collections().collections]
    if COLLECTION_NAME not in collections:
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=VECTOR_DIMENSIONS, distance=Distance.COSINE),
        )
        client.create_payload_index(
            collection_name=COLLECTION_NAME,
            field_name="metadata.chapter_id",
            field_schema=PayloadSchemaType.KEYWORD,
        )
    else:
        collection = client.get_collection(COLLECTION_NAME)
        actual_dim = collection.config.params.vectors.size
        if actual_dim != VECTOR_DIMENSIONS:
            raise ValueError("... Delete the collection first.")
```

**Logic:**
- Vectors are **384-dim cosine** (the output space of `all-MiniLM-L6-v2`).
- A **keyword payload index** on `metadata.chapter_id` is created up front — this is what makes the per-chapter filter at query time an indexed lookup instead of a full scan.
- If the collection already exists with a *different* dimension (e.g., leftover from a previous embedding model), ingestion **hard-fails** instead of silently mixing incompatible vectors.

### 2.3 Loading documents

```python
def load_documents() -> list:
    loader = DirectoryLoader(
        str(DOCS_DIR),
        glob="**/*.mdx",
        loader_cls=TextLoader,
        loader_kwargs={"autodetect_encoding": True},
    )
    return loader.load()
```

One `Document` per `.mdx` file under `website/docs/` (modules 1–4). `autodetect_encoding` guards against non-UTF8 bytes in hand-edited content.

### 2.4 Splitting

```python
splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
)
splits = splitter.split_documents(docs)
```

- **1000 chars/chunk** — large enough to hold a coherent explanation (paragraph + code snippet), small enough for precise retrieval.
- **200 chars overlap (20%)** — sentences that straddle a boundary appear in both neighbors, so context isn't lost at the seam.
- Recursive splitting respects `\n\n → \n → " → ""` separators, so chunks break on paragraph boundaries first, never mid-word.

### 2.5 Metadata enrichment — the chapter_id contract

```python
def derive_chapter_id(source_path: str) -> str:
    file_path = Path(source_path)
    relative_path = file_path.relative_to(DOCS_DIR)
    parts = list(relative_path.parts)
    if parts:
        parts[-1] = re.sub(r"^\d+-", "", parts[-1])   # strip sort prefix from filename
    return str(Path(*parts).with_suffix("")).replace("\\", "/")

for chunk in splits:
    source = chunk.metadata.get("source", "")
    chunk.metadata["chapter_id"] = derive_chapter_id(source)
    chunk.metadata["source_path"] = source
    chunk.metadata["content_hash"] = file_hash(Path(source)) if source else "unknown"
```

**Logic:** each chunk carries three metadata fields:

| Field | Purpose |
|---|---|
| `chapter_id` | Query-time filter — mirrors Docusaurus `metadata.id` (numeric filename prefixes stripped, e.g. `01-ros-nodes-topics-services.mdx` → `ros-nodes-topics-services`) |
| `source_path` | Groups chunks by originating file for incremental updates and orphan cleanup |
| `content_hash` | MD5 of the *file*, stored per chunk so unchanged files can be skipped |

This `chapter_id` must match what the frontend sends (`props.content.metadata.id` from `website/src/theme/DocItem/index.tsx`), otherwise the chapter filter matches nothing and retrieval falls back to empty context.

### 2.6 Incremental logic (default mode)

```python
def get_existing_file_hashes(client) -> dict:
    # scroll ALL points, group point_ids by metadata.source_path,
    # record each file's content_hash → {source_path: {hash, point_ids}}

def delete_orphaned_points(client, current_sources, existing_file_map):
    orphans = set(existing_file_map.keys()) - current_sources
    for source in orphans:
        client.delete(points_selector=PointIdsList(points=existing_file_map[source]["point_ids"]))

# inside ingest():
existing_file_map = get_existing_file_hashes(client)
current_sources = {chunk.metadata["source_path"] for chunk in splits}
delete_orphaned_points(client, current_sources, existing_file_map)

new_splits = [
    split for split in splits
    if split.metadata["source_path"] not in existing_file_map
    or existing_file_map[split.metadata["source_path"]]["hash"] != split.metadata["content_hash"]
]
splits = new_splits
```

**Decision table:**

| Situation | Action |
|---|---|
| File exists in Qdrant, MD5 unchanged | Skipped — no re-embed |
| File exists, MD5 changed | Re-embedded and appended (stale points for that file are replaced by the orphan/hash logic: changed files are re-added; old points for changed files are *not* auto-deleted per-file — see caveat below) |
| File deleted from `website/docs/` | All its points deleted (orphan cleanup) |
| Brand-new file | Embedded and added |

`--full` flag bypasses all of this: `client.delete_collection(...)` → recreate → ingest everything.

```python
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest MDX docs into local Qdrant")
    parser.add_argument("--full", action="store_true", help="Re-ingest all documents")
    args = parser.parse_args()
    ingest(incremental=not args.full)
```

Run as: `python backend/local_ingest.py` (incremental) or `python backend/local_ingest.py --full` (rebuild).

### 2.7 Batched writes

```python
batch_size = 64
for i in range(0, len(splits), batch_size):
    batch = splits[i : i + batch_size]
    vectorstore.add_documents(batch)
```

Chunks are embedded and upserted **64 at a time** — bounds memory, gives progress output, and avoids one giant request to Qdrant. Final count is verified with `client.count(...)`.

> **Caveat worth knowing:** for a *modified* file, the incremental path appends new chunks but only orphan cleanup deletes points for *removed* files — the old chunks of a changed file are keyed by `content_hash` mismatch (re-added) but their previous point IDs aren't explicitly purged. Use `--full` after large content rewrites to guarantee a clean index.

---

## 3. Embeddings — `backend/local_embeddings.py`

A fully offline LangChain `Embeddings` implementation backed by ONNX Runtime. No HuggingFace Hub, no network calls — the model is vendored in `backend/models/all-MiniLM-L6-v2/`.

> **Fresh-clone caveat:** the tokenizer/config files *are* committed, but the 87 MB weights
> (`onnx/model.onnx` + `model.onnx_data`) are **gitignored** (`.gitignore`: "ONNX model — download
> at runtime"). Despite that comment, `LocalEmbeddings` contains **no download logic** — if the
> weights are missing, `ort.InferenceSession(...)` raises at first use. Copy them in manually
> (or restore from an existing checkout / the gitignored HF cache dir
> `backend/models/models--qdrant--all-MiniLM-L6-v2-onnx/`) before ingesting or chatting.

```python
MODEL_DIR = Path(__file__).parent / "models" / "all-MiniLM-L6-v2"

class LocalEmbeddings(Embeddings):
    def __init__(self):
        self.tokenizer = Tokenizer.from_file(str(MODEL_DIR / "tokenizer.json"))
        self.session = ort.InferenceSession(str(MODEL_DIR / "onnx/model.onnx"))
        with open(MODEL_DIR / "config.json") as f:
            config = json.load(f)
        self.pad_id = config.get("pad_token_id", 0)
```

### The embedding math

```python
def _embed(self, texts: list[str]) -> list[list[float]]:
    all_embeddings = []
    for text in texts:
        encoded = self.tokenizer.encode(text)
        inputs = {
            "input_ids": np.array([encoded.ids], dtype=np.int64),
            "attention_mask": np.array([encoded.attention_mask], dtype=np.int64),
            "token_type_ids": np.array([encoded.type_ids], dtype=np.int64),
        }
        outputs = self.session.run(None, inputs)
        token_embeddings = outputs[0][0]                    # (seq_len, hidden_dim)

        # Mean pooling over real (non-pad) tokens
        attention_mask = np.array(encoded.attention_mask)
        input_mask_expanded = attention_mask[:, np.newaxis].astype(np.float32)
        sum_embeddings = np.sum(token_embeddings * input_mask_expanded, axis=0)
        sum_mask = np.clip(input_mask_expanded.sum(), 1e-9, None)
        embedding = sum_embeddings / sum_mask

        # L2 normalize → cosine similarity == dot product
        embedding = embedding / np.linalg.norm(embedding)
        all_embeddings.append(embedding.tolist())
    return all_embeddings

def embed_documents(self, texts): return self._embed(texts)
def embed_query(self, text):      return self._embed([text])[0]
```

**Logic, step by step:**
1. **Tokenize** with the vendored `tokenizer.json` (WordPiece, max 256 tokens for MiniLM).
2. **ONNX forward pass** → per-token embeddings of hidden dim 384.
3. **Mean pooling** — average the token vectors, *masked* so padding tokens contribute nothing (the `1e-9` clip prevents divide-by-zero on empty inputs).
4. **L2 normalize** — every vector lies on the unit sphere, so Qdrant's `COSINE` distance metric reduces to a plain dot product, and scores are comparable across queries.

`embed_query` and `embed_documents` use the **identical model and pipeline** — mandatory; mixing embedding models between index time and query time would make vectors incomparable.

---

## 4. Retrieval — `backend/chain.py`

### 4.1 Connections (lazy module-level singletons)

```python
COLLECTION_NAME = "Physical_AI_Textbook_Local"
QDRANT_URL = "http://localhost:6333"

_client: QdrantClient | None = None
_embedder: LocalEmbeddings | None = None
_store: QdrantVectorStore | None = None

def _default_client() -> QdrantClient:
    global _client
    if _client is None:
        _client = QdrantClient(url=QDRANT_URL)
    return _client

def _default_store() -> QdrantVectorStore:
    global _store
    if _store is None:
        _store = QdrantVectorStore(
            client=_default_client(),
            collection_name=COLLECTION_NAME,
            embedding=_default_embedder(),   # LocalEmbeddings, same model as ingest
        )
    return _store
```

**Logic:** the Qdrant client, embedder, and vector store are created **once per process** and reused across requests — constructing an `InferenceSession` per request would be wasteful. Laziness also means importing `chain.py` never touches the network.

### 4.2 Search kwargs — chapter filter construction

```python
def _search_kwargs(chapter_id: str | None) -> dict:
    search_kwargs = {"k": 5}
    if chapter_id and chapter_id != "General Textbook":
        search_kwargs["filter"] = rest.Filter(
            must=[
                rest.FieldCondition(
                    key="metadata.chapter_id",
                    match=rest.MatchValue(value=chapter_id),
                )
            ]
        )
    return search_kwargs
```

**Logic:**
- Always retrieve **top-5** chunks.
- If a `chapter_id` is provided (and isn't the sentinel `"General Textbook"`), wrap the search in a `must` filter on the pre-indexed `metadata.chapter_id` payload field → retrieval is **scoped to the chapter the user is reading**.
- No `chapter_id` / `"General Textbook"` → unfiltered, whole-corpus search.

```python
def format_docs(docs):
    if not docs:
        print("DEBUG: No documents found for this chapter_id!")
    return "\n\n".join(doc.page_content for doc in docs)
```

Retrieved `Document`s are flattened into a single context string, chunks separated by blank lines.

### 4.3 Retriever assembly in `create_rag_chain`

```python
def create_rag_chain(selected_text: str = None, chapter_id: str = None,
                     retriever=None, embedder=None, llm=None):
    """Precedence: an injected `retriever` wins (embedder/chapter_id ignored)."""
    if llm is None:
        llm = _make_llm(0.3)   # key check FIRST: no ONNX/Qdrant work on a keyless call

    if retriever is None:
        if embedder is None:
            retriever = _default_store().as_retriever(
                search_kwargs=_search_kwargs(chapter_id)
            )
        else:
            store = QdrantVectorStore(
                client=_default_client(),
                collection_name=COLLECTION_NAME,
                embedding=embedder,
            )
            retriever = store.as_retriever(search_kwargs=_search_kwargs(chapter_id))
```

**Three paths, in precedence order:**

1. **`retriever` injected** → used verbatim; `embedder`/`chapter_id` ignored. This is the test seam.
2. **`embedder` injected** → fresh `QdrantVectorStore` bound to that embedder (custom-embedding experiments), still filtered by `chapter_id`.
3. **Default prod path** → shared `_default_store()` + `_search_kwargs(chapter_id)`.

Note the ordering: the **LLM is built first**, so a missing `OPENROUTER_API_KEY` raises *before* any ONNX model loading or Qdrant connection work happens (fail fast on the cheapest check).

---

## 5. LLM Configuration

### 5.1 The answer LLM (RAG chain)

```python
def _make_llm(temperature: float = 0.3) -> ChatOpenAI:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY must be set in backend/.env file for the LLM.")
    return ChatOpenAI(
        model="nvidia/nemotron-3-ultra-550b-a55b:free",
        openai_api_key=api_key,
        openai_api_base="https://openrouter.ai/api/v1",
        temperature=temperature,
        streaming=True,
        default_headers={
            "HTTP-Referer": "https://physical-ai-humanoid-robotics-cours-zeta.vercel.app",
            "X-Title": "Physical AI Textbook",
        },
    )
```

| Setting | Value | Why |
|---|---|---|
| Provider | **OpenRouter** (OpenAI-compatible API) | One key, many models; `langchain_openai.ChatOpenAI` reused via custom base URL |
| Model | `nvidia/nemotron-3-ultra-550b-a55b:free` | Free-tier chat model |
| Temperature | **0.3** for RAG | Low-but-not-zero: mostly faithful quoting of retrieved context, slight flexibility for explanation |
| `streaming` | `True` | Required for `.stream()` in the API route (token-by-token HTTP response) |
| Headers | `HTTP-Referer`, `X-Title` | OpenRouter attribution/app-ranking headers |

Env loading quirk, handled explicitly:

```python
# chain.py — runs at import time, BEFORE app.py's own load_dotenv()
load_dotenv()
```

`chain.py` loads `.env` itself because `app.py` imports it before calling its own `load_dotenv()`.

### 5.2 Other LLM uses (same provider, different settings)

Constructed inline in `app.py`, **not** via `_make_llm`:

| Endpoint | Temperature | Purpose |
|---|---|---|
| `/api/personalize` | **0.7** | Creative rewriting of chapter text to the learner's expertise level |
| `/api/translate` | **0.2** | Near-deterministic translation (Urdu), preserving code blocks |

All three share the same model ID, base URL, API key, and attribution headers.

### 5.3 Agents — no LLM (yet)

`backend/agents/` contains three FastAPI routers (`mermaid_diagram_generator.py`,
`ros2_code_generator.py`, `ros2_doctor.py`) that `AGENTS.md` and the spec (FR-006) advertise as
"AI agent routers". In reality they are **LLM-free placeholders** and **not part of the answer path**:

```python
# backend/agents/mermaid_diagram_generator.py — representative of all three
@router.post("/generate_mermaid_diagram")
async def generate_mermaid_diagram(request: MermaidDiagramRequest):
    # Placeholder for actual Mermaid diagram generation logic
    # In a real scenario, an LLM would parse the prompt and generate Mermaid syntax.
    generated_diagram = f"""```mermaid
graph TD
    A[User Request: {request.prompt}] --> B(Mermaid Diagram Generator Agent)
    ...```"""
    return {"generated_diagram": generated_diagram}
```

- **Zero `ChatOpenAI`/OpenRouter/httpx calls** anywhere in `backend/agents/` — outputs are
  canned f-strings (static templates with the prompt interpolated).
- **Never registered**: `app.py` has no `include_router(...)` for them, so their routes
  (`/generate_mermaid_diagram`, `/generate_ros2_code`, doctor) are not even reachable in the
  running app.
- Consequently the **only three LLM touchpoints in the entire backend** are the ones in §5.1/§5.2:
  chat (via `chain._make_llm`), personalize, and translate.

---

## 6. The Answer Chain (Generate step)

### 6.1 Prompt template

```python
template = """You are a specialized AI tutor for the 'Physical AI & Humanoid Robotics' textbook.

---
TEXTBOOK CONTEXT (Retrieved from database):
{context}

USER'S HIGHLIGHTED TEXT:
{selected_text}
---

INSTRUCTIONS:
1. Look at the 'TEXTBOOK CONTEXT' provided. Does it contain a direct explanation of '{selected_text}'?
2. If YES: Quote the textbook directly where possible. Use the exact wording and examples from the context.
3. If NO: Look at the 'USER'S HIGHLIGHTED TEXT' itself. If the definition is common knowledge in ROS 2
   (like Nodes), explain it clearly using your expertise, but explicitly start by saying:
   "While the retrieved excerpts focus on [Subject of Context, here is a general explanation of {selected_text}..."
4. Ensure you mention specific ROS 2 concepts like 'rclpy', 'executables', and 'graph' if they are in the context.
5. If the question is short or simple (like "What does this mean?"), give a brief 1-2 sentence answer.
   Only go into detail if the question asks for it.

Question: {question}
Answer:"""
prompt = ChatPromptTemplate.from_template(template)
```

**Prompt design logic — a grounded-but-honest tutor:**
- **Three-slot structure:** retrieved `{context}`, the user's highlighted `{selected_text}`, and the `{question}`.
- **Grounding preference (rule 2):** quote the textbook verbatim when the context covers the selection — this is the "answers come from the book" requirement (spec FR-004).
- **Graceful degradation (rule 3):** if retrieval misses, the model may answer from ROS 2 general knowledge **but must announce it** — it never silently passes off non-textbook knowledge as textbook content.
- **Length control (rule 5):** short questions get short answers.

### 6.2 LCEL composition

```python
rag_chain = (
    {
        "context": retriever | format_docs,      # question ─▶ retrieve ─▶ flatten to string
        "question": RunnablePassthrough(),        # question passes through untouched
        "selected_text": lambda x: (
            selected_text if selected_text and selected_text.strip()
            else "No specific text selected."     # closure over request's selection
        ),
    }
    | prompt                                      # dict ─▶ ChatPromptTemplate messages
    | llm                                         # messages ─▶ ChatOpenAI (streaming)
    | StrOutputParser()                           # AIMessage ─▶ str
)
return rag_chain
```

**Dataflow for one `rag_chain.invoke(question)`:**

```
question (str)
   │
   ├─▶ retriever ──embed_query(question)──▶ Qdrant search (k=5, ±chapter filter)
   │         └──▶ Document[] ──format_docs──▶ context (str)
   ├─▶ RunnablePassthrough ──▶ question (str)
   └─▶ lambda ──▶ selected_text (str, or default)
                     │
                     ▼
        ChatPromptTemplate.render(context, question, selected_text)
                     │
                     ▼
        ChatOpenAI (nemotron-3, temp 0.3, streaming)
                     │
                     ▼
        StrOutputParser ──▶ final answer (str)
```

Key LCEL detail: **the input to the chain is just the question string**; `selected_text` and `chapter_id` are baked in at construction time (closure / `search_kwargs`), because they are properties of the *request*, not of each intermediate step.

### 6.3 Standalone demo

```python
if __name__ == "__main__":
    rag_chain = create_rag_chain()
    print(rag_chain.invoke("What are the core concepts of ROS 2?"))

    rag_chain_selected = create_rag_chain(selected_text="ROS 2 Nodes, Topics, and Services")
    print(rag_chain_selected.invoke("Explain topics in ROS 2."))
```

---

## 7. API Layer — `backend/app.py`

### 7.1 Request schema

```python
class ChatRequest(BaseModel):
    message: str                      # the user's question (required)
    selected_text: Optional[str]      # highlighted passage, if any
    chapter_id: Optional[str]         # current doc's Docusaurus metadata.id
```

### 7.2 The chat route

```python
@app.post("/api/chat")
def chat_with_rag(request: ChatRequest):
    logging.info(f"Chapter ID for Search: {request.chapter_id or None}")

    try:
        rag_chain = create_rag_chain(
            selected_text=request.selected_text,
            chapter_id=request.chapter_id,
        )
    except Exception as e:
        logging.exception("chat setup failed")
        raise HTTPException(status_code=500, detail=f"chat setup failed: {e}") from e

    def stream_generator():
        try:
            yield from rag_chain.stream(request.message)
        except Exception:
            logging.exception("chat stream failed")
            yield "Error: the answer stream failed."

    return StreamingResponse(stream_generator(), media_type="text/plain")
```

**Two-phase error handling:**
1. **Build phase** — key check, Qdrant/embedder construction. Failures become a structured **HTTP 500 JSON** (`{"detail": ...}`) the frontend can read.
2. **Stream phase** — once headers are sent, HTTP status can no longer change, so mid-stream failures are reported **in-band as a plain-text message** appended to the stream.

**Streaming:** `rag_chain.stream(request.message)` yields answer fragments as the LLM produces them (enabled by `streaming=True` on `ChatOpenAI`), wrapped in a `StreamingResponse` with `media_type="text/plain"`. Note the route is a plain `def` (sync) — FastAPI runs it in a threadpool, which suits the synchronous LangChain/Qdrant stack.

### 7.3 Frontend consumption — `RAGChatbot.tsx`

```typescript
const body: { message: string; selected_text?: string; chapter_id?: string } = { message: input };
if (snapshot && snapshot.text.trim().length > 0) {
  body.selected_text = snapshot.text;
  if (snapshot.chapterId) {
    body.chapter_id = snapshot.chapterId;      // only sent together with a selection
  }
}

const response = await fetch('/api/chat', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(body),
});

// manual stream read → append to last bot message
const reader = response.body.getReader();
const decoder = new TextDecoder();
while (true) {
  const { value, done } = await reader.read();
  if (done) break;
  const chunk = decoder.decode(value);
  setChatHistory((prev) => {
    const lastMessage = prev[prev.length - 1];
    lastMessage.text += chunk;
    return [...prev];
  });
}
```

- Reads the `text/plain` stream with a `ReadableStream` reader and appends decoded chunks to the pending bot message — giving token-by-token rendering (with a spinner while `msg.text === ''`).
- Errors: non-OK responses are surfaced via `response.json().detail` (matches the build-phase 500 shape).

### 7.4 Selection provenance (where `chapter_id` comes from)

```
website/src/theme/DocItem/index.tsx
    useAskAiCapture(props.content.metadata.id)      ← Docusaurus doc ID = chapterId
        │
        ▼  (user selects text on the page)
website/src/features/ask-ai/useAskAiCapture.ts
    ai.select(selectedString, chapterId, anchor)
        │
        ▼
website/src/features/ask-ai/context.tsx
    state.selection = { text, chapterId }           ← atomic snapshot
        │
        ▼
RAGChatbot.handleSendMessage()  →  POST /api/chat { selected_text, chapter_id }
```

The same `metadata.id` semantics must hold on the ingestion side (`derive_chapter_id` strips `NN-` prefixes) — that's the shared contract that lets the filter find the right chunks.

---

## 8. End-to-End Request Walkthrough

```
1.  User highlights "What is a ROS 2 node?" in module-1 doc, clicks Ask AI,
    types "explain like I'm five".
2.  RAGChatbot POSTs /api/chat:
      { message: "explain like I'm five",
        selected_text: "What is a ROS 2 node?",
        chapter_id: "module-1-robotic-nervous-system/nodes" }
3.  app.chat_with_rag → create_rag_chain(selected_text=..., chapter_id=...):
      a. _make_llm(0.3)                 → fails fast if OPENROUTER_API_KEY missing
      b. _default_store()               → reuse client/embedder/store singletons
      c. _search_kwargs(chapter_id)     → {"k": 5, "filter": must chapter_id == ...}
      d. store.as_retriever(search_kwargs=...)
4.  rag_chain.stream("explain like I'm five"):
      a. embed_query via LocalEmbeddings (ONNX, offline) → 384-d unit vector
      b. Qdrant search: k=5, payload-filtered to the chapter (indexed lookup)
      c. format_docs → context string ("chunk1\n\nchunk2\n\n...")
      d. prompt renders: context + selected_text + question
      e. ChatOpenAI → OpenRouter → nemotron-3 (temp 0.3, streaming)
      f. StrOutputParser → str fragments
5.  stream_generator yields fragments → StreamingResponse (text/plain)
6.  RAGChatbot reader loop appends each chunk to the bot message bubble
7.  ReactMarkdown renders the completed answer; selection snapshot cleared
    (only if it wasn't changed mid-stream).
```

---

## 9. Configuration & Environment

### 9.1 Variables (see `backend/.env.example`; never commit `.env`)

```dotenv
OPENROUTER_API_KEY=sk-or-v1-...   # required: LLM chat, personalize, translate
DATABASE_URL=postgresql://...     # required by app import (profiles); unrelated to RAG
```

Notably **absent** vs. older docs: `QDRANT_HOST` / `QDRANT_API_KEY` — the implementation hardcodes `http://localhost:6333` and runs against a **local, unauthenticated Qdrant**. There are no Gemini or Qdrant-Cloud variables.

### 9.2 Dependency stack (`backend/requirements.txt`)

```text
qdrant-client==1.19.1              # vector DB client
langchain-qdrant==1.1.0            # QdrantVectorStore integration
langchain-core==1.6.3              # LCEL, prompts, retrievers
langchain-openai==1.6.2            # ChatOpenAI (used against OpenRouter)
langchain-community==0.4.2         # DirectoryLoader, TextLoader
langchain-text-splitters==1.1.2    # RecursiveCharacterTextSplitter
onnxruntime==1.30.0                # local embedding inference
tokenizers==0.23.2                 # vendored tokenizer.json
numpy==2.5.3                       # pooling / normalization math
fastapi, uvicorn                   # API + streaming
pytest                             # test suite
```

### 9.3 Runtime topology

| Concern | Value |
|---|---|
| Vector DB | Qdrant, **local** `localhost:6333`, collection `Physical_AI_Textbook_Local` |
| Embeddings | `all-MiniLM-L6-v2` ONNX, 384-dim, vendored in `backend/models/` |
| LLM | OpenRouter → `nvidia/nemotron-3-ultra-550b-a55b:free` |
| Corpus | `website/docs/**/*.mdx` (4 modules) |
| Chunking | 1000 chars / 200 overlap |
| Retrieval | top-5 similarity (cosine), optional `metadata.chapter_id` filter |
| Transport | POST `/api/chat` → `text/plain` chunked stream |

**Deployment caveat:** `vercel.json` builds the backend with `@vercel/python` and rewrites `/api/*` to it, but ingestion is a local CLI and `QDRANT_URL` points at `localhost` — a serverless Vercel instance has neither. The RAG chat path only works where a local Qdrant with an ingested index is reachable (dev machine / self-hosted backend).

### 9.4 Running the pipeline locally (from `README.md`)

```bash
# 1. Start Qdrant — vectors persist to ./qdrant_storage via the bind mount
docker run -p 6333:6333 -v $(pwd)/qdrant_storage:/qdrant/storage qdrant/qdrant
# (or restart an existing named container: docker start qdrant-local)
# verify: curl http://localhost:6333/collections

# 2. Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# create backend/.env: OPENROUTER_API_KEY + DATABASE_URL (see .env.example)
uvicorn app:app --reload                 # http://127.0.0.1:8000

# 3. Ingest the textbook (first run / after edits)
cd backend && python local_ingest.py     # incremental; add --full to rebuild

# 4. Frontend — proxies /api → :8000
cd website && yarn install && yarn start  # http://localhost:3000
```

Smoke-test the RAG stream directly:

```bash
curl -N -X POST http://127.0.0.1:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is a ROS 2 node?",
       "selected_text": "...",
       "chapter_id": "module-1-robotic-nervous-system/ros-nodes-topics-services"}'
```

(`-N` disables curl buffering so tokens appear as generated; `selected_text`/`chapter_id` are
optional — omit them for whole-book retrieval.)

### 9.5 CI — ingestion workflow is a placeholder

`.github/workflows/ingestion.yml` triggers on push to `main` and installs `backend/requirements.txt`,
but its run step is literally `echo "Running document ingestion..."` with a commented-out
`python backend/ingest.py` (a file that doesn't exist — the real script is `local_ingest.py`,
and it would need a Qdrant instance the runner doesn't have). **No CI actually re-ingests content**;
index updates are a manual, local operation.

---

## 10. Test Seams

The chain is deliberately dependency-injected so tests run with **no env vars, no network, no ONNX, no Qdrant**.

### 10.1 In-memory retriever — `backend/tests/in_memory.py`

```python
class InMemoryRetriever(BaseRetriever):
    """Test adapter: returns stored docs, optionally filtered by chapter_id."""
    docs: list[Document] = []
    chapter_id: str | None = None

    def _get_relevant_documents(self, query: str, *, run_manager):
        if self.chapter_id is None:
            return list(self.docs)
        return [doc for doc in self.docs
                if doc.metadata.get("chapter_id") == self.chapter_id]
```

A drop-in `BaseRetriever` that mimics the production filter contract (returns all docs, or only those matching `chapter_id`) without touching Qdrant.

### 10.2 Chain tests — `backend/tests/test_chain.py`

```python
os.environ["OPENROUTER_API_KEY"] = ""   # force BEFORE chain import — env-force rule

ECHO = RunnableLambda(lambda p: p.to_string())   # LLM stand-in: echoes prompt

def test_context_wiring_retrieved_doc_reaches_prompt():
    chain = create_rag_chain(retriever=make_retriever(), llm=ECHO)
    out = chain.invoke("what is torque?")
    assert "Torque is rotational force." in out

def test_search_kwargs_chapter_filter_structure():
    kwargs = _search_kwargs("ch-1")
    assert kwargs["k"] == 5
    condition = kwargs["filter"].must[0]
    assert condition.key == "metadata.chapter_id"
    assert condition.match.value == "ch-1"
    assert "filter" not in _search_kwargs(None)
    assert "filter" not in _search_kwargs("General Textbook")

def test_make_llm_raises_without_key():
    with pytest.raises(ValueError, match="OPENROUTER_API_KEY"):
        _make_llm()
```

What's covered:

| Test | Verifies |
|---|---|
| `test_context_wiring...` | Retrieved doc text actually flows into the prompt (LCEL wiring) |
| `test_search_kwargs...` | Filter shape: key, `k=5`, and filter *omitted* for `None`/`"General Textbook"` |
| `test_in_memory_adapter...` | The adapter reproduces chapter-filter semantics |
| `test_make_llm_raises_without_key` | Fail-fast on missing key |
| `test_full_seam_needs_no_env_or_network` | Full construction works offline with injections |
| `test_empty_selection_default_text` | Blank/None selection → `"No specific text selected."` |

The `ECHO` LLM is the trick that makes wiring testable: it returns the *rendered prompt* as the "answer", so assertions can check that retrieved context and default selection text made it into the prompt.

### 10.3 Route test — `backend/tests/test_chat_route.py`

```python
os.environ["DATABASE_URL"] = "sqlite:///:memory:"   # force BEFORE import app
os.environ["OPENROUTER_API_KEY"] = ""

def test_chat_build_failure_returns_500_json_detail():
    client = TestClient(app_module.app)
    resp = client.post("/api/chat", json={"message": "hello"})
    assert resp.status_code == 500
    assert "OPENROUTER_API_KEY" in resp.json()["detail"]
```

Locks in the **build-phase 500 with JSON `detail`** contract the frontend depends on (env vars are forced *before* module import — the "env-force rule").

### 10.4 Frontend stream tests — `website/src/components/__tests__/RAGChatbot.test.tsx`

Vitest + Testing Library, with `fetch` stubbed to a fake `ReadableStream` reader:

| Test | Verifies |
|---|---|
| `11. writes selection only through select()` | The selection chip renders from AskAi module state |
| `12. request body carries selected_text and chapter_id` | POST body shape contract: `{message, selected_text, chapter_id}` matches §7.1 |
| `13. fresh selection mid-stream survives completion` | Snapshot guard: a selection made *while streaming* is not cleared when the stream ends |
| `14. completed stream with no intervening selection clears` | The in-flight selection *is* cleared after a normal completion |

Companion suites live at `website/src/features/ask-ai/__tests__/` (context atomics,
`useAskAiCapture`, `AskAiButton`) — they lock down the selection provenance chain from §7.4.

### 10.5 Running the suites

```bash
cd backend  && .venv/bin/python -m pytest   # pytest.ini: pythonpath = . tests
cd website && yarn test                     # vitest (ask-ai + RAGChatbot)
```

---

## 11. Design Summary — Why It's Built This Way

1. **Offline-first embeddings** — vendored ONNX MiniLM means ingestion and query embedding never leave the machine; no embedding API cost, deterministic vectors, works air-gapped.
2. **Incremental ingestion** — MD5-per-file hashing makes the common case (edit one chapter → re-run ingest) re-embed only what changed.
3. **Chapter-scoped retrieval** — payload-indexed `metadata.chapter_id` filter keeps answers anchored to the page the reader is on, while `"General Textbook"`/absent id opens the full corpus.
4. **Honest grounding prompt** — quote the book when it answers; when it doesn't, say so explicitly rather than hallucinating textbook authority.
5. **Streaming with two-phase errors** — structured 500s before headers, in-band text after; token-by-token UX via `rag_chain.stream()`.
6. **Constructor injection seams** — `retriever`/`llm` params on `create_rag_chain` let the entire pipeline be unit-tested with an in-memory retriever and an echo LLM, no infrastructure required.
7. **Fail fast** — API-key validation runs before any ONNX/Qdrant work; embedding-dimension mismatches abort ingestion loudly instead of corrupting the index.

---

## 12. Related Documents (and what to trust)

| Document | Status | What it is |
|---|---|---|
| `README.md` | **Current** | Authoritative quickstart (§9.4 above), architecture diagram, and chapter-id contract |
| `CHANGELOG.md` | **Current** | History of the RAG stack: Gemini/Qdrant-Cloud → local ONNX/Qdrant migration; `local_retrieve.py` fold; lazy-singleton work |
| `specs/001-physical-ai-book/contracts/api-contracts.yaml` | Partially current | Formal chat contract; predates streaming (`text/plain` chunked response not fully reflected) |
| `answer-path-module.md` | Design only | **Approved, unimplemented** refactor to collapse the answer path. References `local_retrieve.py` (deleted, `.pyc` only) and claims "no backend tests" (stale — tests exist now). Treat as roadmap, not description |
| `rag-instruct.md` | **Legacy / mismatched** | Early runbook for a *different* stack: `BAAI/bge-small-en-v1.5` + Docker Qdrant + standalone `ingest.py`. None of that matches the shipped code (MiniLM ONNX + `local_ingest.py`) — do not follow it |
| `difference.md`, `architecture-review-*.html` | Historical | Spec-vs-impl audit and architecture review that motivated the seam/singletons design |
| `AGENTS.md`, `.vercelignore` | **Stale on RAG layout** | Still mention `backend/rag/`, `gemini_retrieve.py` — removed; see the doc-drift warning at the top |

---

## 13. File Map

| File | Role |
|---|---|
| `backend/local_ingest.py` | CLI ingestion: load → split → enrich → incremental embed/upsert into Qdrant |
| `backend/local_embeddings.py` | `LocalEmbeddings` (ONNX MiniLM-L6-v2, mean-pool + L2) |
| `backend/chain.py` | LLM factory, Qdrant singletons, `_search_kwargs`, prompt, `create_rag_chain` (LCEL) |
| `backend/app.py` | FastAPI: `POST /api/chat` (streaming), plus personalize/translate LLM routes |
| `backend/models/all-MiniLM-L6-v2/` | Vendored tokenizer + ONNX model |
| `backend/tests/in_memory.py` | `InMemoryRetriever` test adapter |
| `backend/tests/test_chain.py` | Chain wiring, filter-shape, key-required, default-selection tests |
| `backend/tests/test_chat_route.py` | 500-on-build-failure contract test |
| `website/src/theme/DocItem/index.tsx` | Supplies `metadata.id` → `useAskAiCapture` (chapterId source) |
| `website/src/features/ask-ai/` | Selection state: `{ text, chapterId, anchor }` |
| `website/src/components/RAGChatbot.tsx` | Chat UI, `/api/chat` POST + stream reader |
| `website/src/components/__tests__/RAGChatbot.test.tsx` | Vitest: request-body contract, selection snapshot guard |
| `backend/agents/*.py` | Placeholder agent routers — **no LLM, not registered** (§5.3) |
| `backend/pytest.ini` | `pythonpath = . tests`, `testpaths = tests` |
| `qdrant_storage/` | Docker bind-mount volume holding Qdrant's persisted points |
| `.github/workflows/ingestion.yml` | Placeholder CI job — echoes, never ingests (§9.5) |
| `specs/001-physical-ai-book/contracts/api-contracts.yaml` | API contract for the chat endpoint |
| `README.md` | Quickstart + architecture (current); `rag-instruct.md` / `answer-path-module.md` — see §12 |
