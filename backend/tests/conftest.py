import json
import sqlite3
import uuid
from collections.abc import AsyncGenerator

import pytest_asyncio
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.compiler import compiles

from app.models import Base

# Register adapter for lists on SQLite (e.g. Postgres ARRAY)
sqlite3.register_adapter(
    list,
    lambda val: json.dumps([str(x) if isinstance(x, uuid.UUID) else x for x in val]),
)

_orig_array_proc = ARRAY.result_processor


def _sqlite_array_result_processor(self, dialect, coltype):
    if dialect.name == "sqlite":
        def process(value):
            if value is None:
                return []
            if isinstance(value, str):
                try:
                    data = json.loads(value)
                    return [uuid.UUID(x) if isinstance(x, str) else x for x in data]
                except Exception:
                    return value
            return value

        return process
    return _orig_array_proc(self, dialect, coltype)


ARRAY.result_processor = _sqlite_array_result_processor  # type: ignore[method-assign]


# Compile Postgres-specific types on SQLite so create_all doesn't fail
@compiles(ARRAY, "sqlite")
def compile_array_sqlite(type_, compiler, **kw):
    return "TEXT"


@compiles(JSONB, "sqlite")
def compile_jsonb_sqlite(type_, compiler, **kw):
    return "JSON"


DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Yields a clean async SQLAlchemy session backed by in-memory SQLite."""
    engine = create_async_engine(DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with factory() as session:
        yield session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
