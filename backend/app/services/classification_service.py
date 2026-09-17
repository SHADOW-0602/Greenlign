"""Classification service for automating Scope 1/2/3 assignment and audit trail recording."""

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.ghg_taxonomy import validate_scope_category
from app.core.config import settings
from app.models.activity_data import ActivityData
from app.models.audit_log import AuditLogEntry
from app.services.scope_classifier import ScopeClassifier

logger = logging.getLogger(__name__)


class ClassificationService:
    """Orchestrates activity scope classification, threshold gating, and audit trails."""

    def __init__(
        self,
        classifier: ScopeClassifier | None = None,
        confidence_threshold: float | None = None,
    ) -> None:
        self.classifier = classifier or ScopeClassifier()
        self.confidence_threshold = (
            confidence_threshold
            if confidence_threshold is not None
            else settings.classification_confidence_threshold
        )

    async def classify_activity(
        self,
        session: AsyncSession,
        activity: ActivityData,
    ) -> ActivityData:
        """Classify a single activity row, evaluate confidence gating, and log audit event."""
        res = self.classifier.classify(
            activity_type=activity.activity_type,
            unit=activity.unit,
            raw_line_ref=activity.raw_line_ref,
            supplier_ref=activity.supplier_ref,
        )

        activity.scope = res.scope
        activity.ghg_category = res.ghg_category
        activity.classification_confidence = res.confidence

        if res.confidence >= self.confidence_threshold:
            activity.status = "classified"
        else:
            activity.status = "pending_review"

        audit_entry = AuditLogEntry(
            id=uuid.uuid4(),
            entity_type="ActivityData",
            entity_id=activity.id,
            action="CLASSIFY",
            actor="system:scope_classifier",
            detail={
                "scope": res.scope,
                "ghg_category": res.ghg_category,
                "confidence": res.confidence,
                "status": activity.status,
                "reasoning": res.reasoning,
            },
        )
        session.add(audit_entry)
        await session.commit()
        await session.refresh(activity)

        logger.info(
            "Classified activity %s -> Scope %s (%s, confidence=%.2f, status=%s)",
            activity.id,
            activity.scope,
            activity.ghg_category,
            res.confidence,
            activity.status,
        )
        return activity

    async def batch_classify(
        self,
        session: AsyncSession,
        entity_id: uuid.UUID | None = None,
        document_id: uuid.UUID | None = None,
        limit: int = 100,
    ) -> list[ActivityData]:
        """Batch classify pending activities up to limit, updating records and audit trails."""
        stmt = select(ActivityData).where(
            ActivityData.status.in_(["pending", "pending_review"])
        )
        if entity_id:
            stmt = stmt.where(ActivityData.entity_id == entity_id)
        if document_id:
            stmt = stmt.where(ActivityData.source_document_id == document_id)

        stmt = stmt.limit(limit)
        result = await session.execute(stmt)
        activities = list(result.scalars().all())

        classified: list[ActivityData] = []
        for activity in activities:
            res = self.classifier.classify(
                activity_type=activity.activity_type,
                unit=activity.unit,
                raw_line_ref=activity.raw_line_ref,
                supplier_ref=activity.supplier_ref,
            )
            activity.scope = res.scope
            activity.ghg_category = res.ghg_category
            activity.classification_confidence = res.confidence

            if res.confidence >= self.confidence_threshold:
                activity.status = "classified"
            else:
                activity.status = "pending_review"

            audit = AuditLogEntry(
                id=uuid.uuid4(),
                entity_type="ActivityData",
                entity_id=activity.id,
                action="CLASSIFY",
                actor="system:scope_classifier",
                detail={
                    "scope": res.scope,
                    "ghg_category": res.ghg_category,
                    "confidence": res.confidence,
                    "status": activity.status,
                    "reasoning": res.reasoning,
                },
            )
            session.add(audit)
            classified.append(activity)

        await session.commit()
        for activity in classified:
            await session.refresh(activity)

        return classified

    async def apply_human_review(
        self,
        session: AsyncSession,
        activity_id: uuid.UUID,
        reviewer_id: str,
        scope: int,
        ghg_category: str,
        notes: str | None = None,
    ) -> ActivityData:
        """Apply human review override to an activity row and record audit entry."""
        if not validate_scope_category(scope, ghg_category):
            raise ValueError(
                f"Invalid category '{ghg_category}' for scope {scope}."
            )

        stmt = select(ActivityData).where(ActivityData.id == activity_id)
        result = await session.execute(stmt)
        activity = result.scalar_one_or_none()
        if not activity:
            raise ValueError(f"ActivityData with id {activity_id} not found.")

        old_scope = activity.scope
        old_category = activity.ghg_category
        old_status = activity.status

        activity.scope = scope
        activity.ghg_category = ghg_category
        activity.classification_confidence = 1.0
        activity.status = "classified"

        audit = AuditLogEntry(
            id=uuid.uuid4(),
            entity_type="ActivityData",
            entity_id=activity.id,
            action="CLASSIFY_OVERRIDE",
            actor=f"user:{reviewer_id}",
            detail={
                "old_scope": old_scope,
                "new_scope": scope,
                "old_ghg_category": old_category,
                "new_ghg_category": ghg_category,
                "old_status": old_status,
                "new_status": "classified",
                "notes": notes or "",
            },
        )
        session.add(audit)
        await session.commit()
        await session.refresh(activity)

        logger.info(
            "Reviewer %s overrode activity %s to Scope %s (%s)",
            reviewer_id,
            activity.id,
            scope,
            ghg_category,
        )
        return activity
