"""Tests for ClassificationService and audit logging orchestration."""

import uuid
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity_data import ActivityData
from app.models.audit_log import AuditLogEntry
from app.services.classification_service import ClassificationService


@pytest.fixture
def sample_activity() -> ActivityData:
    return ActivityData(
        id=uuid.uuid4(),
        entity_id=uuid.uuid4(),
        raw_line_ref="row:1",
        activity_type="purchased_grid_electricity",
        quantity=Decimal("1500.5"),
        unit="kWh",
        geography="US",
        period_start=date(2025, 1, 1),
        period_end=date(2025, 1, 31),
        supplier_ref="TOKEN_SUPP_1234567890",
        status="pending",
    )


async def test_classify_activity_high_confidence(
    db_session: AsyncSession, sample_activity: ActivityData
) -> None:
    db_session.add(sample_activity)
    await db_session.commit()

    service = ClassificationService()
    updated = await service.classify_activity(db_session, sample_activity)

    assert updated.scope == 2
    assert updated.ghg_category == "purchased_electricity"
    assert updated.classification_confidence is not None
    assert updated.classification_confidence >= 0.75
    assert updated.status == "classified"

    # Verify audit log entry
    stmt = select(AuditLogEntry).where(
        AuditLogEntry.entity_id == sample_activity.id,
        AuditLogEntry.action == "CLASSIFY",
    )
    result = await db_session.execute(stmt)
    audit = result.scalar_one_or_none()
    assert audit is not None
    assert audit.entity_type == "ActivityData"
    assert audit.actor == "system:scope_classifier"
    assert audit.detail["scope"] == 2
    assert audit.detail["ghg_category"] == "purchased_electricity"
    assert audit.detail["status"] == "classified"


async def test_classify_activity_low_confidence_gates_to_pending_review(
    db_session: AsyncSession, sample_activity: ActivityData
) -> None:
    sample_activity.activity_type = "unidentifiable_miscellaneous_code"
    sample_activity.unit = "items"
    sample_activity.raw_line_ref = "row:99"
    db_session.add(sample_activity)
    await db_session.commit()

    service = ClassificationService()
    updated = await service.classify_activity(db_session, sample_activity)

    assert updated.classification_confidence is not None
    assert updated.classification_confidence < 0.75
    assert updated.status == "pending_review"

    # Verify audit log entry created even when pending review
    stmt = select(AuditLogEntry).where(
        AuditLogEntry.entity_id == sample_activity.id,
        AuditLogEntry.action == "CLASSIFY",
    )
    result = await db_session.execute(stmt)
    audit = result.scalar_one_or_none()
    assert audit is not None
    assert audit.detail["status"] == "pending_review"


async def test_batch_classify(
    db_session: AsyncSession,
) -> None:
    entity_id = uuid.uuid4()
    act1 = ActivityData(
        id=uuid.uuid4(),
        entity_id=entity_id,
        raw_line_ref="INV-01",
        activity_type="facility_natural_gas_boiler",
        quantity=Decimal("500"),
        unit="therms",
        geography="US",
        period_start=date(2025, 1, 1),
        period_end=date(2025, 1, 31),
        supplier_ref="TOKEN_SUPP_GAS",
        status="pending",
    )
    act2 = ActivityData(
        id=uuid.uuid4(),
        entity_id=entity_id,
        raw_line_ref="INV-02",
        activity_type="commercial_domestic_flight",
        quantity=Decimal("1200"),
        unit="passenger.km",
        geography="US",
        period_start=date(2025, 2, 1),
        period_end=date(2025, 2, 28),
        supplier_ref="TOKEN_SUPP_AIRLINE",
        status="pending",
    )
    db_session.add_all([act1, act2])
    await db_session.commit()

    service = ClassificationService()
    classified_items = await service.batch_classify(db_session, entity_id=entity_id)

    assert len(classified_items) == 2
    scopes = {item.scope for item in classified_items}
    assert scopes == {1, 3}
    assert all(item.status == "classified" for item in classified_items)


async def test_apply_human_review(
    db_session: AsyncSession, sample_activity: ActivityData
) -> None:
    sample_activity.status = "pending_review"
    sample_activity.scope = 3
    sample_activity.ghg_category = "purchased_goods_services"
    sample_activity.classification_confidence = 0.50
    db_session.add(sample_activity)
    await db_session.commit()

    service = ClassificationService()
    updated = await service.apply_human_review(
        session=db_session,
        activity_id=sample_activity.id,
        reviewer_id="auditor_jane",
        scope=2,
        ghg_category="purchased_electricity",
        notes="Corrected after inspecting utility rate tariff.",
    )

    assert updated.scope == 2
    assert updated.ghg_category == "purchased_electricity"
    assert updated.classification_confidence == 1.0
    assert updated.status == "classified"

    # Verify audit trail contains reviewer override
    stmt = select(AuditLogEntry).where(
        AuditLogEntry.entity_id == sample_activity.id,
        AuditLogEntry.action == "CLASSIFY_OVERRIDE",
    )
    result = await db_session.execute(stmt)
    audit = result.scalar_one_or_none()
    assert audit is not None
    assert audit.actor == "user:auditor_jane"
    assert audit.detail["new_scope"] == 2
    assert audit.detail["new_ghg_category"] == "purchased_electricity"
    assert audit.detail["notes"] == "Corrected after inspecting utility rate tariff."


async def test_apply_human_review_invalid_category_raises(
    db_session: AsyncSession, sample_activity: ActivityData
) -> None:
    db_session.add(sample_activity)
    await db_session.commit()

    service = ClassificationService()
    with pytest.raises(ValueError, match="Invalid category"):
        await service.apply_human_review(
            session=db_session,
            activity_id=sample_activity.id,
            reviewer_id="auditor_bob",
            scope=1,
            ghg_category="purchased_electricity",  # Invalid for Scope 1!
        )
