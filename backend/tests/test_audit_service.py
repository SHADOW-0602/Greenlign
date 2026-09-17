"""Tests for AuditService (provenance graph and referential integrity)."""

import uuid
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity_data import ActivityData
from app.models.audit_log import AuditLogEntry
from app.models.calculation import Calculation
from app.models.disclosure import Disclosure
from app.models.emission_factor import EmissionFactor
from app.models.source_document import SourceDocument
from app.services.audit_service import AuditService, ReferentialIntegrityError


@pytest.fixture
async def setup_audit_entities(
    db_session: AsyncSession,
) -> tuple[SourceDocument, ActivityData, EmissionFactor, Calculation]:
    """Create a linked chain of audit entities."""
    entity_id = uuid.uuid4()

    doc = SourceDocument(
        id=uuid.uuid4(),
        entity_id=entity_id,
        filename="electric_bill_jan2025.pdf",
        file_type="pdf",
        file_size_bytes=102400,
        file_hash_sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        storage_path="documents/test/bill.pdf",
        status="completed",
    )
    db_session.add(doc)

    act = ActivityData(
        id=uuid.uuid4(),
        entity_id=entity_id,
        source_document_id=doc.id,
        raw_line_ref="page:1,line:14",
        activity_type="electricity_purchase",
        quantity=Decimal("1000"),
        unit="kWh",
        geography="US",
        period_start=date(2025, 1, 1),
        period_end=date(2025, 1, 31),
        supplier_ref="TOKEN_SUPP_CONED",
        scope=2,
        ghg_category="Purchased Electricity",
        classification_confidence=0.99,
        status="computed",
    )
    db_session.add(act)

    factor = EmissionFactor(
        id=uuid.uuid4(),
        source="EPA_GHG_Hub",
        source_version="2025",
        activity_type="electricity_purchase",
        geography="US",
        unit="kWh",
        factor_value=Decimal("0.3859"),
        factor_unit="kgCO2e/kWh",
        published_date=date(2025, 1, 1),
        effective_from=date(2025, 1, 1),
        effective_to=None,
    )
    db_session.add(factor)

    calc = Calculation(
        id=uuid.uuid4(),
        activity_data_id=act.id,
        emission_factor_id=factor.id,
        formula_applied="1000 kWh * 0.3859 kgCO2e/kWh / 1000 = 0.38590000 tCO2e",
        result_tco2e=Decimal("0.38590000"),
        computed_by="calc_engine_v1",
    )
    db_session.add(calc)

    audit_entry = AuditLogEntry(
        id=uuid.uuid4(),
        entity_type="activity_data",
        entity_id=act.id,
        action="CALCULATE",
        actor="test_runner",
        detail={"result_tco2e": "0.38590000"},
    )
    db_session.add(audit_entry)

    await db_session.commit()
    return doc, act, factor, calc


@pytest.mark.asyncio
async def test_get_calculation_trace_full_chain(
    db_session: AsyncSession,
    setup_audit_entities: tuple[SourceDocument, ActivityData, EmissionFactor, Calculation],
) -> None:
    """Verify get_calculation_trace accurately hydrates the complete end-to-end chain."""
    doc, act, factor, calc = setup_audit_entities

    service = AuditService(db_session)
    trace = await service.get_calculation_trace(calc.id)

    assert trace.calculation.id == calc.id
    assert trace.calculation.result_tco2e == Decimal("0.38590000")
    assert trace.activity.id == act.id
    assert trace.activity.raw_line_ref == "page:1,line:14"
    assert trace.source_document is not None
    assert trace.source_document.id == doc.id
    assert trace.source_document.filename == "electric_bill_jan2025.pdf"
    expected_hash = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    assert trace.source_document.file_hash_sha256 == expected_hash
    assert trace.emission_factor.id == factor.id
    assert trace.emission_factor.source == "EPA_GHG_Hub"
    assert len(trace.audit_events) >= 1
    assert trace.audit_events[0].action == "CALCULATE"
    assert len(trace.linked_disclosures) == 0


@pytest.mark.asyncio
async def test_calculation_referenced_in_disclosure_blocks_deletion(
    db_session: AsyncSession,
    setup_audit_entities: tuple[SourceDocument, ActivityData, EmissionFactor, Calculation],
) -> None:
    """A Calculation referenced in a Disclosure line_item_refs CANNOT be deleted."""
    _, _, _, calc = setup_audit_entities

    disclosure = Disclosure(
        id=uuid.uuid4(),
        entity_id=uuid.uuid4(),
        framework="CA_SB253",
        reporting_period="2025",
        status="draft",
        line_item_refs=[calc.id],
    )
    db_session.add(disclosure)
    await db_session.commit()

    service = AuditService(db_session)

    # Check deletable returns False
    check = await service.check_calculation_deletable(calc.id)
    assert check.can_delete is False
    assert disclosure.id in check.blocking_disclosures

    # Deleting raises ReferentialIntegrityError
    with pytest.raises(ReferentialIntegrityError, match="cannot be deleted"):
        await service.delete_calculation_guarded(calc.id)


@pytest.mark.asyncio
async def test_unreferenced_calculation_can_be_deleted(
    db_session: AsyncSession,
    setup_audit_entities: tuple[SourceDocument, ActivityData, EmissionFactor, Calculation],
) -> None:
    """An unreferenced calculation can be safely deleted, leaving an audit trace."""
    _, _, _, calc = setup_audit_entities

    service = AuditService(db_session)
    check = await service.check_calculation_deletable(calc.id)
    assert check.can_delete is True

    await service.delete_calculation_guarded(calc.id, actor="test_auditor")

    # Verify deleted
    deleted_calc = await db_session.get(Calculation, calc.id)
    assert deleted_calc is None


@pytest.mark.asyncio
async def test_emission_factor_referenced_by_calculation_blocks_deletion(
    db_session: AsyncSession,
    setup_audit_entities: tuple[SourceDocument, ActivityData, EmissionFactor, Calculation],
) -> None:
    """An EmissionFactor referenced by a Calculation CANNOT be deleted."""
    _, _, factor, _ = setup_audit_entities

    service = AuditService(db_session)
    check = await service.check_factor_deletable(factor.id)
    assert check.can_delete is False

    with pytest.raises(ReferentialIntegrityError, match="cannot be deleted"):
        await service.delete_emission_factor_guarded(factor.id)
