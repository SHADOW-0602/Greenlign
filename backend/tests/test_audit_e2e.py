"""End-to-End Integration Test for Audit Trail & Governance Log.

Tests complete journey:
1. Ingest raw file (creates SourceDocument with sha256 hash).
2. Classify activity and compute emissions (creates Calculation and AuditLogEntry records).
3. Create regulatory Disclosure referencing the calculation in line_item_refs.
4. Verify GET /api/audit/trace/{calc_id} hydrates the entire provenance chain
   including the disclosure.
5. Verify guarded deletion prevents deleting the referenced Calculation or EmissionFactor.
"""

import uuid

import httpx
import pytest
from httpx import ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.main import app
from app.models.activity_data import ActivityData
from app.models.disclosure import Disclosure
from app.models.source_document import SourceDocument
from app.seeds.factors import seed_factors
from app.services.calculation_service import CalculationService
from app.services.classification_service import ClassificationService
from app.services.tabular_parser import TabularParser


@pytest.mark.asyncio
async def test_end_to_end_audit_trail_lifecycle(db_session: AsyncSession) -> None:
    """Validate full provenance chain and referential integrity governance."""
    # 1. Seed factor library
    await seed_factors(session=db_session)

    # 2. Ingest sample document and activities
    entity_id = uuid.uuid4()
    doc_id = uuid.uuid4()
    doc_hash = "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"

    doc = SourceDocument(
        id=doc_id,
        entity_id=entity_id,
        filename="utility_bills_q1.csv",
        file_type="csv",
        file_size_bytes=1024,
        file_hash_sha256=doc_hash,
        storage_path="documents/test/q1.csv",
        status="completed",
    )
    db_session.add(doc)

    csv_data = (
        b"activity_type,quantity,unit,geography,period_start,period_end,supplier,line_id\n"
        b"electricity_purchase,1000,kWh,US,2025-01-01,2025-01-31,Consolidated Edison,line_1\n"
    )
    parser = TabularParser()
    rows = parser.parse_csv(csv_data)
    r = rows[0]

    act = ActivityData(
        id=uuid.uuid4(),
        entity_id=entity_id,
        source_document_id=doc_id,
        raw_line_ref=r.raw_line_ref,
        activity_type=r.activity_type,
        quantity=r.quantity,
        unit=r.unit,
        geography=r.geography,
        period_start=r.period_start,
        period_end=r.period_end,
        supplier_ref=r.supplier_ref,
        status="pending_review",
    )
    db_session.add(act)
    await db_session.commit()

    # 3. Classify & Compute
    classifier = ClassificationService()
    await classifier.batch_classify(session=db_session, document_id=doc_id)

    calc_service = CalculationService(db_session)
    calc_summary = await calc_service.compute_document_activities(
        source_document_id=doc_id,
        actor="e2e_auditor",
    )
    assert len(calc_summary["computed"]) == 1
    calc_id = uuid.UUID(calc_summary["computed"][0]["calculation_id"])

    # 4. Create Disclosure referencing calculation
    disclosure = Disclosure(
        id=uuid.uuid4(),
        entity_id=entity_id,
        framework="CA_SB253",
        reporting_period="2025-Q1",
        status="draft",
        line_item_refs=[calc_id],
    )
    db_session.add(disclosure)
    await db_session.commit()

    # 5. Query Audit Trace API
    app.dependency_overrides[get_db] = lambda: db_session
    try:
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.get(f"/api/audit/trace/{calc_id}")
            assert resp.status_code == 200
            data = resp.json()

            # Verify complete chain
            assert data["calculation"]["id"] == str(calc_id)
            assert data["calculation"]["result_tco2e"] == "0.38590000"
            assert data["source_document"]["file_hash_sha256"] == doc_hash
            assert data["source_document"]["filename"] == "utility_bills_q1.csv"
            assert data["activity"]["raw_line_ref"] == r.raw_line_ref
            assert data["activity"]["scope"] == 2
            assert data["emission_factor"]["source"] == "EPA_GHG_Hub"
            assert len(data["linked_disclosures"]) == 1
            assert data["linked_disclosures"][0]["framework"] == "CA_SB253"

            # 6. Verify Deletion Guard
            del_resp = await ac.delete(f"/api/audit/calculations/{calc_id}")
            assert del_resp.status_code == 409
            assert "cannot be deleted" in del_resp.json()["detail"]
    finally:
        app.dependency_overrides.clear()
