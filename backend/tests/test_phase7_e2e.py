"""End-to-end integration test for Greenlign Phase 7.

Tests full lifecycle across:
1. Executive ESG Analytics Dashboard aggregation
2. Decarbonization Scenario Simulator & MACC ROI ranking
3. Scope 3 Supplier Outreach Agent & Primary Data Ingestion
4. Complete Audit Trail Verification
"""

import uuid
from datetime import date
from decimal import Decimal

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.main import app
from app.models.activity_data import ActivityData
from app.models.anomaly_flag import AnomalyFlag
from app.models.audit_log import AuditLogEntry
from app.models.calculation import Calculation
from app.models.emission_factor import EmissionFactor


@pytest.mark.asyncio
async def test_phase7_end_to_end_lifecycle(db_session: AsyncSession) -> None:
    """Full Phase 7 lifecycle: dashboard -> simulation -> supplier outreach -> audit log."""
    entity_id = uuid.uuid4()
    source_doc_id = uuid.uuid4()

    # 1. Setup Emission Factors
    factor_elec = EmissionFactor(
        source="EPA_eGRID",
        source_version="2025",
        activity_type="electricity_purchase",
        geography="US",
        unit="kWh",
        factor_value=Decimal("0.4"),
        factor_unit="kgCO2e/kWh",
        published_date=date(2025, 1, 1),
        effective_from=date(2025, 1, 1),
    )
    factor_gas = EmissionFactor(
        source="EPA_GHG_Hub",
        source_version="2025",
        activity_type="natural_gas",
        geography="US",
        unit="therms",
        factor_value=Decimal("5.3"),
        factor_unit="kgCO2e/therm",
        published_date=date(2025, 1, 1),
        effective_from=date(2025, 1, 1),
    )
    factor_goods = EmissionFactor(
        source="DEFRA",
        source_version="2025",
        activity_type="purchased_goods",
        geography="US",
        unit="USD",
        factor_value=Decimal("0.3"),
        factor_unit="kgCO2e/USD",
        published_date=date(2025, 1, 1),
        effective_from=date(2025, 1, 1),
    )
    factor_flight = EmissionFactor(
        source="DEFRA",
        source_version="2025",
        activity_type="flight",
        geography="US",
        unit="km",
        factor_value=Decimal("0.2"),
        factor_unit="kgCO2e/km",
        published_date=date(2025, 1, 1),
        effective_from=date(2025, 1, 1),
    )
    db_session.add_all([factor_elec, factor_gas, factor_goods, factor_flight])
    await db_session.flush()

    # 2. Setup Activity & Calculation Data (FY2025)
    # Scope 1: 10,000 therms -> 53.0 tCO2e
    act_gas = ActivityData(
        source_document_id=source_doc_id,
        raw_line_ref="gas_row",
        entity_id=entity_id,
        activity_type="natural_gas",
        quantity=Decimal("10000"),
        unit="therms",
        geography="US",
        period_start=date(2025, 1, 1),
        period_end=date(2025, 12, 31),
        supplier_ref="SUPP_GAS_CO",
        scope=1,
        ghg_category="Scope 1.1 Stationary Combustion",
        status="calculated",
    )
    db_session.add(act_gas)
    await db_session.flush()

    calc_gas = Calculation(
        activity_data_id=act_gas.id,
        emission_factor_id=factor_gas.id,
        formula_applied="10000 therms * 5.3 kgCO2e/therm",
        result_tco2e=Decimal("53.0"),
        computed_by="calc_engine_v1",
    )
    db_session.add(calc_gas)

    # Scope 2: 100,000 kWh -> 40.0 tCO2e
    act_elec = ActivityData(
        source_document_id=source_doc_id,
        raw_line_ref="elec_row",
        entity_id=entity_id,
        activity_type="electricity_purchase",
        quantity=Decimal("100000"),
        unit="kWh",
        geography="US",
        period_start=date(2025, 1, 1),
        period_end=date(2025, 12, 31),
        supplier_ref="SUPP_GRID_UTIL",
        scope=2,
        ghg_category="Scope 2.1 Purchased Electricity",
        status="calculated",
    )
    db_session.add(act_elec)
    await db_session.flush()

    calc_elec = Calculation(
        activity_data_id=act_elec.id,
        emission_factor_id=factor_elec.id,
        formula_applied="100000 kWh * 0.4 kgCO2e/kWh",
        result_tco2e=Decimal("40.0"),
        computed_by="calc_engine_v1",
    )
    db_session.add(calc_elec)

    # Scope 3.1: Purchased Goods (Acme Packaging) -> $50,000 -> 15.0 tCO2e
    act_goods = ActivityData(
        source_document_id=source_doc_id,
        raw_line_ref="goods_row",
        entity_id=entity_id,
        activity_type="purchased_goods",
        quantity=Decimal("50000"),
        unit="USD",
        geography="US",
        period_start=date(2025, 1, 1),
        period_end=date(2025, 12, 31),
        supplier_ref="SUPP_ACME_PACKAGING",
        scope=3,
        ghg_category="Scope 3.1 Purchased Goods",
        status="calculated",
    )
    db_session.add(act_goods)
    await db_session.flush()

    calc_goods = Calculation(
        activity_data_id=act_goods.id,
        emission_factor_id=factor_goods.id,
        formula_applied="50000 USD * 0.3 kgCO2e/USD",
        result_tco2e=Decimal("15.0"),
        computed_by="calc_engine_v1",
    )
    db_session.add(calc_goods)

    # Scope 3.6: Flight Travel -> 30,000 km -> 6.0 tCO2e
    act_flight = ActivityData(
        source_document_id=source_doc_id,
        raw_line_ref="flight_row",
        entity_id=entity_id,
        activity_type="flight",
        quantity=Decimal("30000"),
        unit="km",
        geography="US",
        period_start=date(2025, 1, 1),
        period_end=date(2025, 12, 31),
        supplier_ref="SUPP_AIRLINES",
        scope=3,
        ghg_category="Scope 3.6 Business Travel",
        status="calculated",
    )
    db_session.add(act_flight)
    await db_session.flush()

    calc_flight = Calculation(
        activity_data_id=act_flight.id,
        emission_factor_id=factor_flight.id,
        formula_applied="30000 km * 0.2 kgCO2e/km",
        result_tco2e=Decimal("6.0"),
        computed_by="calc_engine_v1",
    )
    db_session.add(calc_flight)

    # Add AnomalyFlag
    flag = AnomalyFlag(
        entity_id=entity_id,
        reporting_period="2025",
        flag_type="YOY_DROP",
        severity="WARNING",
        title="Unusual 60% drop in freight emissions",
        description="Investigation required",
        status="OPEN",
        details_json={},
    )
    db_session.add(flag)
    await db_session.commit()

    # Total Gross Baseline: 53.0 + 40.0 + 15.0 + 6.0 = 114.0 tCO2e
    app.dependency_overrides[get_db] = lambda: db_session
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            # -------------------------------------------------------------
            # STEP 1: Verify Executive ESG Analytics Dashboard
            # -------------------------------------------------------------
            dash_resp = await client.get(
                f"/api/dashboard/summary?entity_id={entity_id}&reporting_period=2025"
            )
            assert dash_resp.status_code == 200
            dash = dash_resp.json()

            assert dash["entity_id"] == str(entity_id)
            assert dash["gross_emissions_tco2e"] == pytest.approx(114.0, rel=1e-2)
            assert dash["total_calculations"] == 4
            assert dash["open_anomalies_count"] == 1

            scope_map = {s["scope"]: s for s in dash["scope_breakdown"]}
            assert scope_map[1]["total_tco2e"] == pytest.approx(53.0)
            assert scope_map[2]["total_tco2e"] == pytest.approx(40.0)
            assert scope_map[3]["total_tco2e"] == pytest.approx(21.0)  # 15 + 6

            assert len(dash["top_hotspots"]) >= 3
            assert dash["top_hotspots"][0]["ghg_category"] == "Scope 1.1 Stationary Combustion"

            # -------------------------------------------------------------
            # STEP 2: Verify Decarbonization Scenario Simulator & MACC
            # -------------------------------------------------------------
            levers_resp = await client.get("/api/simulator/levers")
            assert levers_resp.status_code == 200
            catalog = levers_resp.json()
            assert len(catalog) >= 4

            sim_payload = {
                "entity_id": str(entity_id),
                "reporting_period": "2025",
                "applied_levers": [
                    {
                        "lever_id": "SOLAR_PPA_GRID_ELEC",
                        "implementation_rate": 1.0,  # 100% green power: 40.0 tCO2e abated
                        "custom_capex_usd": 0.0,
                        "custom_annual_opex_delta_usd": -3000.0,  # -$75/tCO2e
                    },
                    {
                        "lever_id": "BUSINESS_TRAVEL_MODAL_SHIFT",
                        "implementation_rate": 0.5,  # 50% * 0.85 = 42.5% * 6.0 = 2.55 tCO2e abated
                        "custom_capex_usd": 0.0,
                        "custom_annual_opex_delta_usd": -2550.0,  # -$1000/tCO2e
                    },
                ],
                "target_reduction_percent": 30.0,
            }
            sim_resp = await client.post("/api/simulator/simulate", json=sim_payload)
            assert sim_resp.status_code == 200
            sim = sim_resp.json()

            assert sim["baseline_gross_tco2e"] == pytest.approx(114.0, rel=1e-2)
            assert sim["total_reduction_tco2e"] == pytest.approx(42.55, rel=1e-2)
            assert sim["simulated_gross_tco2e"] == pytest.approx(71.45, rel=1e-2)
            assert sim["total_reduction_percent"] == pytest.approx(37.32, rel=1e-1)
            assert sim["target_met"] is True

            # Check MACC rank: Travel modal shift (-$1000/t) ranks before Solar PPA (-$75/t)
            assert len(sim["ranked_levers"]) == 2
            assert sim["ranked_levers"][0]["lever_id"] == "BUSINESS_TRAVEL_MODAL_SHIFT"
            assert sim["ranked_levers"][0]["roi_rank"] == 1
            assert sim["ranked_levers"][1]["lever_id"] == "SOLAR_PPA_GRID_ELEC"
            assert sim["ranked_levers"][1]["roi_rank"] == 2

            # -------------------------------------------------------------
            # STEP 3: Verify Scope 3 Supplier Outreach Agent
            # -------------------------------------------------------------
            missing_resp = await client.get(
                f"/api/outreach/missing-scope3?entity_id={entity_id}&reporting_period=2025"
            )
            assert missing_resp.status_code == 200
            missing_list = missing_resp.json()
            assert len(missing_list) >= 1
            supp_refs = [m["supplier_ref"] for m in missing_list]
            assert "SUPP_ACME_PACKAGING" in supp_refs

            # Generate AI email draft
            gen_resp = await client.post(
                "/api/outreach/generate-email",
                json={
                    "supplier_name": "Acme Packaging Co",
                    "supplier_ref": "SUPP_ACME_PACKAGING",
                    "activity_type": "purchased_goods",
                    "reporting_period": "2025",
                    "template_type": "PRIMARY_EMISSION_FACTOR",
                },
            )
            assert gen_resp.status_code == 200
            email_draft = gen_resp.json()
            assert "subject" in email_draft and "body" in email_draft

            # Create outreach record
            create_resp = await client.post(
                "/api/outreach",
                json={
                    "entity_id": str(entity_id),
                    "supplier_ref": "SUPP_ACME_PACKAGING",
                    "supplier_name": "Acme Packaging Co",
                    "supplier_email": "sustainability@acmepackaging.com",
                    "contact_name": "Alex Rivera",
                    "activity_type": "purchased_goods",
                    "reporting_period": "2025",
                    "template_type": "PRIMARY_EMISSION_FACTOR",
                    "custom_subject": email_draft["subject"],
                    "custom_body": email_draft["body"],
                },
            )
            assert create_resp.status_code == 201
            outreach = create_resp.json()
            outreach_id = outreach["id"]
            assert outreach["status"] == "DRAFT"

            # Dispatch outreach
            send_resp = await client.post(f"/api/outreach/{outreach_id}/send")
            assert send_resp.status_code == 200
            assert send_resp.json()["status"] == "SENT"

            # Ingest supplier primary response
            record_resp = await client.patch(
                f"/api/outreach/{outreach_id}/record-response",
                json={
                    "primary_factor_value": 0.15,  # 50% lower than DEFRA proxy (0.3)
                    "primary_factor_unit": "kgCO2e/USD",
                    "verified_quantity": 50000.0,
                    "response_notes": "Acme certified using 100% recycled post-consumer pulp.",
                },
            )
            assert record_resp.status_code == 200
            rec_data = record_resp.json()
            assert rec_data["status"] == "RECEIVED"
            assert rec_data["response_data_json"]["primary_factor_value"] == 0.15

            # -------------------------------------------------------------
            # STEP 4: Verify Governance Audit Log Entries
            # -------------------------------------------------------------
            audit_stmt = (
                select(AuditLogEntry)
                .where(
                    AuditLogEntry.entity_type == "supplier_outreach",
                    AuditLogEntry.entity_id == uuid.UUID(outreach_id),
                )
                .order_by(AuditLogEntry.timestamp.asc())
            )
            audit_res = await db_session.execute(audit_stmt)
            audit_entries = list(audit_res.scalars().all())

            actions = [entry.action for entry in audit_entries]
            assert "CREATE_SUPPLIER_OUTREACH" in actions
            assert "DISPATCH_SUPPLIER_OUTREACH" in actions
            assert "RECORD_SUPPLIER_PRIMARY_DATA" in actions
    finally:
        app.dependency_overrides.clear()
