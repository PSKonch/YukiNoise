from collections.abc import AsyncGenerator
from dataclasses import dataclass

from sqlalchemy import text
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


@dataclass(frozen=True, slots=True)
class ReplicaStatus:
    is_replica: bool
    lag_bytes: int | None


async def get_replica_status() -> ReplicaStatus:
    """Return the physical-replication state observed by both database nodes."""
    async with async_primary_engine.connect() as primary_connection:
        primary_lsn = await primary_connection.scalar(
            text("SELECT pg_current_wal_lsn()::text")
        )

    async with async_replica_engine.connect() as replica_connection:
        is_replica = await replica_connection.scalar(text("SELECT pg_is_in_recovery()"))
        if not is_replica:
            return ReplicaStatus(is_replica=False, lag_bytes=None)

        lag_bytes = await replica_connection.scalar(
            text(
                "SELECT pg_wal_lsn_diff(CAST(CAST(:primary_lsn AS text) AS pg_lsn), "
                "pg_last_wal_replay_lsn())"
            ),
            {"primary_lsn": str(primary_lsn)},
        )
    return ReplicaStatus(
        is_replica=True,
        lag_bytes=int(lag_bytes) if lag_bytes is not None else None,
    )


class Base(DeclarativeBase):
    pass
