"""anomaly_flag

Revision ID: 0003_anomaly_flag
Revises: 0002_source_document
Create Date: 2026-09-17 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003_anomaly_flag"
down_revision: str | None = "0002_source_document"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "anomaly_flag",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reporting_period", sa.String(length=32), nullable=False),
        sa.Column("flag_type", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column(
            "details_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("resolution_notes", sa.Text(), nullable=True),
        sa.Column("resolved_by", sa.String(length=128), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_anomaly_flag_entity_id",
        "anomaly_flag",
        ["entity_id"],
        unique=False,
    )
    op.create_index(
        "ix_anomaly_flag_reporting_period",
        "anomaly_flag",
        ["reporting_period"],
        unique=False,
    )
    op.create_index(
        "ix_anomaly_flag_flag_type",
        "anomaly_flag",
        ["flag_type"],
        unique=False,
    )
    op.create_index(
        "ix_anomaly_flag_status",
        "anomaly_flag",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_anomaly_flag_status", table_name="anomaly_flag")
    op.drop_index("ix_anomaly_flag_flag_type", table_name="anomaly_flag")
    op.drop_index("ix_anomaly_flag_reporting_period", table_name="anomaly_flag")
    op.drop_index("ix_anomaly_flag_entity_id", table_name="anomaly_flag")
    op.drop_table("anomaly_flag")
