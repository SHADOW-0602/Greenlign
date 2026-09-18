"""API tests for the /api/outreach router."""

import uuid

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.main import app


@pytest.mark.asyncio
async def test_generate_email_api(db_session: AsyncSession) -> None:
    """Verify POST /api/outreach/generate-email generates inquiry email."""
    app.dependency_overrides[get_db] = lambda: db_session
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            payload = {
                "supplier_name": "Apex Logistics Group",
                "supplier_ref": "SUPP_APEX_1",
                "activity_type": "freight_ocean_container",
                "reporting_period": "2025",
                "template_type": "PRIMARY_EMISSION_FACTOR",
            }
            resp = await client.post("/api/outreach/generate-email", json=payload)
            assert resp.status_code == 200
            data = resp.json()
            assert data["template_type"] == "PRIMARY_EMISSION_FACTOR"
            assert "subject" in data and len(data["subject"]) > 5
            assert "body" in data and len(data["body"]) > 20
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_create_send_and_record_outreach_api(db_session: AsyncSession) -> None:
    """Verify full API lifecycle: create outreach -> send -> record supplier response."""
    entity_id = uuid.uuid4()
    app.dependency_overrides[get_db] = lambda: db_session
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. Create outreach
            create_payload = {
                "entity_id": str(entity_id),
                "supplier_ref": "SUPP_CHEM_88",
                "supplier_name": "ChemPure Solutions",
                "supplier_email": "compliance@chempure.com",
                "contact_name": "David Green",
                "activity_type": "specialty_chemicals",
                "reporting_period": "2025",
                "template_type": "PRIMARY_EMISSION_FACTOR",
                "custom_subject": "Primary Factor Request - ChemPure FY25",
                "custom_body": "Please provide primary PCF data.",
            }
            create_resp = await client.post("/api/outreach", json=create_payload)
            assert create_resp.status_code == 201
            outreach_data = create_resp.json()
            outreach_id = outreach_data["id"]
            assert outreach_data["status"] == "DRAFT"

            # 2. List outreach
            list_resp = await client.get(f"/api/outreach?entity_id={entity_id}")
            assert list_resp.status_code == 200
            assert len(list_resp.json()) == 1

            # 3. Send outreach
            send_resp = await client.post(f"/api/outreach/{outreach_id}/send")
            assert send_resp.status_code == 200
            assert send_resp.json()["status"] == "SENT"
            assert send_resp.json()["sent_at"] is not None

            # 4. Record response
            resp_payload = {
                "primary_factor_value": 0.45,
                "primary_factor_unit": "kgCO2e/kg",
                "verified_quantity": 12000.0,
                "response_notes": "Third-party verified cradle-to-gate LCA.",
            }
            rec_resp = await client.patch(
                f"/api/outreach/{outreach_id}/record-response", json=resp_payload
            )
            assert rec_resp.status_code == 200
            updated_data = rec_resp.json()
            assert updated_data["status"] == "RECEIVED"
            assert updated_data["responded_at"] is not None
            assert updated_data["response_data_json"]["primary_factor_value"] == 0.45
    finally:
        app.dependency_overrides.clear()
