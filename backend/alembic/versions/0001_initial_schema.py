"""initial_schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-09-17 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "activity_data",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_document_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("raw_line_ref", sa.String(length=255), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("activity_type", sa.String(length=128), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=20, scale=6), nullable=False),
        sa.Column("unit", sa.String(length=64), nullable=False),
        sa.Column("geography", sa.String(length=16), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("supplier_ref", sa.String(length=255), nullable=False),
        sa.Column("scope", sa.Integer(), nullable=True),
        sa.Column("ghg_category", sa.String(length=128), nullable=True),
        sa.Column("classification_confidence", sa.Float(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_activity_data_activity_type",
        "activity_data",
        ["activity_type"],
        unique=False,
    )
    op.create_index(
        "ix_activity_data_entity_id",
        "activity_data",
        ["entity_id"],
        unique=False,
    )
    op.create_index(
        "ix_activity_data_geography",
        "activity_data",
        ["geography"],
        unique=False,
    )
    op.create_index(
        "ix_activity_data_source_document_id",
        "activity_data",
        ["source_document_id"],
        unique=False,
    )
    op.create_index(
        "ix_activity_data_status",
        "activity_data",
        ["status"],
        unique=False,
    )

    op.create_table(
        "emission_factor",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("source_version", sa.String(length=32), nullable=False),
        sa.Column("activity_type", sa.String(length=128), nullable=False),
        sa.Column("geography", sa.String(length=16), nullable=False),
        sa.Column("unit", sa.String(length=64), nullable=False),
        sa.Column("factor_value", sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column("factor_unit", sa.String(length=64), nullable=False),
        sa.Column("published_date", sa.Date(), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_emission_factor_activity_type",
        "emission_factor",
        ["activity_type"],
        unique=False,
    )
    op.create_index(
        "ix_emission_factor_effective_from",
        "emission_factor",
        ["effective_from"],
        unique=False,
    )
    op.create_index(
        "ix_emission_factor_geography",
        "emission_factor",
        ["geography"],
        unique=False,
    )
    op.create_index(
        "ix_emission_factor_source",
        "emission_factor",
        ["source"],
        unique=False,
    )

    op.create_table(
        "calculation",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("activity_data_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("emission_factor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("formula_applied", sa.Text(), nullable=False),
        sa.Column("result_tco2e", sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column("computed_by", sa.String(length=64), nullable=False),
        sa.Column(
            "computed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["activity_data_id"],
            ["activity_data.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["emission_factor_id"],
            ["emission_factor.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_calculation_activity_data_id",
        "calculation",
        ["activity_data_id"],
        unique=False,
    )
    op.create_index(
        "ix_calculation_emission_factor_id",
        "calculation",
        ["emission_factor_id"],
        unique=False,
    )

    op.create_table(
        "audit_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("actor", sa.String(length=128), nullable=False),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "detail",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_audit_log_action",
        "audit_log",
        ["action"],
        unique=False,
    )
    op.create_index(
        "ix_audit_log_entity_id",
        "audit_log",
        ["entity_id"],
        unique=False,
    )
    op.create_index(
        "ix_audit_log_entity_type",
        "audit_log",
        ["entity_type"],
        unique=False,
    )

    op.create_table(
        "disclosure",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("framework", sa.String(length=64), nullable=False),
        sa.Column("reporting_period", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("generated_document_ref", sa.Text(), nullable=True),
        sa.Column(
            "line_item_refs",
            postgresql.ARRAY(postgresql.UUID(as_uuid=True)),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_disclosure_entity_id",
        "disclosure",
        ["entity_id"],
        unique=False,
    )
    op.create_index(
        "ix_disclosure_framework",
        "disclosure",
        ["framework"],
        unique=False,
    )
    op.create_index(
        "ix_disclosure_status",
        "disclosure",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_disclosure_status", table_name="disclosure")
    op.drop_index("ix_disclosure_framework", table_name="disclosure")
    op.drop_index("ix_disclosure_entity_id", table_name="disclosure")
    op.drop_table("disclosure")

    op.drop_index("ix_audit_log_entity_type", table_name="audit_log")
    op.drop_index("ix_audit_log_entity_id", table_name="audit_log")
    op.drop_index("ix_audit_log_action", table_name="audit_log")
    op.drop_table("audit_log")

    op.drop_index("ix_calculation_emission_factor_id", table_name="calculation")
    op.drop_index("ix_calculation_activity_data_id", table_name="calculation")
    op.drop_table("calculation")

    op.drop_index("ix_emission_factor_source", table_name="emission_factor")
    op.drop_index("ix_emission_factor_geography", table_name="emission_factor")
    op.drop_index("ix_emission_factor_effective_from", table_name="emission_factor")
    op.drop_index("ix_emission_factor_activity_type", table_name="emission_factor")
    op.drop_table("emission_factor")

    op.drop_index("ix_activity_data_status", table_name="activity_data")
    op.drop_index("ix_activity_data_source_document_id", table_name="activity_data")
    op.drop_index("ix_activity_data_geography", table_name="activity_data")
    op.drop_index("ix_activity_data_entity_id", table_name="activity_data")
    op.drop_index("ix_activity_data_activity_type", table_name="activity_data")
    op.drop_table("activity_data")
