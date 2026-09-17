"""Smoke tests for Alembic migration configuration and revision directory."""
import contextlib
import io
import os
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory


def _get_alembic_config() -> Config:
    """Helper to locate alembic.ini relative to backend root."""
    backend_dir = Path(__file__).resolve().parent.parent
    ini_path = backend_dir / "alembic.ini"
    assert ini_path.exists(), f"alembic.ini not found at {ini_path}"
    return Config(str(ini_path))


def test_alembic_config_loadable():
    """Verify alembic configuration can be loaded from alembic.ini."""
    config = _get_alembic_config()
    script_location = config.get_main_option("script_location")
    assert script_location == "alembic"

    sqlalchemy_url = config.get_main_option("sqlalchemy.url")
    assert sqlalchemy_url is not None
    assert "driver://user:pass@host/dbname" in sqlalchemy_url


def test_script_directory_contains_initial_migration():
    """Verify migration script directory contains the initial migration and subsequent revisions."""
    config = _get_alembic_config()
    script_dir = ScriptDirectory.from_config(config)

    revisions = {rev.revision: rev for rev in script_dir.walk_revisions()}
    assert "0001_initial_schema" in revisions
    assert revisions["0001_initial_schema"].down_revision is None
    assert "0002_source_document" in revisions
    assert revisions["0002_source_document"].down_revision == "0001_initial_schema"
    assert "0003_anomaly_flag" in revisions
    assert revisions["0003_anomaly_flag"].down_revision == "0002_source_document"


def test_script_directory_recognizes_head_revision():
    """Verify script directory recognizes head revision and callable hooks."""
    config = _get_alembic_config()
    script_dir = ScriptDirectory.from_config(config)

    assert script_dir.get_current_head() == "0003_anomaly_flag"
    assert script_dir.get_heads() == ["0003_anomaly_flag"]

    head_rev = script_dir.get_revision(script_dir.get_current_head())
    assert head_rev is not None
    assert callable(head_rev.module.upgrade)
    assert callable(head_rev.module.downgrade)


def test_offline_migration_sql_generation():
    """Verify offline upgrade generates DDL for all core tables and downgrade drops them."""
    os.environ.setdefault(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@localhost:5432/greenlign?sslmode=require",
    )

    config = _get_alembic_config()

    # Test upgrade DDL generation
    upgrade_buf = io.StringIO()
    with contextlib.redirect_stdout(upgrade_buf):
        command.upgrade(config, "head", sql=True)
    upgrade_sql = upgrade_buf.getvalue()

    expected_tables = [
        "activity_data",
        "emission_factor",
        "calculation",
        "audit_log",
        "disclosure",
        "source_document",
    ]
    for table in expected_tables:
        assert f"CREATE TABLE {table}" in upgrade_sql

    # Verify foreign key constraints on calculation
    assert "FOREIGN KEY(activity_data_id) REFERENCES activity_data (id)" in upgrade_sql
    assert "FOREIGN KEY(emission_factor_id) REFERENCES emission_factor (id)" in upgrade_sql

    # Test downgrade DDL generation
    downgrade_buf = io.StringIO()
    with contextlib.redirect_stdout(downgrade_buf):
        command.downgrade(config, "0002_source_document:base", sql=True)
    downgrade_sql = downgrade_buf.getvalue()

    for table in expected_tables:
        assert f"DROP TABLE {table}" in downgrade_sql
