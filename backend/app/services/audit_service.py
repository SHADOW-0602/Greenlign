"""Audit and Governance Service.

Constructs complete provenance chains:
Source Document -> Activity -> Factor -> Calculation -> Audit History.
Strictly guards referential integrity against deletion of calculation
or emission factor records referenced by Disclosures.
"""

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity_data import ActivityData
from app.models.audit_log import AuditLogEntry
from app.models.calculation import Calculation
from app.models.disclosure import Disclosure
from app.models.emission_factor import EmissionFactor
from app.models.source_document import SourceDocument
from app.schemas.audit import (
    AuditActivityDataSummary,
    AuditCalculationSummary,
    AuditDisclosureSummary,
    AuditEmissionFactorSummary,
    AuditLogEntryResponse,
    AuditSourceDocumentSummary,
    AuditTraceResponse,
    ReferentialIntegrityCheckResponse,
)

logger = logging.getLogger(__name__)


class ReferentialIntegrityError(Exception):
    """Raised when an operation would violate audit ledger referential integrity."""


class AuditService:
    """Service providing audit trails, provenance graphs, and referential guards."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_calculation_trace(self, calculation_id: uuid.UUID) -> AuditTraceResponse:
        """Construct the complete provenance chain for a given calculation.

        Returns:
            AuditTraceResponse with calculation, activity, source_document, factor,
            audit events, and linked disclosures.
        Raises:
            ValueError: If calculation with calculation_id does not exist.
        """
        # Fetch calculation
        calc = await self.session.get(Calculation, calculation_id)
        if not calc:
            raise ValueError(f"Calculation with ID '{calculation_id}' not found.")

        # Fetch activity
        activity = await self.session.get(ActivityData, calc.activity_data_id)
        if not activity:
            raise ValueError(f"Underlying ActivityData '{calc.activity_data_id}' not found.")

        # Fetch emission factor
        factor = await self.session.get(EmissionFactor, calc.emission_factor_id)
        if not factor:
            raise ValueError(f"Underlying EmissionFactor '{calc.emission_factor_id}' not found.")

        # Fetch source document if present
        source_doc: SourceDocument | None = None
        if activity.source_document_id:
            source_doc = await self.session.get(SourceDocument, activity.source_document_id)

        # Fetch audit events tied to activity, calculation, or source document
        entity_ids = [activity.id, calc.id]
        if source_doc:
            entity_ids.append(source_doc.id)

        audit_query = (
            select(AuditLogEntry)
            .where(AuditLogEntry.entity_id.in_(entity_ids))
            .order_by(AuditLogEntry.timestamp.asc())
        )
        audit_res = await self.session.scalars(audit_query)
        audit_entries = list(audit_res.all())

        # Fetch linked disclosures that reference this calculation
        disc_query = select(Disclosure)
        disc_res = await self.session.scalars(disc_query)
        all_disclosures = list(disc_res.all())

        linked_disclosures = [
            AuditDisclosureSummary.model_validate(d)
            for d in all_disclosures
            if self._is_calculation_in_disclosure(calculation_id, d)
        ]

        return AuditTraceResponse(
            calculation=AuditCalculationSummary.model_validate(calc),
            activity=AuditActivityDataSummary.model_validate(activity),
            source_document=(
                AuditSourceDocumentSummary.model_validate(source_doc) if source_doc else None
            ),
            emission_factor=AuditEmissionFactorSummary.model_validate(factor),
            audit_events=[AuditLogEntryResponse.model_validate(e) for e in audit_entries],
            linked_disclosures=linked_disclosures,
        )

    @staticmethod
    def _is_calculation_in_disclosure(
        calculation_id: uuid.UUID,
        disclosure: Disclosure,
    ) -> bool:
        refs = disclosure.line_item_refs
        if not refs:
            return False
        if isinstance(refs, str):
            try:
                import json
                refs = json.loads(refs)
            except Exception:
                return str(calculation_id) in refs
        calc_id_str = str(calculation_id)
        return any(str(r) == calc_id_str for r in refs)

    async def check_calculation_deletable(
        self, calculation_id: uuid.UUID
    ) -> ReferentialIntegrityCheckResponse:
        """Verify whether a calculation is referenced by any disclosure."""
        disc_query = select(Disclosure)
        disc_res = await self.session.scalars(disc_query)
        all_disclosures = list(disc_res.all())

        blocking_ids = [
            d.id for d in all_disclosures if self._is_calculation_in_disclosure(calculation_id, d)
        ]

        if blocking_ids:
            return ReferentialIntegrityCheckResponse(
                can_delete=False,
                reason=(
                    f"Calculation '{calculation_id}' is referenced by {len(blocking_ids)} "
                    f"regulatory disclosure(s) and cannot be deleted."
                ),
                blocking_disclosures=blocking_ids,
            )

        return ReferentialIntegrityCheckResponse(can_delete=True)

    async def delete_calculation_guarded(
        self,
        calculation_id: uuid.UUID,
        actor: str = "auditor",
    ) -> None:
        """Delete calculation record only if not referenced in any disclosure."""
        calc = await self.session.get(Calculation, calculation_id)
        if not calc:
            raise ValueError(f"Calculation with ID '{calculation_id}' not found.")

        check = await self.check_calculation_deletable(calculation_id)
        if not check.can_delete:
            raise ReferentialIntegrityError(check.reason)

        # Log audit entry prior to deletion
        audit_entry = AuditLogEntry(
            id=uuid.uuid4(),
            entity_type="calculation",
            entity_id=calculation_id,
            action="CALCULATION_DELETED",
            actor=actor,
            detail={
                "deleted_calculation_id": str(calculation_id),
                "result_tco2e": str(calc.result_tco2e),
                "activity_data_id": str(calc.activity_data_id),
            },
        )
        self.session.add(audit_entry)
        await self.session.delete(calc)
        await self.session.commit()

    async def check_factor_deletable(
        self, factor_id: uuid.UUID
    ) -> ReferentialIntegrityCheckResponse:
        """Verify whether an emission factor is referenced by any calculation."""
        calc_query = select(Calculation.id).where(Calculation.emission_factor_id == factor_id)
        calc_res = await self.session.scalars(calc_query)
        calcs = list(calc_res.all())

        if calcs:
            return ReferentialIntegrityCheckResponse(
                can_delete=False,
                reason=(
                    f"EmissionFactor '{factor_id}' is referenced by {len(calcs)} "
                    f"calculation(s) in the audit ledger and cannot be deleted."
                ),
            )

        return ReferentialIntegrityCheckResponse(can_delete=True)

    async def delete_emission_factor_guarded(
        self,
        factor_id: uuid.UUID,
        actor: str = "auditor",
    ) -> None:
        """Delete emission factor only if not referenced in any calculation."""
        factor = await self.session.get(EmissionFactor, factor_id)
        if not factor:
            raise ValueError(f"EmissionFactor with ID '{factor_id}' not found.")

        check = await self.check_factor_deletable(factor_id)
        if not check.can_delete:
            raise ReferentialIntegrityError(check.reason)

        audit_entry = AuditLogEntry(
            id=uuid.uuid4(),
            entity_type="emission_factor",
            entity_id=factor_id,
            action="EMISSION_FACTOR_DELETED",
            actor=actor,
            detail={
                "deleted_factor_id": str(factor_id),
                "source": factor.source,
                "activity_type": factor.activity_type,
            },
        )
        self.session.add(audit_entry)
        await self.session.delete(factor)
        await self.session.commit()

    async def list_audit_logs(
        self,
        entity_id: uuid.UUID | None = None,
        entity_type: str | None = None,
        action: str | None = None,
        actor: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AuditLogEntry]:
        """Query audit log entries with optional filtering."""
        query = select(AuditLogEntry).order_by(AuditLogEntry.timestamp.desc())

        if entity_id:
            query = query.where(AuditLogEntry.entity_id == entity_id)
        if entity_type:
            query = query.where(AuditLogEntry.entity_type == entity_type)
        if action:
            query = query.where(AuditLogEntry.action == action)
        if actor:
            query = query.where(AuditLogEntry.actor == actor)

        query = query.offset(offset).limit(limit)
        result = await self.session.scalars(query)
        return list(result.all())
