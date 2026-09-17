"""Unit tests for SourceDocument SQLAlchemy model and database roundtrip."""
import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import DateTime, Integer, String, Text, select
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.models import Base, SourceDocument
from app.models.base import new_uuid


def test_source_document_registered_in_metadata():
    """Verify SourceDocument table is registered in Base.metadata."""
    assert SourceDocument.__tablename__ == "source_document"
    assert "source_document" in Base.metadata.tables


def test_source_document_column_specifications():
    """Verify column types, nullability, and indexes on SourceDocument."""
    table = SourceDocument.__table__

    # id column
    id_col = table.c.id
    assert isinstance(id_col.type, UUID)
    assert id_col.primary_key is True
    assert callable(id_col.default.arg)
    assert isinstance(id_col.default.arg(None), uuid.UUID)

    # entity_id column
    entity_col = table.c.entity_id
    assert isinstance(entity_col.type, UUID)
    assert entity_col.nullable is False
    assert entity_col.index is True

    # filename column
    filename_col = table.c.filename
    assert isinstance(filename_col.type, String)
    assert filename_col.type.length == 255
    assert filename_col.nullable is False

    # file_type column
    file_type_col = table.c.file_type
    assert isinstance(file_type_col.type, String)
    assert file_type_col.type.length == 32
    assert file_type_col.nullable is False

    # file_size_bytes column
    size_col = table.c.file_size_bytes
    assert isinstance(size_col.type, Integer)
    assert size_col.nullable is False

    # file_hash_sha256 column
    hash_col = table.c.file_hash_sha256
    assert isinstance(hash_col.type, String)
    assert hash_col.type.length == 64
    assert hash_col.nullable is False
    assert hash_col.index is True

    # storage_path column
    path_col = table.c.storage_path
    assert isinstance(path_col.type, String)
    assert path_col.type.length == 512
    assert path_col.nullable is False

    # status column
    status_col = table.c.status
    assert isinstance(status_col.type, String)
    assert status_col.type.length == 32
    assert status_col.nullable is False
    assert status_col.index is True
    assert status_col.default.arg == "pending"

    # error_message column
    error_col = table.c.error_message
    assert isinstance(error_col.type, Text)
    assert error_col.nullable is True

    # metadata_json column
    meta_col = table.c.metadata_json
    assert isinstance(meta_col.type, JSONB)
    assert meta_col.nullable is False
    assert callable(meta_col.default.arg)
    assert meta_col.default.arg(None) == {}

    # created_at column
    created_col = table.c.created_at
    assert isinstance(created_col.type, DateTime)
    assert created_col.type.timezone is True
    assert created_col.nullable is False
    assert created_col.server_default is not None

    # processed_at column
    processed_col = table.c.processed_at
    assert isinstance(processed_col.type, DateTime)
    assert processed_col.type.timezone is True
    assert processed_col.nullable is True


def test_source_document_instantiation():
    """Verify model instantiation with explicit attributes."""
    doc_id = uuid.uuid4()
    entity_id = uuid.uuid4()
    doc = SourceDocument(
        id=doc_id,
        entity_id=entity_id,
        filename="test.csv",
        file_type="csv",
        file_size_bytes=100,
        file_hash_sha256="abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
        storage_path="raw/documents/test.csv",
        status="pending",
        metadata_json={"custom": "field"},
    )
    assert doc.id == doc_id
    assert doc.entity_id == entity_id
    assert doc.filename == "test.csv"
    assert doc.file_type == "csv"
    assert doc.file_size_bytes == 100
    assert doc.status == "pending"
    assert doc.error_message is None
    assert doc.metadata_json == {"custom": "field"}
    assert doc.processed_at is None


@pytest.mark.asyncio
async def test_source_document_insert_with_defaults(db_session):
    """Verify column defaults (UUID, status, metadata_json) are populated on insert."""
    entity_id = new_uuid()
    sha256_hash = "c" * 64
    storage_path = f"raw/{entity_id}/2026/09/defaults.csv"

    doc = SourceDocument(
        entity_id=entity_id,
        filename="defaults.csv",
        file_type="csv",
        file_size_bytes=512,
        file_hash_sha256=sha256_hash,
        storage_path=storage_path,
    )
    db_session.add(doc)
    await db_session.flush()

    assert doc.id is not None
    assert isinstance(doc.id, uuid.UUID)
    assert doc.status == "pending"
    assert doc.metadata_json == {}
    assert doc.created_at is not None
    assert doc.processed_at is None
    assert doc.error_message is None


@pytest.mark.asyncio
async def test_source_document_insert_and_readback(db_session):
    """Verify insert and readback of SourceDocument using db_session."""
    doc_id = new_uuid()
    entity_id = new_uuid()
    sha256_hash = "a" * 64
    storage_path = f"raw/{entity_id}/2026/09/invoice.pdf"

    doc = SourceDocument(
        id=doc_id,
        entity_id=entity_id,
        filename="invoice.pdf",
        file_type="pdf",
        file_size_bytes=54321,
        file_hash_sha256=sha256_hash,
        storage_path=storage_path,
        status="pending",
        error_message=None,
        metadata_json={"page_count": 3, "ocr_used": False},
    )
    db_session.add(doc)
    await db_session.flush()

    stmt = select(SourceDocument).where(SourceDocument.id == doc_id)
    result = await db_session.execute(stmt)
    persisted = result.scalar_one()

    assert persisted.id == doc_id
    assert persisted.entity_id == entity_id
    assert persisted.filename == "invoice.pdf"
    assert persisted.file_type == "pdf"
    assert persisted.file_size_bytes == 54321
    assert persisted.file_hash_sha256 == sha256_hash
    assert persisted.storage_path == storage_path
    assert persisted.status == "pending"
    assert persisted.error_message is None
    assert persisted.metadata_json == {"page_count": 3, "ocr_used": False}
    assert persisted.created_at is not None
    assert persisted.processed_at is None


@pytest.mark.asyncio
async def test_source_document_update_status_and_error(db_session):
    """Verify updating status, processed_at, and error_message."""
    doc_id = new_uuid()
    entity_id = new_uuid()

    doc = SourceDocument(
        id=doc_id,
        entity_id=entity_id,
        filename="corrupted.xlsx",
        file_type="xlsx",
        file_size_bytes=1024,
        file_hash_sha256="b" * 64,
        storage_path=f"raw/{entity_id}/corrupted.xlsx",
        status="processing",
    )
    db_session.add(doc)
    await db_session.flush()

    now = datetime.now(UTC)
    doc.status = "failed"
    doc.error_message = "Corrupted zip archive"
    doc.processed_at = now
    await db_session.flush()

    stmt = select(SourceDocument).where(SourceDocument.id == doc_id)
    result = await db_session.execute(stmt)
    updated = result.scalar_one()

    assert updated.status == "failed"
    assert updated.error_message == "Corrupted zip archive"
    assert updated.processed_at is not None
