from collections.abc import AsyncGenerator

from sqlalchemy.engine.url import make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.util import immutabledict

from app.core.config import settings


def get_async_engine(db_url: str) -> AsyncEngine:
    url = make_url(db_url)
    connect_args: dict[str, object] = {}
    if "sqlite" not in db_url:
        query = dict(url.query)
        ssl_val = query.pop("sslmode", None) or query.pop("ssl", None)
        query.pop("channel_binding", None)
        url = url._replace(query=immutabledict(query))
        if ssl_val:
            connect_args["ssl"] = ssl_val
        else:
            connect_args["ssl"] = "require"
    return create_async_engine(
        url,
        echo=settings.environment == "development",
        pool_pre_ping=True,
        connect_args=connect_args,
    )


engine = get_async_engine(settings.database_url)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields a database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
