"""Seed script: load versioned emission factors from bundled JSON files."""
import asyncio
import json
import uuid
from datetime import date
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.models.emission_factor import EmissionFactor

FACTOR_FILES = [
    Path(__file__).parent.parent / "factor_tables" / "epa_ghg_factors_2025.json",
    Path(__file__).parent.parent / "factor_tables" / "defra_2025.json",
]


def _parse_date(s: str | None) -> date | None:
    return date.fromisoformat(s) if s else None


async def seed_factors(session: AsyncSession | None = None) -> int:
    """Insert factors that don't already exist (idempotent). Returns count inserted."""
    if session is None:
        async with AsyncSessionLocal() as session_ctx:
            return await seed_factors(session=session_ctx)

    inserted = 0
    for factor_file in FACTOR_FILES:
        rows = json.loads(factor_file.read_text(encoding="utf-8"))
        for row in rows:
            # Idempotency check: skip if (source, source_version, activity_type, geography) exists
            existing = await session.scalar(
                select(EmissionFactor).where(
                    EmissionFactor.source == row["source"],
                    EmissionFactor.source_version == row["source_version"],
                    EmissionFactor.activity_type == row["activity_type"],
                    EmissionFactor.geography == row["geography"],
                )
            )
            if existing:
                continue

            session.add(
                EmissionFactor(
                    id=uuid.uuid4(),
                    source=row["source"],
                    source_version=row["source_version"],
                    activity_type=row["activity_type"],
                    geography=row["geography"],
                    unit=row["unit"],
                    factor_value=Decimal(row["factor_value"]),
                    factor_unit=row["factor_unit"],
                    published_date=date.fromisoformat(row["published_date"]),
                    effective_from=date.fromisoformat(row["effective_from"]),
                    effective_to=_parse_date(row.get("effective_to")),
                )
            )
            inserted += 1

    await session.commit()
    return inserted


if __name__ == "__main__":
    count = asyncio.run(seed_factors())
    print(f"Seeded {count} emission factors.")
