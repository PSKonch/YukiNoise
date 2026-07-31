from datetime import datetime
from typing import cast
from uuid import UUID

from sqlalchemy import Table, insert
from sqlalchemy.ext.asyncio import AsyncSession

from yn.shared.outbox.model import OutboxEvent


class OutboxRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(
        self,
        *,
        event_id: UUID,
        event_type: str,
        exchange: str,
        routing_key: str,
        payload: dict[str, object],
        occurred_at: datetime,
    ) -> None:
        outbox_table = cast(Table, OutboxEvent.__table__)
        await self._session.execute(
            insert(outbox_table).values(
                id=event_id,
                event_type=event_type,
                exchange=exchange,
                routing_key=routing_key,
                payload=payload,
                occurred_at=occurred_at,
            )
        )
