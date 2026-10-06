"""Document ingestion: extract -> split -> embed -> upsert, owning Document-row lifecycle."""

from __future__ import annotations

import hashlib
import mimetypes
import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

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

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP
    )
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
                    db,
                    user_id=user_id,
                    document_id=document_id,
                    filename=filename,
                    original_filename=filename,
                    file_path=file_path,
                    content=content,
                    result=result,
                )
            except (
                Exception
            ) as exc:  # noqa: BLE001 - one bad file must not sink the batch
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

    def ingest_paths(
        self, db: Session, user_id: str, paths: Sequence[str]
    ) -> IngestResult:
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
                    db,
                    user_id=user_id,
                    document_id=document_id,
                    filename=path.name,
                    original_filename=path.name,
                    file_path=path,
                    content=content,
                    result=result,
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
                    must=[
                        models.FieldCondition(
                            key="metadata.user_id",
                            match=models.MatchValue(value=user_id),
                        )
                    ]
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
                            must=[
                                models.FieldCondition(
                                    key="metadata.user_id",
                                    match=models.MatchValue(value=user_id),
                                )
                            ]
                        )
                    ),
                )
                deleted = len(points)

        rows = db.exec(select(Document).where(Document.user_id == user_id)).all()
        for row in rows:
            db.delete(row)
        db.commit()
        return deleted

    # -- internals -----------------------------------------------------
    def _index_one(
        self,
        db,
        *,
        user_id,
        document_id,
        filename,
        original_filename,
        file_path,
        content,
        result,
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
            row = Document(
                id=document_id, user_id=user_id, original_filename=original_filename
            )

        row.filename = Path(file_path).name
        row.file_path = str(file_path)
        row.file_size = len(content)
        row.mime_type = (
            mimetypes.guess_type(original_filename)[0] or "application/octet-stream"
        )
        row.hash = new_hash
        row.status = "processing"
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
                        must=[
                            models.FieldCondition(
                                key="metadata.document_id",
                                match=models.MatchValue(value=document_id),
                            )
                        ]
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
                docs[start : start + UPLOAD_BATCH],
                ids=ids[start : start + UPLOAD_BATCH],
            )

        row.status = "indexed"
        row.indexed_at = datetime.now(timezone.utc)
        row.document_metadata = {
            "original_filename": original_filename,
            "chunks": len(chunks),
        }
        db.add(row)
        db.commit()
        result.indexed += 1
