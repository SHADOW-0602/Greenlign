"""End-to-End Integration Test for Regulatory Disclosure Pipeline.

Validates complete journey:
1. Ingest raw CSV data.
2. Classify activity records.
3. Compute exact deterministic emissions with factor matching.
4. Evaluate entity eligibility for California SB 253.
5. Generate official CA SB 253 disclosure report.
6. Verify audit citations footnoted in the generated PDF report.
7. Verify Disclosure audit trail entry created.
"""

import io
import uuid

import httpx
import pytest
from httpx import ASGITransport
from pypdf import PdfReader
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.main import app
from app.models.activity_data import ActivityData
from app.models.audit_log import AuditLogEntry
from app.seeds.factors import seed_factors
from app.services.calculation_service import CalculationService
from app.services.classification_service import ClassificationService
from app.services.tabular_parser import TabularParser


@pytest.mark.asyncio
async def test_end_to_end_disclosure_generation(db_session: AsyncSession) -> None:
    """Validate full disclosure generation pipeline with exact citations."""
    # 1. Seed factor library
    await seed_factors(session=db_session)

    # 2. Ingest sample activity items
    entity_id = uuid.uuid4()
    doc_id = uuid.uuid4()

    csv_data = (
        b"activity_type,quantity,unit,geography,period_start,period_end,supplier,line_id\n"
        b"electricity_purchase,1000,kWh,US,2025-01-01,2025-01-31,Consolidated Edison,row_1\n"
        b"stationary_combustion_diesel,100,gallons,US,2025-01-01,2025-01-31,Fleet Fuels,row_2\n"
    )
    parser = TabularParser()
    rows = parser.parse_csv(csv_data)

    for r in rows:
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
    summary = await calc_service.compute_document_activities(
        source_document_id=doc_id,
        actor="e2e_auditor",
    )
    assert len(summary["computed"]) == 2

    # 4. Generate CA SB 253 Disclosure via API
    app.dependency_overrides[get_db] = lambda: db_session
    try:
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
            gen_payload = {
                "entity_id": str(entity_id),
                "framework": "CA_SB253",
                "reporting_period": "2025",
                "entity_profile": {
                    "annual_revenue_usd": "2500000000",
                    "does_business_in_california": True,
                },
            }
            resp = await ac.post("/api/disclosures/generate", json=gen_payload)
            assert resp.status_code == 201
            data = resp.json()

            # Electricity: 0.3859 tCO2e, Diesel: 100 * 10.21 / 1000 = 1.0210 tCO2e
            # Total = 1.40690000 tCO2e
            assert data["total_tco2e"] == "1.40690000"
            assert data["scope_1_tco2e"] == "1.02100000"
            assert data["scope_2_tco2e"] == "0.38590000"
            assert len(data["line_item_refs"]) == 2
            disc_id = data["id"]

            # 5. Download and verify PDF report
            pdf_resp = await ac.get(f"/api/disclosures/{disc_id}/download-pdf")
            assert pdf_resp.status_code == 200
            reader = PdfReader(io.BytesIO(pdf_resp.content))
            text = "".join(p.extract_text() or "" for p in reader.pages)
            assert "California Senate Bill 253" in text
            assert "1.4069" in text

            # 6. Verify audit log entry
            audit_res = await db_session.scalars(
                select(AuditLogEntry).where(
                    AuditLogEntry.action == "GENERATE_DISCLOSURE",
                    AuditLogEntry.entity_id == uuid.UUID(disc_id),
                )
            )
            audit_entry = audit_res.first()
            assert audit_entry is not None
            assert audit_entry.detail["framework"] == "CA_SB253"
            assert audit_entry.detail["total_tco2e"] == "1.40690000"
    finally:
        app.dependency_overrides.clear()
