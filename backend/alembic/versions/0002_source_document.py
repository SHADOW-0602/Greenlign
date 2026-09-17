"""source_document

Revision ID: 0002_source_document
Revises: 0001_initial_schema
Create Date: 2026-09-17 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002_source_document"
down_revision: str | None = "0001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "source_document",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("file_type", sa.String(length=32), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False),
        sa.Column("file_hash_sha256", sa.String(length=64), nullable=False),
        sa.Column("storage_path", sa.String(length=512), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "metadata_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_source_document_entity_id",
        "source_document",
        ["entity_id"],
        unique=False,
    )
    op.create_index(
        "ix_source_document_file_hash_sha256",
        "source_document",
        ["file_hash_sha256"],
        unique=False,
    )
    op.create_index(
        "ix_source_document_status",
        "source_document",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_source_document_status", table_name="source_document")
    op.drop_index("ix_source_document_file_hash_sha256", table_name="source_document")
    op.drop_index("ix_source_document_entity_id", table_name="source_document")
    op.drop_table("source_document")
