from uuid import UUID

from yn.modules.auth.dto import TokenPairDTO
from yn.modules.auth.errors import (
    InvalidAccessTokenError,
    InvalidCredentialsError,
    InvalidRefreshTokenError,
)
from yn.modules.auth.security import SecurityManager
from yn.modules.users.dto import UserDTO
from yn.modules.users.errors import EmailAlreadyTakenError
from yn.shared.unit_of_work import UnitOfWork


class AuthService:
    def __init__(self, uow: UnitOfWork, security: SecurityManager):
        self.uow = uow
        self.security = security

    async def register(
        self,
        *,
        email: str,
        password: str,
    ) -> TokenPairDTO:
        hashed_password = self.security.password_hasher.hash_password(password)
        user = await self.uow.users.create(
            email=self._normalize_email(email),
            hashed_password=hashed_password,
            role="user",
        )
        if user is None:
            raise EmailAlreadyTakenError

        token_pair = await self._issue_token_pair(user.id)
        await self.uow.commit()
        return token_pair

    async def login(
        self,
        *,
        email: str,
        password: str,
    ) -> TokenPairDTO:
        user = await self.uow.users.get_user_by_email(self._normalize_email(email))
        if (
            user is None
            or not user.is_active
            or user.deleted_at is not None
            or not self.security.password_hasher.verify_password(
                password,
                user.hashed_password,
            )
        ):
            raise InvalidCredentialsError

        token_pair = await self._issue_token_pair(user.id)
        await self.uow.commit()
        return token_pair

    async def refresh(self, refresh_token: str) -> TokenPairDTO:
        token_hash = self.security.token_processor.hash_refresh_token(refresh_token)
        stored_token = await self.uow.refresh_tokens.get_active_by_hash(
            token_hash,
            for_update=True,
        )
        if stored_token is None:
            raise InvalidRefreshTokenError

        user = await self.uow.users.get_user_by_id(stored_token.user_id)
        if user is None or not user.is_active or user.deleted_at is not None:
            await self.uow.refresh_tokens.revoke(stored_token.id)
            await self.uow.commit()
            raise InvalidRefreshTokenError

        revoked = await self.uow.refresh_tokens.revoke(stored_token.id)
        if not revoked:
            raise InvalidRefreshTokenError

        token_pair = await self._issue_token_pair(stored_token.user_id)
        await self.uow.commit()
        return token_pair

    async def logout(self, refresh_token: str) -> None:
        token_hash = self.security.token_processor.hash_refresh_token(refresh_token)
        stored_token = await self.uow.refresh_tokens.get_active_by_hash(
            token_hash,
            for_update=True,
        )
        if stored_token is None:
            raise InvalidRefreshTokenError

        revoked = await self.uow.refresh_tokens.revoke(stored_token.id)
        if not revoked:
            raise InvalidRefreshTokenError
        await self.uow.commit()

    async def get_user_from_access_token(
        self,
        access_token: str,
        *,
        allow_deleted: bool = False,
    ) -> UserDTO:
        user_id = self.security.token_processor.get_user_id_from_access_token(
            access_token
        )
        user = await self.uow.users.get_user_with_profile_by_id(user_id)
        if (
            user is None
            or not user.is_active
            or (user.deleted_at is not None and not allow_deleted)
        ):
            raise InvalidAccessTokenError
        return UserDTO.from_orm(user)

    async def revoke_all_user_sessions(self, user_id: UUID) -> None:
        await self.uow.refresh_tokens.revoke_all_for_user(user_id)
        await self.uow.commit()

    async def _issue_token_pair(self, user_id: UUID) -> TokenPairDTO:
        access_token = self.security.token_processor.create_access_token(user_id)
        refresh_token = self.security.token_processor.create_refresh_token()
        await self.uow.refresh_tokens.create(
            user_id=user_id,
            token_hash=refresh_token.token_hash,
            expires_at=refresh_token.expires_at,
        )
        return TokenPairDTO(
            access_token=access_token.token,
            refresh_token=refresh_token.token,
        )

    @staticmethod
    def _normalize_email(email: str) -> str:
        return email.strip().casefold()
