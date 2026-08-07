from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from yn.shared.outbox.model import OutboxModel


class OutboxRepository:
    model = OutboxModel

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(
        self,
        *,
        event_id: UUID,
        topic: str,
        message_key: str | None,
        event_type: str,
        version: int,
        payload: dict[str, object],
    ) -> OutboxModel:
        event = self.model(
            id=event_id,
            topic=topic,
            message_key=message_key,
            event_type=event_type,
            version=version,
            payload=payload,
        )
        self._session.add(event)
        return event

    async def get_pending_ids(self, *, limit: int) -> list[UUID]:
        statement = (
            select(self.model.id)
            .where(
                self.model.published_at.is_(None),
                or_(
                    self.model.next_attempt_at.is_(None),
                    self.model.next_attempt_at <= func.now(),
                ),
            )
            .order_by(self.model.created_at.asc(), self.model.id.asc())
            .limit(limit)
        )
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def lock_pending(
        self,
        event_id: UUID,
        *,
        ignore_retry_schedule: bool = False,
    ) -> OutboxModel | None:
        conditions = [
            self.model.id == event_id,
            self.model.published_at.is_(None),
        ]
        if not ignore_retry_schedule:
            conditions.append(
                or_(
                    self.model.next_attempt_at.is_(None),
                    self.model.next_attempt_at <= func.now(),
                )
            )

        statement = (
            select(self.model).where(*conditions).with_for_update(skip_locked=True)
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    @staticmethod
    def mark_published(event: OutboxModel) -> None:
        event.published_at = datetime.now(UTC)
        event.next_attempt_at = None

    @staticmethod
    def mark_failed(event: OutboxModel, *, next_attempt_at: datetime) -> None:
        event.attempts += 1
        event.next_attempt_at = next_attempt_at
