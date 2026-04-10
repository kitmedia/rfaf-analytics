"""PostgreSQL AsyncPG connection + create_tables()"""

import os
from collections.abc import AsyncGenerator

import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.models import Base

logger = structlog.get_logger()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://rfaf_user:rfaf_pass@localhost:5432/rfaf_analytics",
)

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_size=10,
    max_overflow=20,
)

async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: yields an async DB session."""
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def create_tables() -> None:
    """Create all tables from SQLAlchemy models. For dev/initial setup only."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    table_names = list(Base.metadata.tables.keys())
    await logger.ainfo(
        "tables_created",
        tables=table_names,
        count=len(table_names),
    )


async def drop_tables() -> None:
    """Drop all tables. Only for testing."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await logger.ainfo("tables_dropped")
