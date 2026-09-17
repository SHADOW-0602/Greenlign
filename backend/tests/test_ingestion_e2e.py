"""End-to-End integration tests for Phase 1 Ingestion Pipeline."""

import io
import json
import uuid
from pathlib import Path
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.database import get_db
from app.main import app
from app.models.activity_data import ActivityData
from app.models.audit_log import AuditLogEntry
from app.services.storage_service import StorageService

FIXTURES_DIR = Path(__file__).parent / "fixtures"


class MockE2EStorage(StorageService):
    """In-memory storage for E2E integration test isolation."""

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
        return self.store[storage_path]

    def delete_file(self, storage_path: str) -> None:
        self.store.pop(storage_path, None)


@pytest.fixture
def e2e_storage():
    return MockE2EStorage()


@pytest.fixture(autouse=True)
def override_e2e_deps(db_session, e2e_storage):
    app.dependency_overrides[get_db] = lambda: db_session
    with patch("app.services.ingestion_service.StorageService", return_value=e2e_storage):
        yield
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_e2e_utility_bill_pdf_ingestion(db_session):
    """Criterion 1: Utility PDF produces ActivityData rows with status='pending_review'."""
    pdf_path = FIXTURES_DIR / "sample_utility_bill.pdf"
    assert pdf_path.exists(), f"Fixture missing: {pdf_path}"
    pdf_bytes = pdf_path.read_bytes()

    entity_id = uuid.uuid4()
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/ingestion/upload",
            data={"entity_id": str(entity_id), "async_process": "false"},
            files={"file": ("utility_bill_jan2025.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        )

    assert response.status_code == 200
    res_data = response.json()
    assert res_data["activities_count"] >= 1
    doc_id = uuid.UUID(res_data["document"]["id"])

    # Verify ActivityData rows created
    stmt = select(ActivityData).where(ActivityData.source_document_id == doc_id)
    result = await db_session.scalars(stmt)
    activities = result.all()
    assert len(activities) >= 1

    for act in activities:
        assert act.status == "pending_review"
        assert act.entity_id == entity_id
        assert act.supplier_ref.startswith("TOKEN_SUPP_")
        assert "Pacific Gas" not in act.supplier_ref
        assert "PG&E" not in act.supplier_ref
        assert act.activity_type in {
            "electricity_purchase",
            "natural_gas_combustion",
            "freight_road",
        }
        assert act.quantity > 0


@pytest.mark.asyncio
async def test_e2e_erp_csv_ingestion_with_column_mapping(db_session):
    """Criteria 2 & 3: Sample ERP CSV produces mapped rows, no raw PII in logs."""
    csv_path = FIXTURES_DIR / "sample_erp_export.csv"
    assert csv_path.exists(), f"Fixture missing: {csv_path}"
    csv_bytes = csv_path.read_bytes()

    entity_id = uuid.uuid4()
    transport = ASGITransport(app=app)

    mapping = {
        "period_start": "Transaction Date",
        "supplier_ref": "Vendor Name",
        "activity_type": "Activity Category",
        "quantity": "Consumption",
        "unit": "UOM",
        "geography": "Facility Location",
        "raw_line_ref": "Invoice Number",
    }

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/ingestion/upload",
            data={
                "entity_id": str(entity_id),
                "column_mapping": json.dumps(mapping),
                "async_process": "false",
            },
            files={"file": ("erp_export_q1.csv", io.BytesIO(csv_bytes), "text/csv")},
        )

    assert response.status_code == 200
    res_data = response.json()
    assert res_data["activities_count"] == 3
    doc_id = uuid.UUID(res_data["document"]["id"])

    # Verify ActivityData rows
    stmt = (
        select(ActivityData)
        .where(ActivityData.source_document_id == doc_id)
        .order_by(ActivityData.created_at)
    )
    result = await db_session.scalars(stmt)
    activities = result.all()
    assert len(activities) == 3

    # Check row 1: Electricity
    act_elec = next(a for a in activities if a.activity_type == "electricity_purchase")
    assert act_elec.quantity == 14250.00
    assert act_elec.unit == "kWh"
    assert act_elec.geography == "NY"
    assert act_elec.raw_line_ref == "INV-88901"
    assert act_elec.supplier_ref.startswith("TOKEN_SUPP_")

    # Check row 2: Natural Gas
    act_gas = next(a for a in activities if a.activity_type == "natural_gas_combustion")
    assert act_gas.quantity == 820.50
    assert act_gas.unit == "therms"
    assert act_gas.geography == "MA"
    assert act_gas.raw_line_ref == "INV-88902"
    assert act_gas.supplier_ref.startswith("TOKEN_SUPP_")

    # Check row 3: Freight
    act_freight = next(a for a in activities if a.activity_type == "freight_road")
    assert act_freight.quantity == 3400.00
    assert act_freight.unit == "tonne.km"
    assert act_freight.geography == "US"
    assert act_freight.raw_line_ref == "INV-88903"
    assert act_freight.supplier_ref.startswith("TOKEN_SUPP_")

    # Acceptance criterion 3: Verify no raw supplier names appear in ActivityData or AuditLog
    raw_suppliers = [
        "Consolidated Edison",
        "National Grid Energy",
        "Schneider National Logistics",
    ]

    for act in activities:
        for raw in raw_suppliers:
            assert raw not in act.supplier_ref

    # Verify AuditLogEntry detail contains no raw PII
    audit_stmt = select(AuditLogEntry).where(AuditLogEntry.entity_id == entity_id)
    audit_res = await db_session.scalars(audit_stmt)
    audit_entries = audit_res.all()
    assert len(audit_entries) >= 1

    for entry in audit_entries:
        entry_json_str = json.dumps(entry.detail)
        for raw in raw_suppliers:
            assert raw not in entry_json_str
