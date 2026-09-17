"""Calculation Service.

Orchestrates deterministic emission calculations for activity records:
1. Loads activity and factors from the database.
2. Matches factors using factor_matcher (geographic & temporal fallback).
3. Computes emissions via pure Decimal calc_engine.
4. Writes Calculation database records.
5. Updates ActivityData status to 'computed' or 'pending_factor'.
6. Writes AuditLogEntry records for auditability and compliance.
"""

import logging
import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity_data import ActivityData
from app.models.audit_log import AuditLogEntry
from app.models.calculation import Calculation
from app.models.emission_factor import EmissionFactor
from app.services.calc_engine import IncompatibleUnitError, compute_emission
from app.services.factor_matcher import match_emission_factor

logger = logging.getLogger(__name__)


class CalculationService:
    """Service managing GHG emission calculation workflows."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _get_available_factors(self) -> list[EmissionFactor]:
        """Fetch all emission factors from database."""
        result = await self.session.scalars(select(EmissionFactor))
        return list(result.all())

    async def compute_activity(
        self,
        activity_id: uuid.UUID,
        actor: str = "calc_engine_v1",
    ) -> Calculation | None:
        """Compute emissions for a single ActivityData record."""
        activity = await self.session.get(ActivityData, activity_id)
        if not activity:
            raise ValueError(f"ActivityData with ID {activity_id} not found.")

        factors = await self._get_available_factors()
        match_result = match_emission_factor(
            activity_type=activity.activity_type,
            geography=activity.geography,
            activity_date=activity.period_start,
            available_factors=factors,
        )

        if not match_result.matched or not match_result.factor:
            # Missing factor: explicitly mark activity and record audit log
            activity.status = "pending_factor"
            audit_entry = AuditLogEntry(
                id=uuid.uuid4(),
                entity_type="activity_data",
                entity_id=activity.id,
                action="CALCULATE_FAILED_MISSING_FACTOR",
                actor=actor,
                detail={
                    "reason": match_result.reason,
                    "activity_type": activity.activity_type,
                    "geography": activity.geography,
                    "period_start": str(activity.period_start),
                },
            )
            self.session.add(audit_entry)
            await self.session.commit()
            return None

        factor = match_result.factor

        try:
            calc_result = compute_emission(
                quantity=Decimal(str(activity.quantity)),
                activity_unit=activity.unit,
                factor_value=Decimal(str(factor.factor_value)),
                factor_unit=factor.factor_unit,
            )
        except IncompatibleUnitError as e:
            activity.status = "calculation_error"
            audit_entry = AuditLogEntry(
                id=uuid.uuid4(),
                entity_type="activity_data",
                entity_id=activity.id,
                action="CALCULATE_FAILED_INCOMPATIBLE_UNITS",
                actor=actor,
                detail={
                    "error": str(e),
                    "activity_unit": activity.unit,
                    "factor_unit": factor.factor_unit,
                },
            )
            self.session.add(audit_entry)
            await self.session.commit()
            raise

        # Create calculation record
        calc_record = Calculation(
            id=uuid.uuid4(),
            activity_data_id=activity.id,
            emission_factor_id=factor.id,
            formula_applied=calc_result.formula_applied,
            result_tco2e=calc_result.result_tco2e,
            computed_by=actor,
        )
        self.session.add(calc_record)

        # Update activity status
        activity.status = "computed"

        # Create audit log entry
        audit_entry = AuditLogEntry(
            id=uuid.uuid4(),
            entity_type="activity_data",
            entity_id=activity.id,
            action="CALCULATE",
            actor=actor,
            detail={
                "calculation_id": str(calc_record.id),
                "emission_factor_id": str(factor.id),
                "factor_source": factor.source,
                "factor_version": factor.source_version,
                "fallback_level": match_result.fallback_level,
                "formula_applied": calc_result.formula_applied,
                "result_tco2e": str(calc_result.result_tco2e),
            },
        )
        self.session.add(audit_entry)

        await self.session.commit()
        await self.session.refresh(calc_record)
        return calc_record

    async def compute_document_activities(
        self,
        source_document_id: uuid.UUID,
        actor: str = "celery_worker",
    ) -> dict[str, list[dict[str, Any]]]:
        """Compute emissions for all activities belonging to a source document."""
        query = select(ActivityData).where(
            ActivityData.source_document_id == source_document_id
        )
        result = await self.session.scalars(query)
        activities = list(result.all())

        summary: dict[str, list[dict[str, Any]]] = {
            "computed": [],
            "pending_factor": [],
            "errors": [],
        }

        for act in activities:
            try:
                calc = await self.compute_activity(act.id, actor=actor)
                if calc:
                    summary["computed"].append({
                        "activity_id": str(act.id),
                        "calculation_id": str(calc.id),
                        "result_tco2e": str(calc.result_tco2e),
                    })
                else:
                    summary["pending_factor"].append({
                        "activity_id": str(act.id),
                        "activity_type": act.activity_type,
                    })
            except Exception as exc:
                logger.exception(f"Error computing activity {act.id}: {exc}")
                summary["errors"].append({
                    "activity_id": str(act.id),
                    "error": str(exc),
                })

        return summary
