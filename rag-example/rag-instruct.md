Docusaurus → Qdrant RAG Setup (Agent Runbook)
Goal: Ingest a small Docusaurus docs site (5–10 pages) into a local Qdrant vector database using BAAI/bge-small-en-v1.5, then support semantic retrieval over it.

Follow these steps in order. Each step includes what to run and how to verify it worked before moving on.

Prerequisites
Docker installed and running locally
Python 3.9+ installed
Path to the Docusaurus project (the folder containing docs/ with .md/.mdx files)
Step 1 — Start Qdrant in Docker
docker pull qdrant/qdrant

docker run -d \
  --name qdrant-rag \
  -p 6333:6333 \
  -p 6334:6334 \
  -v $(pwd)/qdrant_storage:/qdrant/storage \
  qdrant/qdrant
-v $(pwd)/qdrant_storage:/qdrant/storage persists data to disk so it survives container restarts.
Port 6333 is the REST/HTTP API, 6334 is gRPC.
Verify: open http://localhost:6333/dashboard in a browser, or run:

curl http://localhost:6333/collections
You should get a JSON response (likely {"result":{"collections":[]},...} on first run).

Step 2 — Set up the Python environment
mkdir docusaurus-rag && cd docusaurus-rag
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

pip install sentence-transformers qdrant-client markdown python-frontmatter
python-frontmatter strips YAML frontmatter from .md/.mdx files cleanly.
markdown helps strip markdown syntax down to plain text if needed.
Step 3 — Locate and parse the Docusaurus docs
Create ingest.py. Point DOCS_PATH at the actual docs/ folder of the Docusaurus project.

import os
import glob
import frontmatter

DOCS_PATH = "/path/to/your-docusaurus-site/docs"  # <-- update this

def load_docs(docs_path):
    files = glob.glob(os.path.join(docs_path, "**/*.md"), recursive=True) \
          + glob.glob(os.path.join(docs_path, "**/*.mdx"), recursive=True)
    documents = []
    for filepath in files:
        with open(filepath, "r", encoding="utf-8") as f:
            post = frontmatter.load(f)
            documents.append({
                "path": filepath,
                "title": post.get("title", os.path.basename(filepath)),
                "content": post.content
            })
    return documents

if __name__ == "__main__":
    docs = load_docs(DOCS_PATH)
    print(f"Loaded {len(docs)} documents")
    for d in docs:
        print(" -", d["title"], f"({len(d['content'])} chars)")
Verify: run python ingest.py — it should list every doc page with a non-zero character count. If it prints 0 documents, double check DOCS_PATH.

Step 4 — Chunk by heading
At this scale, chunk each page by markdown headings (##) rather than fixed character counts, so each chunk stays semantically coherent.

Add this to ingest.py:

import re

def chunk_by_heading(text, min_chunk_len=50):
    # Split on level-2 headings, keep the heading with its section
    sections = re.split(r"\n(?=## )", text)
    chunks = [s.strip() for s in sections if len(s.strip()) >= min_chunk_len]
    return chunks if chunks else [text.strip()]

def build_chunks(documents):
    all_chunks = []
    for doc in documents:
        for i, chunk in enumerate(chunk_by_heading(doc["content"])):
            all_chunks.append({
                "id": f'{doc["path"]}::{i}',
                "text": chunk,
                "source": doc["path"],
                "title": doc["title"]
            })
    return all_chunks
Verify: print len(build_chunks(docs)) — for 5–10 pages expect roughly 15–60 chunks depending on how many headings each page has.

Step 5 — Load the embedding model
from sentence_transformers import SentenceTransformer

EMBED_MODEL = SentenceTransformer("BAAI/bge-small-en-v1.5")
VECTOR_SIZE = 384
First run downloads ~130MB of weights automatically and caches them. No GPU needed.

Step 6 — Create the Qdrant collection
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance

client = QdrantClient(host="localhost", port=6333)

COLLECTION_NAME = "docusaurus_docs"

client.recreate_collection(
    collection_name=COLLECTION_NAME,
    vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
)
recreate_collection wipes and recreates it — fine while iterating during practice; switch to create_collection once your pipeline is stable so re-runs don't erase existing data.

Step 7 — Embed and upsert into Qdrant
from qdrant_client.models import PointStruct
import uuid

def ingest(chunks):
    texts = [c["text"] for c in chunks]
    vectors = EMBED_MODEL.encode(texts, normalize_embeddings=True)

    points = [
        PointStruct(
            id=str(uuid.uuid4()),
            vector=vectors[i].tolist(),
            payload={
                "text": chunks[i]["text"],
                "source": chunks[i]["source"],
                "title": chunks[i]["title"]
            }
        )
        for i in range(len(chunks))
    ]

    client.upsert(collection_name=COLLECTION_NAME, points=points)
    print(f"Upserted {len(points)} chunks into '{COLLECTION_NAME}'")

if __name__ == "__main__":
    docs = load_docs(DOCS_PATH)
    chunks = build_chunks(docs)
    ingest(chunks)
Run it:

python ingest.py
Verify:

curl http://localhost:6333/collections/docusaurus_docs
points_count should match the number of chunks you ingested.

Step 8 — Retrieval script
Create retrieve.py:

from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient

EMBED_MODEL = SentenceTransformer("BAAI/bge-small-en-v1.5")
client = QdrantClient(host="localhost", port=6333)
COLLECTION_NAME = "docusaurus_docs"

def search(query, top_k=5):
    # bge models need this instruction prefix on QUERIES only, not on ingested docs
    prefixed_query = "Represent this sentence for searching relevant passages: " + query
    query_vector = EMBED_MODEL.encode(prefixed_query, normalize_embeddings=True).tolist()

    results = client.search(
        collection_name=COLLECTION_NAME,
        query_vector=query_vector,
        limit=top_k
    )

    for r in results:
        print(f"\nScore: {r.score:.4f}")
        print(f"Source: {r.payload['source']}")
        print(f"Title: {r.payload['title']}")
        print(f"Text: {r.payload['text'][:300]}...")

if __name__ == "__main__":
    query = input("Ask something about your docs: ")
    search(query)
Run it:

python retrieve.py
Verify: ask a question you know the answer to from your docs (e.g. "how do I configure the sidebar?") and confirm the top result's source and text are actually relevant. If results look off, check the query prefix is applied and that ingestion actually completed with the right number of points.

Quick troubleshooting
Symptom	Likely cause
Loaded 0 documents	Wrong DOCS_PATH, or files are .md under a different folder (e.g. versioned_docs/)
Connection refused on port 6333	Qdrant container isn't running — check docker ps
Irrelevant search results	Missing the query prefix, or chunks are too large/small — try adjusting min_chunk_len
points_count: 0 after ingest	recreate_collection ran after ingestion, or ingest() wasn't called
Next steps once this works
Swap BAAI/bge-small-en-v1.5 for bge-base-en-v1.5 (768 dims) if you want to compare quality — remember to update VECTOR_SIZE and recreate the collection.
Add a reranker on top of the top-k results for better precision.
Wire retrieve.py's output into an LLM call (e.g. Claude via the Anthropic API) to generate a final answer grounded in the retrieved chunks — that's the "generation" half of RAG.