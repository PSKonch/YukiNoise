from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from yn.modules.auth.model import RefreshToken


class RefreshTokenRepository:
    model = RefreshToken

    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(
        self,
        *,
        user_id: UUID,
        token_hash: str,
        expires_at: datetime,
    ) -> RefreshToken:
        stmt = (
            insert(self.model)
            .values(
                user_id=user_id,
                token_hash=token_hash,
                expires_at=expires_at,
            )
            .returning(self.model)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def get_active_by_hash(
        self,
        token_hash: str,
        *,
        for_update: bool = False,
    ) -> RefreshToken | None:
        query = select(self.model).where(
            self.model.token_hash == token_hash,
            self.model.revoked_at.is_(None),
            self.model.expires_at > datetime.now(UTC),
        )
        if for_update:
            query = query.with_for_update()

        result = await self._session.execute(query)
        return result.scalar_one_or_none()

    async def revoke(self, refresh_token_id: UUID) -> bool:
        stmt = (
            update(self.model)
            .where(
                self.model.id == refresh_token_id,
                self.model.revoked_at.is_(None),
            )
            .values(revoked_at=datetime.now(UTC))
            .returning(self.model.id)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def revoke_all_for_user(self, user_id: UUID) -> None:
        stmt = (
            update(self.model)
            .where(
                self.model.user_id == user_id,
                self.model.revoked_at.is_(None),
            )
            .values(revoked_at=datetime.now(UTC))
        )
        await self._session.execute(stmt)
