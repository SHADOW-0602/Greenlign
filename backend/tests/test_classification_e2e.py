"""End-to-End integration tests for Greenlign Phase 2 classification workflow."""

import io
import uuid
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.main import app
from app.models.audit_log import AuditLogEntry
from app.services.storage_service import StorageService


class MockStorageService(StorageService):
    """In-memory storage service for E2E tests."""

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
def mock_storage() -> MockStorageService:
    return MockStorageService()


@pytest.fixture(autouse=True)
def override_e2e_deps(db_session: AsyncSession, mock_storage: MockStorageService):
    """Provide database session and mock storage for API clients."""
    app.dependency_overrides[get_db] = lambda: db_session
    with patch(
        "app.services.ingestion_service.StorageService",
        return_value=mock_storage,
    ):
        yield
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_classification_lifecycle_e2e(
    db_session: AsyncSession,
) -> None:
    """Validate full flow: upload -> parse -> auto classify -> queue review -> audit trail."""
    transport = ASGITransport(app=app)
    entity_id = str(uuid.uuid4())

    # Step 1: Upload ERP CSV with 2 items: 1 high confidence, 1 low confidence
    csv_data = (
        b"Date,Supplier,Activity,Quantity,Unit,State\n"
        b"2025-01-15,Acme Electric Co,electricity_purchase,4500,kWh,CA\n"
        b"2025-01-20,Vendor Unknown,miscellaneous_mystery_item,10,items,NY\n"
    )

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        upload_resp = await client.post(
            "/api/ingestion/upload",
            data={"entity_id": entity_id, "async_process": "false"},
            files={"file": ("erp_batch.csv", io.BytesIO(csv_data), "text/csv")},
        )
        assert upload_resp.status_code == 200
        doc_id = upload_resp.json()["document"]["id"]

        # Step 2: Trigger Batch Classification on the ingested activities
        batch_resp = await client.post(
            "/api/classification/batch-classify",
            json={"entity_id": entity_id, "document_id": doc_id},
        )
        assert batch_resp.status_code == 200
        batch_data = batch_resp.json()
        assert batch_data["total_processed"] == 2
        assert batch_data["classified_count"] >= 1
        assert batch_data["pending_review_count"] >= 1

        # Step 3: Check review queue endpoint
        queue_resp = await client.get(
            f"/api/classification/queue?entity_id={entity_id}"
        )
        assert queue_resp.status_code == 200
        queue_items = queue_resp.json()
        assert len(queue_items) == 1
        pending_item = queue_items[0]
        assert pending_item["status"] == "pending_review"
        assert pending_item["classification_confidence"] < 0.75

        # Step 4: Auditor submits manual review override
        review_resp = await client.post(
            f"/api/classification/review/{pending_item['id']}",
            json={
                "scope": 3,
                "ghg_category": "purchased_goods_services",
                "reviewer_id": "auditor_e2e_lead",
                "notes": "Reviewed itemized vendor invoice; categorized as Category 1 Supplies.",
            },
        )
        assert review_resp.status_code == 200
        review_data = review_resp.json()
        assert review_data["status"] == "success"
        assert review_data["activity"]["status"] == "classified"
        assert review_data["activity"]["scope"] == 3
        assert review_data["activity"]["classification_confidence"] == 1.0

        # Step 5: Verify review queue is now empty
        queue_after_resp = await client.get(
            f"/api/classification/queue?entity_id={entity_id}"
        )
        assert queue_after_resp.status_code == 200
        assert len(queue_after_resp.json()) == 0

        # Step 6: Verify comprehensive audit trail in database
        stmt = (
            select(AuditLogEntry)
            .where(AuditLogEntry.entity_id == uuid.UUID(pending_item["id"]))
            .order_by(AuditLogEntry.timestamp.asc())
        )
        res = await db_session.execute(stmt)
        audit_entries = list(res.scalars().all())

        # Should have 2 audit entries for this item: 1 automatic CLASSIFY, 1 CLASSIFY_OVERRIDE
        assert len(audit_entries) == 2
        assert audit_entries[0].action == "CLASSIFY"
        assert audit_entries[0].actor == "system:scope_classifier"
        assert audit_entries[1].action == "CLASSIFY_OVERRIDE"
        assert audit_entries[1].actor == "user:auditor_e2e_lead"
        assert audit_entries[1].detail["notes"] == (
            "Reviewed itemized vendor invoice; categorized as Category 1 Supplies."
        )
