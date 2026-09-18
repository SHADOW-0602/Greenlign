"""Corporate demo data seed script for Greenlign."""
import asyncio
import datetime
import uuid
from decimal import Decimal

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.activity_data import ActivityData
from app.models.anomaly_flag import AnomalyFlag
from app.models.calculation import Calculation
from app.models.emission_factor import EmissionFactor
from app.models.source_document import SourceDocument
from app.models.supplier_outreach import SupplierOutreach
from app.services.calc_engine import compute_emission

ENTITY_ID = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")

async def seed_corporate_data():
    async with AsyncSessionLocal() as session:
        # Check if already seeded
        existing = await session.scalar(
            select(ActivityData).where(ActivityData.entity_id == ENTITY_ID)
        )
        if existing:
            print("Corporate data already seeded for entity:", ENTITY_ID)
            return

        print("Seeding corporate data for Acme Global Corp...")

        # 1. Source Documents
        doc1 = SourceDocument(
            id=uuid.uuid4(),
            entity_id=ENTITY_ID,
            filename="FY2025_HQ_Utility_Power_Bills.pdf",
            file_type="pdf",
            file_hash_sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            file_size_bytes=245800,
            storage_path="documents/550e8400-e29b-41d4-a716-446655440000/bills.pdf",
            status="completed",
        )
        doc2 = SourceDocument(
            id=uuid.uuid4(),
            entity_id=ENTITY_ID,
            filename="FY2025_Vehicle_Fleet_Logs.xlsx",
            file_type="xlsx",
            file_hash_sha256="c4ca4238a0b923820dcc509a6f75849b27ae41e4649b934ca495991b7852b855",
            file_size_bytes=112400,
            storage_path="documents/550e8400-e29b-41d4-a716-446655440000/fleet.xlsx",
            status="completed",
        )
        session.add_all([doc1, doc2])
        await session.flush()

        # Load factors map
        factors = (await session.scalars(select(EmissionFactor))).all()
        f_map = {(f.activity_type, f.geography): f for f in factors}

        activities_spec = [
            # 2025 Data
            (
                "natural_gas_combustion", "US", Decimal("12000"), "MMBtu", 1,
                "Scope 1 Stationary Combustion", doc1.id, 2025, 1, 1, 2025, 12, 31,
                "facility-gas-meter-01", "Acme Facilities Management"
            ),
            (
                "mobile_combustion_gasoline", "US", Decimal("85000"), "gallons", 1,
                "Scope 1 Mobile Combustion", doc2.id, 2025, 1, 1, 2025, 12, 31,
                "fleet-card-us", "Shell Fleet Services"
            ),
            (
                "stationary_combustion_diesel", "US", Decimal("14000"), "gallons", 1,
                "Scope 1 Stationary Combustion", doc2.id, 2025, 1, 1, 2025, 12, 31,
                "backup-generator-02", "Sunoco Commercial"
            ),
            (
                "electricity_purchase", "US-CA", Decimal("4200000"), "kWh", 2,
                "Scope 2 Purchased Electricity", doc1.id, 2025, 1, 1, 2025, 12, 31,
                "pge-acct-84920", "Pacific Gas & Electric"
            ),
            (
                "electricity_purchase", "US-NY", Decimal("3800000"), "kWh", 2,
                "Scope 2 Purchased Electricity", doc1.id, 2025, 1, 1, 2025, 12, 31,
                "coned-acct-11942", "Consolidated Edison"
            ),
            (
                "business_travel_air", "GLO", Decimal("12500000"), "passenger.km", 3,
                "Scope 3.6 Business Travel", doc2.id, 2025, 1, 1, 2025, 12, 31,
                "amex-travel-portal", "American Express Global Business Travel"
            ),
            (
                "freight_road", "GB", Decimal("8500000"), "tonne.km", 3,
                "Scope 3.4 Upstream Transportation", doc2.id, 2025, 1, 1, 2025, 12, 31,
                "dhl-logistics-gb", "DHL Supply Chain"
            ),
            (
                "refrigerant_leakage_r410a", "GLO", Decimal("180"), "kg", 1,
                "Scope 1 Fugitive Emissions", doc1.id, 2025, 1, 1, 2025, 12, 31,
                "carrier-chiller-04", "Carrier Commercial HVAC"
            ),
            # 2024 Baseline Data
            (
                "natural_gas_combustion", "US", Decimal("14500"), "MMBtu", 1,
                "Scope 1 Stationary Combustion", doc1.id, 2024, 1, 1, 2024, 12, 31,
                "facility-gas-meter-01", "Acme Facilities Management"
            ),
            (
                "mobile_combustion_gasoline", "US", Decimal("92000"), "gallons", 1,
                "Scope 1 Mobile Combustion", doc2.id, 2024, 1, 1, 2024, 12, 31,
                "fleet-card-us", "Shell Fleet Services"
            ),
            (
                "electricity_purchase", "US-CA", Decimal("4600000"), "kWh", 2,
                "Scope 2 Purchased Electricity", doc1.id, 2024, 1, 1, 2024, 12, 31,
                "pge-acct-84920", "Pacific Gas & Electric"
            ),
            (
                "business_travel_air", "GLO", Decimal("14000000"), "passenger.km", 3,
                "Scope 3.6 Business Travel", doc2.id, 2024, 1, 1, 2024, 12, 31,
                "amex-travel-portal", "American Express Global Business Travel"
            ),
        ]

        created_calcs = 0
        for (
            act_type, geo, qty, unit, scope, ghg_cat, doc_id,
            s_yr, s_m, s_d, e_yr, e_m, e_d, sup_ref, sup_name
        ) in activities_spec:
            act = ActivityData(
                id=uuid.uuid4(),
                source_document_id=doc_id,
                raw_line_ref=f"LINE-{sup_ref}",
                entity_id=ENTITY_ID,
                activity_type=act_type,
                quantity=qty,
                unit=unit,
                geography=geo,
                period_start=datetime.date(s_yr, s_m, s_d),
                period_end=datetime.date(e_yr, e_m, e_d),
                supplier_ref=sup_ref,
                scope=scope,
                ghg_category=ghg_cat,
                classification_confidence=0.96,
                status="calculated",
            )
            session.add(act)
            await session.flush()

            factor = f_map.get((act_type, geo))
            if factor:
                result = compute_emission(
                    quantity=act.quantity,
                    activity_unit=act.unit,
                    factor_value=factor.factor_value,
                    factor_unit=factor.factor_unit,
                )
                calc = Calculation(
                    id=uuid.uuid4(),
                    activity_data_id=act.id,
                    emission_factor_id=factor.id,
                    formula_applied=result.formula_applied,
                    result_tco2e=result.result_tco2e,
                    computed_by="calc_engine_v1",
                )
                session.add(calc)
                created_calcs += 1

        # 3. Anomaly Flags
        flag1 = AnomalyFlag(
            id=uuid.uuid4(),
            entity_id=ENTITY_ID,
            reporting_period="2025",
            flag_type="YOY_SPIKE",
            severity="WARNING",
            title="Surge in Air Travel Post-Conference Season",
            description="Scope 3.6 Business travel passenger.km increased 14% over Q3 threshold.",
            status="OPEN",
            details_json={
                "metric": "business_travel_air",
                "variance_percentage": 14.2,
                "current_val": 12500000,
                "baseline_val": 14000000,
            },
        )
        flag2 = AnomalyFlag(
            id=uuid.uuid4(),
            entity_id=ENTITY_ID,
            reporting_period="2025",
            flag_type="INTENSITY_OUTLIER",
            severity="INFO",
            title="Facility NY Data Center PUE Variance",
            description=(
                "Normalized emissions intensity within 2.1 standard deviations (within tolerance)."
            ),
            status="CONFIRMED",
            details_json={"z_score": 2.1, "tolerance": 3.0},
            resolution_notes="Auditor verified renewable energy credit REC-84920.",
            resolved_by="lead_esg_auditor@greenlign.com",
            resolved_at=datetime.datetime.now(datetime.UTC),
        )
        session.add_all([flag1, flag2])

        # 4. Supplier Outreach Records
        outreach1 = SupplierOutreach(
            id=uuid.uuid4(),
            entity_id=ENTITY_ID,
            supplier_ref="dhl-logistics-gb",
            supplier_name="DHL Global Forwarding",
            supplier_email="esg-reporting@dhl.com",
            contact_name="Marcus Vance",
            activity_type="freight_road",
            reporting_period="2025",
            status="SENT",
            template_type="ANNUAL_PRIMARY_FACTOR_REQUEST",
            generated_email_subject="Greenlign Scope 3 Primary Request — Acme FY2025",
            generated_email_body=(
                "Dear Marcus Vance,\n\n"
                "As part of Acme Global Corp's Scope 3 emissions accounting for FY2025, "
                "we request primary fuel intensity factors for road freight transport..."
            ),
            response_data_json={},
            sent_at=datetime.datetime.now(datetime.UTC),
        )
        outreach2 = SupplierOutreach(
            id=uuid.uuid4(),
            entity_id=ENTITY_ID,
            supplier_ref="amex-travel-portal",
            supplier_name="American Express GBT",
            supplier_email="carbon-analytics@amexgbt.com",
            contact_name="Sarah Jenkins",
            activity_type="business_travel_air",
            reporting_period="2025",
            status="RECEIVED",
            template_type="ANNUAL_PRIMARY_FACTOR_REQUEST",
            generated_email_subject="Primary Air Travel Fleet Fuel Factor Submission",
            generated_email_body="Primary SAF (Sustainable Aviation Fuel) blend factor submitted.",
            response_data_json={
                "primary_factor": "0.142",
                "unit": "kgCO2e/passenger.km",
                "saf_blend_pct": 12.5,
            },
            sent_at=datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=14),
            responded_at=datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=2),
        )
        session.add_all([outreach1, outreach2])

        await session.commit()
        print(
            f"Successfully seeded Acme Global Corp with {created_calcs} calculations, "
            "2 anomaly flags, and 2 outreach campaigns!"
        )

if __name__ == "__main__":
    asyncio.run(seed_corporate_data())
