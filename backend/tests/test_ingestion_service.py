"""Tests for IngestionService."""
import io
import uuid
from datetime import date
from decimal import Decimal

import openpyxl
import pytest
from sqlalchemy import select

from app.models.activity_data import ActivityData
from app.models.audit_log import AuditLogEntry
from app.services.ingestion_service import IngestionService, UnsupportedFileTypeError
from app.services.storage_service import StorageService


class MockStorageService(StorageService):
    """In-memory storage service mock for test isolation."""

    def __init__(self) -> None:
        self.store: dict[str, bytes] = {}

    def upload_bytes(
        self,
        content: bytes,
        storage_path: str,
        content_type: str = "application/octet-stream",
    ) -> str:
        self.store[storage_path] = content
        return storage_path

    def download_bytes(self, storage_path: str) -> bytes:
        if storage_path not in self.store:
            raise FileNotFoundError(f"Key not found: {storage_path}")
        return self.store[storage_path]

    def delete_file(self, storage_path: str) -> None:
        self.store.pop(storage_path, None)


@pytest.fixture
def mock_storage() -> MockStorageService:
    return MockStorageService()


@pytest.fixture
def ingestion_service(mock_storage: MockStorageService) -> IngestionService:
    return IngestionService(storage_service=mock_storage)


@pytest.mark.asyncio
async def test_ingest_document_stores_file_and_creates_record(
    db_session, ingestion_service: IngestionService, mock_storage: MockStorageService
) -> None:
    entity_id = uuid.uuid4()
    content = b"header1,header2\nval1,val2\n"
    filename = "test_export.csv"

    source_doc = await ingestion_service.ingest_document(
        session=db_session,
        entity_id=entity_id,
        filename=filename,
        content=content,
        column_mapping={"colA": "colB"},
    )

    assert source_doc.id is not None
    assert source_doc.entity_id == entity_id
    assert source_doc.filename == filename
    assert source_doc.file_type == "csv"
    assert source_doc.file_size_bytes == len(content)
    assert source_doc.status == "pending"
    assert source_doc.metadata_json.get("column_mapping") == {"colA": "colB"}
    assert source_doc.storage_path in mock_storage.store


@pytest.mark.asyncio
async def test_process_csv_document_creates_activity_data_and_audit_log(
    db_session, ingestion_service: IngestionService
) -> None:
    entity_id = uuid.uuid4()
    csv_content = (
        b"Date,Supplier,Activity,Quantity,Unit,State\n"
        b"2025-01-15,Acme Energy,electricity_purchase,1500.50,kWh,CA\n"
        b"2025-02-15,Acme Energy,electricity_purchase,1750.00,kWh,CA\n"
    )

    source_doc, activities = await ingestion_service.ingest_and_process_document(
        session=db_session,
        entity_id=entity_id,
        filename="electric_erp.csv",
        content=csv_content,
    )

    assert source_doc.status == "completed"
    assert source_doc.processed_at is not None
    assert len(activities) == 2

    # Verify ActivityData rows in DB
    result = await db_session.scalars(
        select(ActivityData).where(ActivityData.source_document_id == source_doc.id)
    )
    rows = result.all()
    assert len(rows) == 2

    for row in rows:
        assert row.status == "pending_review"
        assert row.entity_id == entity_id
        assert row.supplier_ref.startswith("TOKEN_SUPP_")
        assert isinstance(row.quantity, Decimal)
        assert isinstance(row.period_start, date)
        assert row.unit == "kWh"

    # Verify AuditLogEntry
    audit_res = await db_session.scalars(
        select(AuditLogEntry).where(AuditLogEntry.entity_id == entity_id)
    )
    audit_entries = audit_res.all()
    assert len(audit_entries) >= 1
    ingest_audit = next(a for a in audit_entries if a.action == "ingest_and_parse")
    assert ingest_audit.detail["rows_created"] == 2
    assert ingest_audit.detail["source_document_id"] == str(source_doc.id)


@pytest.mark.asyncio
async def test_process_xlsx_document(
    db_session, ingestion_service: IngestionService
) -> None:
    entity_id = uuid.uuid4()
    wb = openpyxl.Workbook()
    ws = wb.active
    assert ws is not None
    ws.append(["Date", "Supplier", "Activity", "Quantity", "Unit", "State"])
    ws.append(["2025-03-01", "Fleet Fuel Co", "freight_road", 450.75, "gallons", "TX"])
    bio = io.BytesIO()
    wb.save(bio)
    xlsx_bytes = bio.getvalue()
    wb.close()

    source_doc, activities = await ingestion_service.ingest_and_process_document(
        session=db_session,
        entity_id=entity_id,
        filename="fleet_fuel.xlsx",
        content=xlsx_bytes,
    )

    assert source_doc.status == "completed"
    assert len(activities) == 1
    assert activities[0].quantity == Decimal("450.75")
    assert activities[0].unit == "gallons"
    assert activities[0].supplier_ref.startswith("TOKEN_SUPP_")


@pytest.mark.asyncio
async def test_unsupported_file_type_raises_error(
    db_session, ingestion_service: IngestionService
) -> None:
    entity_id = uuid.uuid4()
    with pytest.raises(UnsupportedFileTypeError):
        await ingestion_service.ingest_document(
            session=db_session,
            entity_id=entity_id,
            filename="document.docx",
            content=b"word document",
        )


@pytest.mark.asyncio
async def test_process_document_failure_marks_status_failed(
    db_session, ingestion_service: IngestionService
) -> None:
    entity_id = uuid.uuid4()
    invalid_content = b"corrupted random data"

    source_doc = await ingestion_service.ingest_document(
        session=db_session,
        entity_id=entity_id,
        filename="corrupt.xlsx",
        content=invalid_content,
        file_type="xlsx",
    )

    with pytest.raises(Exception):
        await ingestion_service.process_document(
            session=db_session, source_document_id=source_doc.id
        )

    # Re-fetch document to verify status updated to failed
    await db_session.refresh(source_doc)
    assert source_doc.status == "failed"
    assert source_doc.error_message is not None
    assert source_doc.processed_at is not None
