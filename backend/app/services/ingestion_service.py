"""Ingestion Orchestration Service.

Coordinates file storage, parsing (CSV/XLSX/PDF), PII tokenization,
ActivityData generation, and AuditLogEntry creation.
"""

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity_data import ActivityData
from app.models.audit_log import AuditLogEntry
from app.models.source_document import SourceDocument
from app.services.pdf_parser import ParsedPDFActivityItem, PDFParser
from app.services.storage_service import StorageService
from app.services.tabular_parser import ParsedActivityRow, TabularParser


class IngestionError(Exception):
    """Base exception for ingestion pipeline errors."""


class UnsupportedFileTypeError(IngestionError):
    """Raised when file extension or MIME type is not supported."""


class IngestionService:
    """Orchestrates source document ingestion and normalization into ActivityData."""

    SUPPORTED_EXTENSIONS = {
        ".csv": "csv",
        ".xlsx": "xlsx",
        ".pdf": "pdf",
    }

    def __init__(self, storage_service: StorageService | None = None) -> None:
        self.storage = storage_service or StorageService()
        self.tabular_parser = TabularParser()
        self.pdf_parser = PDFParser()

    @classmethod
    def detect_file_type(cls, filename: str, explicit_type: str | None = None) -> str:
        """Derive normalized file type from explicit argument or filename extension."""
        if explicit_type:
            cleaned = explicit_type.strip().lower().lstrip(".")
            if cleaned in {"csv", "xlsx", "pdf"}:
                return cleaned
        ext = Path(filename).suffix.lower()
        if ext in cls.SUPPORTED_EXTENSIONS:
            return cls.SUPPORTED_EXTENSIONS[ext]
        raise UnsupportedFileTypeError(
            f"Unsupported file type for '{filename}'. Must be one of: .csv, .xlsx, .pdf"
        )

    async def ingest_document(
        self,
        session: AsyncSession,
        entity_id: uuid.UUID,
        filename: str,
        content: bytes,
        file_type: str | None = None,
        column_mapping: dict[str, str] | None = None,
    ) -> SourceDocument:
        """Save file to storage and insert a pending SourceDocument database record."""
        resolved_file_type = self.detect_file_type(filename, file_type)
        file_hash = self.storage.compute_sha256(content)
        storage_path = self.storage.generate_storage_path(entity_id, file_hash, filename)

        # Upload file bytes to object storage
        content_type = (
            "text/csv"
            if resolved_file_type == "csv"
            else "application/pdf"
            if resolved_file_type == "pdf"
            else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        self.storage.upload_bytes(content, storage_path, content_type=content_type)

        # Build metadata payload
        metadata: dict[str, Any] = {}
        if column_mapping:
            metadata["column_mapping"] = column_mapping

        source_doc = SourceDocument(
            id=uuid.uuid4(),
            entity_id=entity_id,
            filename=filename,
            file_type=resolved_file_type,
            file_size_bytes=len(content),
            file_hash_sha256=file_hash,
            storage_path=storage_path,
            status="pending",
            metadata_json=metadata,
        )

        session.add(source_doc)
        await session.commit()
        await session.refresh(source_doc)
        return source_doc

    async def process_document(
        self,
        session: AsyncSession,
        source_document_id: uuid.UUID,
    ) -> list[ActivityData]:
        """Download raw file, parse line items, and persist ActivityData rows."""
        result = await session.execute(
            select(SourceDocument).where(SourceDocument.id == source_document_id)
        )
        source_doc = result.scalar_one_or_none()
        if not source_doc:
            raise IngestionError(f"SourceDocument with ID {source_document_id} not found.")

        # Update status to processing
        source_doc.status = "processing"
        await session.commit()

        try:
            content = self.storage.download_bytes(source_doc.storage_path)
            mapping = source_doc.metadata_json.get("column_mapping")

            parsed_items: list[ParsedActivityRow] | list[ParsedPDFActivityItem]
            if source_doc.file_type == "csv":
                parsed_items = self.tabular_parser.parse_csv(content, mapping=mapping)
            elif source_doc.file_type == "xlsx":
                parsed_items = self.tabular_parser.parse_xlsx(content, mapping=mapping)
            elif source_doc.file_type == "pdf":
                parsed_items = self.pdf_parser.parse_utility_pdf(content)
            else:
                raise UnsupportedFileTypeError(f"Cannot process type: {source_doc.file_type}")

            created_activities: list[ActivityData] = []
            for item in parsed_items:
                activity = ActivityData(
                    id=uuid.uuid4(),
                    source_document_id=source_doc.id,
                    raw_line_ref=item.raw_line_ref,
                    entity_id=source_doc.entity_id,
                    activity_type=item.activity_type,
                    quantity=Decimal(str(item.quantity)),
                    unit=item.unit,
                    geography=item.geography,
                    period_start=item.period_start,
                    period_end=item.period_end,
                    supplier_ref=item.supplier_ref,
                    status="pending_review",
                )
                session.add(activity)
                created_activities.append(activity)

            # Record AuditLogEntry
            audit_entry = AuditLogEntry(
                id=uuid.uuid4(),
                entity_id=source_doc.entity_id,
                entity_type="source_document",
                action="ingest_and_parse",
                actor="ingestion_pipeline",
                detail={
                    "source_document_id": str(source_doc.id),
                    "filename": source_doc.filename,
                    "file_type": source_doc.file_type,
                    "rows_created": len(created_activities),
                },
            )
            session.add(audit_entry)

            # Update SourceDocument status to completed
            source_doc.status = "completed"
            source_doc.processed_at = datetime.now(UTC)
            updated_meta = dict(source_doc.metadata_json)
            updated_meta["rows_created"] = len(created_activities)
            source_doc.metadata_json = updated_meta

            await session.commit()
            return created_activities

        except Exception as exc:
            await session.rollback()
            # Mark document as failed
            source_doc.status = "failed"
            source_doc.error_message = str(exc)
            source_doc.processed_at = datetime.now(UTC)
            session.add(source_doc)
            await session.commit()
            raise

    async def ingest_and_process_document(
        self,
        session: AsyncSession,
        entity_id: uuid.UUID,
        filename: str,
        content: bytes,
        file_type: str | None = None,
        column_mapping: dict[str, str] | None = None,
    ) -> tuple[SourceDocument, list[ActivityData]]:
        """Convenience method for synchronous ingest and immediate processing."""
        source_doc = await self.ingest_document(
            session=session,
            entity_id=entity_id,
            filename=filename,
            content=content,
            file_type=file_type,
            column_mapping=column_mapping,
        )
        activities = await self.process_document(session=session, source_document_id=source_doc.id)
        return source_doc, activities
