import zipfile
from pathlib import Path

import pytest

from src.rag.ingest import ALLOWED_EXTENSIONS, DocumentIngestor, extract_text
from tests.rag.in_memory import FakeEmbedder

# Valid minimal PDF with correct xref offsets (verified against installed pypdf 6.19.0)
MINI_PDF = (
    b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
    b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
    b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
    b"/Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n"
    b"4 0 obj\n<< /Length 46 >>\nstream\nBT /F1 24 Tf 72 720 Td (Hello RAG world) Tj ET\n"
    b"endstream\nendobj\n5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\n"
    b"endobj\nxref\n0 6\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n"
    b"0000000115 00000 n \n0000000241 00000 n \n0000000337 00000 n \n"
    b"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n407\n%%EOF\n"
)


def make_docx(text: str) -> bytes:
    document_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body><w:p><w:r><w:t>{text}</w:t></w:r></w:p></w:body></w:document>"
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/word/document.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
        "</Types>"
    )
    rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
        "</Relationships>"
    )
    buffer = __import__("io").BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        zf.writestr("[Content_Types].xml", content_types)
        zf.writestr("_rels/.rels", rels)
        zf.writestr("word/document.xml", document_xml)
    return buffer.getvalue()


@pytest.fixture
def ingestor(qdrant_client, tmp_path):
    return DocumentIngestor(
        client=qdrant_client, embedder=FakeEmbedder(), uploads_dir=tmp_path / "uploads"
    )


def _count(client) -> int:
    from src.rag.store import collection_name

    return client.count(collection_name()).count


def test_txt_upload_indexes_row_and_points(ingestor, qdrant_client, db_session):
    result = ingestor.ingest_upload(
        db_session, "1", [("notes.txt", b"alpha beta gamma")]
    )
    assert (result.indexed, result.failed) == (1, 0)
    assert _count(qdrant_client) >= 1
    from sqlmodel import select

    from src.models.rag import Document

    row = db_session.exec(select(Document).where(Document.user_id == "1")).one()
    assert row.status == "indexed"
    assert row.hash and len(row.hash) == 64
    assert row.indexed_at is not None


def test_duplicate_upload_skips(ingestor, qdrant_client, db_session):
    payload = b"same content every time"
    ingestor.ingest_upload(db_session, "1", [("a.txt", payload)])
    before = _count(qdrant_client)
    result = ingestor.ingest_upload(db_session, "1", [("a.txt", payload)])
    assert result.skipped == 1 and result.indexed == 0
    assert _count(qdrant_client) == before


def test_changed_content_reindexes(ingestor, db_session):
    ingestor.ingest_upload(db_session, "1", [("a.txt", b"version one")])
    result = ingestor.ingest_upload(
        db_session, "1", [("a.txt", b"version two changed")]
    )
    assert result.indexed == 1


def test_unsupported_extension_fails(ingestor, db_session):
    result = ingestor.ingest_upload(db_session, "1", [("malware.exe", b"MZ")])
    assert result.failed == 1 and "unsupported extension" in result.errors[0]
    assert result.indexed == 0


def test_pdf_text_extracted(ingestor, db_session, qdrant_client):
    result = ingestor.ingest_upload(db_session, "1", [("doc.pdf", MINI_PDF)])
    assert result.indexed == 1
    from src.rag.store import collection_name

    points, _ = qdrant_client.scroll(collection_name(), limit=10, with_payload=True)
    assert any("Hello RAG world" in p.payload["page_content"] for p in points)


def test_docx_text_extracted(ingestor, db_session):
    result = ingestor.ingest_upload(
        db_session, "1", [("brief.docx", make_docx("quarterly plan overview"))]
    )
    assert result.indexed == 1
    assert not [e for e in result.errors]


def test_empty_text_marks_failed(ingestor, db_session):
    result = ingestor.ingest_upload(db_session, "1", [("empty.txt", b"")])
    assert result.failed == 1
    assert "no extractable text" in result.errors[0]


def test_reset_user_only_clears_own_data(ingestor, qdrant_client, db_session):
    ingestor.ingest_upload(db_session, "1", [("one.txt", b"users one document")])
    ingestor.ingest_upload(db_session, "2", [("two.txt", b"users two document")])
    before = _count(qdrant_client)
    deleted = ingestor.reset_user(db_session, "1")
    assert deleted >= 1
    assert _count(qdrant_client) == before - deleted

    from qdrant_client import models

    from src.rag.store import collection_name

    points, _ = qdrant_client.scroll(
        collection_name(),
        scroll_filter=models.Filter(
            must=[
                models.FieldCondition(
                    key="metadata.user_id", match=models.MatchValue(value="2")
                )
            ]
        ),
        limit=10,
    )
    assert len(points) >= 1
    from sqlmodel import select

    from src.models.rag import Document

    remaining = db_session.exec(select(Document)).all()
    assert {r.user_id for r in remaining} == {"2"}


def test_allowed_extensions_contract():
    assert ALLOWED_EXTENSIONS == {".pdf", ".txt", ".md", ".markdown", ".docx"}
    assert extract_text("a.txt", "héllo".encode(), Path("a.txt")) == "héllo"
