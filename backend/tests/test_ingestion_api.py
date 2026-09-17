"""Tests for Ingestion API endpoints."""

import io
import uuid
from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import get_db
from app.main import app
from app.services.storage_service import StorageService


class MockStorageService(StorageService):
    """In-memory storage service mock."""

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
            raise FileNotFoundError(f"Not found: {storage_path}")
        return self.store[storage_path]

    def delete_file(self, storage_path: str) -> None:
        self.store.pop(storage_path, None)


@pytest.fixture
def mock_storage():
    return MockStorageService()


@pytest.fixture(autouse=True)
def override_deps(db_session, mock_storage):
    """Override database dependency and patch StorageService globally for API tests."""
    app.dependency_overrides[get_db] = lambda: db_session
    with patch("app.services.ingestion_service.StorageService", return_value=mock_storage):
        yield
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_upload_csv_sync():
    transport = ASGITransport(app=app)
    entity_id = str(uuid.uuid4())
    csv_bytes = (
        b"Date,Supplier,Activity,Quantity,Unit,State\n"
        b"2025-01-10,PG&E,electricity_purchase,1200,kWh,CA\n"
    )

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/ingestion/upload",
            data={"entity_id": entity_id, "async_process": "false"},
            files={"file": ("test_data.csv", io.BytesIO(csv_bytes), "text/csv")},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["activities_count"] == 1
    assert data["document"]["status"] == "completed"
    assert data["document"]["filename"] == "test_data.csv"
    assert data["document"]["file_type"] == "csv"
    assert data["task_id"] is None


@pytest.mark.asyncio
async def test_upload_async_enqueues_celery_task():
    transport = ASGITransport(app=app)
    entity_id = str(uuid.uuid4())
    csv_bytes = (
        b"Date,Supplier,Activity,Quantity,Unit,State\n"
        b"2025-01-10,PG&E,electricity_purchase,1200,kWh,CA\n"
    )

    mock_async_result = MagicMock()
    mock_async_result.id = "mock-task-id-12345"

    with patch(
        "app.api.ingestion.process_document_task.delay", return_value=mock_async_result
    ) as mock_delay:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/ingestion/upload",
                data={"entity_id": entity_id, "async_process": "true"},
                files={"file": ("test_async.csv", io.BytesIO(csv_bytes), "text/csv")},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == "mock-task-id-12345"
        assert data["document"]["status"] == "pending"
        mock_delay.assert_called_once()


@pytest.mark.asyncio
async def test_list_and_get_documents():
    transport = ASGITransport(app=app)
    entity_id = str(uuid.uuid4())
    csv_bytes = (
        b"Date,Supplier,Activity,Quantity,Unit,State\n"
        b"2025-01-10,Utility,electricity_purchase,500,kWh,US\n"
    )

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Upload a document
        upload_res = await client.post(
            "/api/ingestion/upload",
            data={"entity_id": entity_id},
            files={"file": ("list_test.csv", io.BytesIO(csv_bytes), "text/csv")},
        )
        assert upload_res.status_code == 200
        doc_id = upload_res.json()["document"]["id"]

        # 2. List documents
        list_res = await client.get(f"/api/ingestion/documents?entity_id={entity_id}")
        assert list_res.status_code == 200
        docs = list_res.json()
        assert len(docs) >= 1
        assert any(d["id"] == doc_id for d in docs)

        # 3. Get document detail
        detail_res = await client.get(f"/api/ingestion/documents/{doc_id}")
        assert detail_res.status_code == 200
        detail = detail_res.json()
        assert detail["document"]["id"] == doc_id
        assert len(detail["activities"]) == 1
        assert detail["activities"][0]["supplier_ref"].startswith("TOKEN_SUPP_")


@pytest.mark.asyncio
async def test_upload_invalid_file_type_returns_400():
    transport = ASGITransport(app=app)
    entity_id = str(uuid.uuid4())

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/ingestion/upload",
            data={"entity_id": entity_id},
            files={"file": ("unsupported.txt", io.BytesIO(b"random text"), "text/plain")},
        )

    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]
