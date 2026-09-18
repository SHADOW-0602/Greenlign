"""Scope 3 Supplier Outreach Agent Service.

Identifies upstream and downstream Scope 3 categories reliant on generic secondary
factors, drafts tailored primary data collection inquiries using Groq LLM
(with deterministic fallback templates), and tracks supplier responses.
"""

import json
import logging
from collections import defaultdict
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from groq import Groq
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.activity_data import ActivityData
from app.models.audit_log import AuditLogEntry
from app.models.calculation import Calculation
from app.models.emission_factor import EmissionFactor
from app.models.supplier_outreach import SupplierOutreach
from app.schemas.outreach import (
    CreateOutreachRequest,
    GenerateEmailRequest,
    GenerateEmailResponse,
    MissingScope3SupplierItem,
    RecordSupplierResponseRequest,
)

logger = logging.getLogger(__name__)


class SupplierOutreachService:
    """Agent service managing Scope 3 primary data requests and supplier communication."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def generate_email(self, request: GenerateEmailRequest) -> GenerateEmailResponse:
        """Draft a formal ESG inquiry using Groq API or deterministic fallback."""
        if settings.groq_api_key:
            try:
                client = Groq(api_key=settings.groq_api_key)
                prompt = (
                    "You are a sustainability and carbon accounting director at a corporation.\n"
                    "Draft a polite, professional, and clear supplier inquiry email for "
                    "Scope 3 greenhouse gas data.\n"
                    f"Supplier: {request.supplier_name} (Ref: {request.supplier_ref})\n"
                    f"Procured Activity / Goods: {request.activity_type}\n"
                    f"Reporting Period: FY{request.reporting_period}\n"
                    f"Request Objective: {request.template_type}\n\n"
                    "Return ONLY valid JSON with keys 'subject' and 'body'. "
                    "No markdown formatting or extra text."
                )
                response = client.chat.completions.create(
                    model=settings.groq_model,
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "You generate structured enterprise ESG correspondence in JSON. "
                                'Output must be JSON: {"subject": "...", "body": "..."}.'
                            ),
                        },
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.3,
                    response_format={"type": "json_object"},
                )
                content = response.choices[0].message.content or "{}"
                data = json.loads(content)
                if "subject" in data and "body" in data:
                    return GenerateEmailResponse(
                        template_type=request.template_type,
                        subject=data["subject"].strip(),
                        body=data["body"].strip(),
                    )
            except Exception as e:
                logger.warning(
                    "Groq email generation failed, falling back to deterministic template: %s",
                    e,
                )

        return self._generate_heuristic_email(request)

    def _generate_heuristic_email(self, request: GenerateEmailRequest) -> GenerateEmailResponse:
        """Deterministic professional email template fallback."""
        if request.template_type == "ACTIVITY_DATA_VERIFICATION":
            subject = (
                f"Verification Request: FY{request.reporting_period} Consumption Data — "
                f"{request.supplier_name}"
            )
            body = (
                f"Dear ESG & Sustainability Team at {request.supplier_name},\n\n"
                f"As part of our annual GHG inventory for FY{request.reporting_period}, "
                f"we are auditing our supply chain records for '{request.activity_type}'.\n\n"
                "Could you please review and confirm the total billed quantities delivered to us "
                "during this period? If any discrepancies are identified, please share your "
                "reconciled figures at your earliest convenience.\n\n"
                "Thank you for your partnership in our decarbonization commitments.\n\n"
                "Sincerely,\nCorporate Sustainability Department"
            )
        elif request.template_type == "REDUCTION_PLEDGE":
            subject = (
                f"Supply Chain Climate Engagement: FY{request.reporting_period} Decarbonization "
                f"Targets — {request.supplier_name}"
            )
            body = (
                f"Dear {request.supplier_name} Leadership,\n\n"
                "In alignment with our Science-Based Targets initiative (SBTi) and statutory "
                f"Scope 3 requirements, we are engaging key partners in '{request.activity_type}' "
                "to track emissions reduction roadmaps.\n\n"
                "Please inform us if your organization has set a formal emissions reduction target "
                "(e.g. net zero, renewable energy pledge) and any progress made during "
                f"FY{request.reporting_period}.\n\n"
                "Warm regards,\nCorporate Sustainability Department"
            )
        else:
            # PRIMARY_EMISSION_FACTOR
            subject = (
                f"Inquiry: FY{request.reporting_period} Product Carbon Intensity Data — "
                f"{request.supplier_name}"
            )
            body = (
                f"Dear {request.supplier_name} Sustainability Team,\n\n"
                f"Our organization is currently compiling its FY{request.reporting_period} "
                "corporate greenhouse gas inventory. In order to move from industry-average "
                "secondary estimates to accurate supplier-specific accounting for "
                f"'{request.activity_type}', we are requesting your primary product carbon "
                "footprint or facility emissions intensity (e.g., kg CO2e per kg or unit).\n\n"
                "If an Environmental Product Declaration (EPD) or ISO 14064 verification report "
                "is available, please share a copy or provide the verified emission factor.\n\n"
                "We appreciate your assistance in ensuring compliance with California SB 253 "
                "and CSRD disclosure mandates.\n\n"
                "Best regards,\nCorporate Procurement & Sustainability Team"
            )

        return GenerateEmailResponse(
            template_type=request.template_type,
            subject=subject,
            body=body,
        )

    async def find_missing_scope3_suppliers(
        self, entity_id: UUID, reporting_period: str
    ) -> list[MissingScope3SupplierItem]:
        """Find Scope 3 activity lines that currently rely on secondary proxy emission factors."""
        query = (
            select(Calculation, ActivityData, EmissionFactor)
            .join(ActivityData, Calculation.activity_data_id == ActivityData.id)
            .join(EmissionFactor, Calculation.emission_factor_id == EmissionFactor.id)
            .where(
                ActivityData.entity_id == entity_id,
                ActivityData.scope == 3,
            )
        )
        res = await self.session.execute(query)
        rows = list(res.all())

        # Group by supplier_ref and activity_type
        aggregated: dict[tuple[str, str], dict[str, Any]] = defaultdict(
            lambda: {
                "tco2e": Decimal("0"),
                "count": 0,
                "factor_source": "Secondary / Industry Proxy",
            }
        )

        for calc, act, factor in rows:
            start_year = str(act.period_start.year)
            valid_periods = (
                start_year,
                f"{start_year}-Q1",
                f"{start_year}-Q2",
                f"{start_year}-Q3",
                f"{start_year}-Q4",
            )
            if reporting_period in valid_periods or reporting_period == start_year:
                key = (act.supplier_ref, act.activity_type)
                aggregated[key]["tco2e"] += calc.result_tco2e
                aggregated[key]["count"] += 1
                aggregated[key]["factor_source"] = factor.source

        items: list[MissingScope3SupplierItem] = []
        for (supp_ref, act_type), data in aggregated.items():
            items.append(
                MissingScope3SupplierItem(
                    supplier_ref=supp_ref,
                    activity_type=act_type,
                    reporting_period=reporting_period,
                    current_factor_source=data["factor_source"],
                    estimated_tco2e=float(data["tco2e"]),
                    line_item_count=data["count"],
                )
            )

        # Sort by highest emissions contribution first
        items.sort(key=lambda x: x.estimated_tco2e, reverse=True)
        return items

    async def create_outreach(self, request: CreateOutreachRequest) -> SupplierOutreach:
        """Create and persist a new supplier outreach communication record."""
        subject = request.custom_subject
        body = request.custom_body

        if not subject or not body:
            email_data = await self.generate_email(
                GenerateEmailRequest(
                    supplier_name=request.supplier_name or request.supplier_ref,
                    supplier_ref=request.supplier_ref,
                    activity_type=request.activity_type,
                    reporting_period=request.reporting_period,
                    template_type=request.template_type,
                )
            )
            subject = subject or email_data.subject
            body = body or email_data.body

        outreach = SupplierOutreach(
            entity_id=request.entity_id,
            supplier_ref=request.supplier_ref,
            supplier_name=request.supplier_name,
            supplier_email=request.supplier_email,
            contact_name=request.contact_name,
            activity_type=request.activity_type,
            reporting_period=request.reporting_period,
            status="DRAFT",
            template_type=request.template_type,
            generated_email_subject=subject,
            generated_email_body=body,
            response_data_json={},
        )
        self.session.add(outreach)
        await self.session.flush()

        audit = AuditLogEntry(
            entity_type="supplier_outreach",
            entity_id=outreach.id,
            action="CREATE_SUPPLIER_OUTREACH",
            actor="outreach_agent",
            detail={
                "supplier_ref": request.supplier_ref,
                "supplier_email": request.supplier_email,
                "template_type": request.template_type,
            },
        )
        self.session.add(audit)
        await self.session.commit()
        await self.session.refresh(outreach)
        return outreach

    async def send_outreach(self, outreach_id: UUID) -> SupplierOutreach:
        """Mark an outreach communication as dispatched."""
        stmt = select(SupplierOutreach).where(SupplierOutreach.id == outreach_id)
        res = await self.session.execute(stmt)
        outreach = res.scalar_one_or_none()
        if not outreach:
            raise ValueError(f"Supplier outreach record {outreach_id} not found.")

        outreach.status = "SENT"
        outreach.sent_at = datetime.now(UTC)

        audit = AuditLogEntry(
            entity_type="supplier_outreach",
            entity_id=outreach.id,
            action="DISPATCH_SUPPLIER_OUTREACH",
            actor="outreach_agent",
            detail={"sent_at": outreach.sent_at.isoformat()},
        )
        self.session.add(audit)
        await self.session.commit()
        await self.session.refresh(outreach)
        return outreach

    async def record_response(
        self, outreach_id: UUID, request: RecordSupplierResponseRequest
    ) -> SupplierOutreach:
        """Record primary supplier emissions intensity data and responses."""
        stmt = select(SupplierOutreach).where(SupplierOutreach.id == outreach_id)
        res = await self.session.execute(stmt)
        outreach = res.scalar_one_or_none()
        if not outreach:
            raise ValueError(f"Supplier outreach record {outreach_id} not found.")

        outreach.status = "RECEIVED"
        outreach.responded_at = datetime.now(UTC)
        outreach.response_data_json = {
            "primary_factor_value": request.primary_factor_value,
            "primary_factor_unit": request.primary_factor_unit,
            "verified_quantity": request.verified_quantity,
            "response_notes": request.response_notes,
            "recorded_at": outreach.responded_at.isoformat(),
        }

        audit = AuditLogEntry(
            entity_type="supplier_outreach",
            entity_id=outreach.id,
            action="RECORD_SUPPLIER_PRIMARY_DATA",
            actor="outreach_agent",
            detail=outreach.response_data_json,
        )
        self.session.add(audit)
        await self.session.commit()
        await self.session.refresh(outreach)
        return outreach

    async def list_outreach(
        self, entity_id: UUID, status: str | None = None
    ) -> list[SupplierOutreach]:
        """List outreach campaigns for an entity with optional status filter."""
        stmt = select(SupplierOutreach).where(SupplierOutreach.entity_id == entity_id)
        if status:
            stmt = stmt.where(SupplierOutreach.status == status)
        stmt = stmt.order_by(SupplierOutreach.created_at.desc())
        res = await self.session.execute(stmt)
        return list(res.scalars().all())
