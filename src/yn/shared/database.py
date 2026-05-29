from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from yn.shared.settings import settings

async_primary_engine = create_async_engine(settings.postgres_primary_url, echo=True)
async_primary_session = async_sessionmaker(
    async_primary_engine, expire_on_commit=False, class_=AsyncSession
)

async_replica_engine = create_async_engine(settings.postgres_replica_url, echo=True)
async_replica_session = async_sessionmaker(
    async_replica_engine, expire_on_commit=False, class_=AsyncSession
)


async def get_primary_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_primary_session() as session:
        yield session


async def get_replica_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_replica_session() as session:
        yield session


class Base(DeclarativeBase):
    pass
