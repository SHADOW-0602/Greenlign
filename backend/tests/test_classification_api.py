"""Integration tests for Classification and Review Queue REST API."""

import uuid
from datetime import date
from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.main import app
from app.models.activity_data import ActivityData


@pytest.fixture(autouse=True)
def override_deps(db_session: AsyncSession):
    """Override database dependency for API tests."""
    app.dependency_overrides[get_db] = lambda: db_session
    yield
    app.dependency_overrides.clear()


@pytest.fixture
async def sample_pending_activity(db_session: AsyncSession) -> ActivityData:
    act = ActivityData(
        id=uuid.uuid4(),
        entity_id=uuid.uuid4(),
        raw_line_ref="INV-REV-01",
        activity_type="ambiguous_facility_charge",
        quantity=Decimal("100"),
        unit="units",
        geography="US",
        period_start=date(2025, 1, 1),
        period_end=date(2025, 1, 31),
        supplier_ref="TOKEN_SUPP_UNKNOWN",
        scope=3,
        ghg_category="purchased_goods_services",
        classification_confidence=0.50,
        status="pending_review",
    )
    db_session.add(act)
    await db_session.commit()
    await db_session.refresh(act)
    return act


async def test_get_review_queue_returns_pending_items(
    db_session: AsyncSession, sample_pending_activity: ActivityData
) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/classification/queue")

    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    item_ids = [item["id"] for item in data]
    assert str(sample_pending_activity.id) in item_ids


async def test_get_review_queue_filter_by_entity_id(
    db_session: AsyncSession, sample_pending_activity: ActivityData
) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            f"/api/classification/queue?entity_id={sample_pending_activity.entity_id}"
        )

    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert data[0]["entity_id"] == str(sample_pending_activity.entity_id)


async def test_post_human_review_success(
    db_session: AsyncSession, sample_pending_activity: ActivityData
) -> None:
    transport = ASGITransport(app=app)
    payload = {
        "scope": 1,
        "ghg_category": "stationary_combustion",
        "reviewer_id": "auditor_jane",
        "notes": "Confirmed natural gas heating bill.",
    }
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            f"/api/classification/review/{sample_pending_activity.id}",
            json=payload,
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["activity"]["scope"] == 1
    assert data["activity"]["ghg_category"] == "stationary_combustion"
    assert data["activity"]["status"] == "classified"
    assert data["activity"]["classification_confidence"] == 1.0


async def test_post_human_review_invalid_category_returns_400(
    db_session: AsyncSession, sample_pending_activity: ActivityData
) -> None:
    transport = ASGITransport(app=app)
    payload = {
        "scope": 1,
        "ghg_category": "purchased_electricity",  # Invalid for Scope 1!
        "reviewer_id": "auditor_jane",
    }
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            f"/api/classification/review/{sample_pending_activity.id}",
            json=payload,
        )

    assert resp.status_code == 400
    assert "Invalid category" in resp.json()["detail"]


async def test_post_human_review_not_found_returns_404() -> None:
    transport = ASGITransport(app=app)
    payload = {
        "scope": 2,
        "ghg_category": "purchased_electricity",
        "reviewer_id": "auditor_jane",
    }
    non_existent_id = uuid.uuid4()
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            f"/api/classification/review/{non_existent_id}",
            json=payload,
        )

    assert resp.status_code == 404


async def test_batch_classify_endpoint(
    db_session: AsyncSession,
) -> None:
    entity_id = uuid.uuid4()
    act = ActivityData(
        id=uuid.uuid4(),
        entity_id=entity_id,
        raw_line_ref="INV-BC-01",
        activity_type="office_chiller_district_cooling",
        quantity=Decimal("250"),
        unit="ton_hours",
        geography="US",
        period_start=date(2025, 1, 1),
        period_end=date(2025, 1, 31),
        supplier_ref="TOKEN_SUPP_COOL",
        status="pending",
    )
    db_session.add(act)
    await db_session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/classification/batch-classify",
            json={"entity_id": str(entity_id), "limit": 10},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["total_processed"] >= 1
    assert len(data["items"]) >= 1
    assert data["items"][0]["scope"] == 2
    assert data["items"][0]["ghg_category"] == "purchased_cooling"
