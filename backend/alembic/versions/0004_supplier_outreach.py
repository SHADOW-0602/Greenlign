"""supplier_outreach

Revision ID: 0004_supplier_outreach
Revises: 0003_anomaly_flag
Create Date: 2026-09-18 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0004_supplier_outreach"
down_revision: str | None = "0003_anomaly_flag"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "supplier_outreach",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("supplier_ref", sa.String(length=128), nullable=False),
        sa.Column("supplier_name", sa.String(length=255), nullable=True),
        sa.Column("supplier_email", sa.String(length=255), nullable=False),
        sa.Column("contact_name", sa.String(length=255), nullable=False),
        sa.Column("activity_type", sa.String(length=128), nullable=False),
        sa.Column("reporting_period", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("template_type", sa.String(length=64), nullable=False),
        sa.Column("generated_email_subject", sa.String(length=512), nullable=False),
        sa.Column("generated_email_body", sa.Text(), nullable=False),
        sa.Column(
            "response_data_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_supplier_outreach_entity_id",
        "supplier_outreach",
        ["entity_id"],
        unique=False,
    )
    op.create_index(
        "ix_supplier_outreach_supplier_ref",
        "supplier_outreach",
        ["supplier_ref"],
        unique=False,
    )
    op.create_index(
        "ix_supplier_outreach_reporting_period",
        "supplier_outreach",
        ["reporting_period"],
        unique=False,
    )
    op.create_index(
        "ix_supplier_outreach_status",
        "supplier_outreach",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_supplier_outreach_status", table_name="supplier_outreach")
    op.drop_index("ix_supplier_outreach_reporting_period", table_name="supplier_outreach")
    op.drop_index("ix_supplier_outreach_supplier_ref", table_name="supplier_outreach")
    op.drop_index("ix_supplier_outreach_entity_id", table_name="supplier_outreach")
    op.drop_table("supplier_outreach")
