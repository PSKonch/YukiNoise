import hashlib
import hmac
from datetime import UTC, datetime, timedelta
from secrets import token_urlsafe
from typing import Any
from uuid import UUID

import jwt
from jwt import ExpiredSignatureError, InvalidTokenError

from yn.modules.auth.dto import AccessTokenDTO, RefreshTokenDTO
from yn.modules.auth.errors import AccessTokenExpiredError, InvalidAccessTokenError


class TokenProcessor:
    def __init__(
        self,
        *,
        secret_key: str,
        algorithm: str,
        access_token_expire_minutes: int,
        refresh_token_expire_minutes: int,
    ) -> None:
        self._secret_key = secret_key
        self._algorithm = algorithm
        self._access_token_expire_minutes = access_token_expire_minutes
        self._refresh_token_expire_minutes = refresh_token_expire_minutes

    def create_access_token(self, user_id: UUID) -> AccessTokenDTO:
        now = datetime.now(UTC)
        expires_at = now + timedelta(minutes=self._access_token_expire_minutes)
        payload = {
            "sub": str(user_id),
            "iat": now,
            "exp": expires_at,
            "type": "access",
        }
        token = jwt.encode(
            payload=payload,
            key=self._secret_key,
            algorithm=self._algorithm,
        )
        return AccessTokenDTO(token=token, expires_at=expires_at)

    def decode_access_token(self, token: str) -> dict[str, Any]:
        try:
            payload = jwt.decode(
                jwt=token,
                key=self._secret_key,
                algorithms=[self._algorithm],
            )
        except ExpiredSignatureError as exc:
            raise AccessTokenExpiredError from exc
        except InvalidTokenError as exc:
            raise InvalidAccessTokenError from exc

        if payload.get("type") != "access":
            raise InvalidAccessTokenError
        return payload

    def get_user_id_from_access_token(self, token: str) -> UUID:
        payload = self.decode_access_token(token)
        user_id = payload.get("sub")
        if user_id is None:
            raise InvalidAccessTokenError

        try:
            return UUID(str(user_id))
        except (TypeError, ValueError) as exc:
            raise InvalidAccessTokenError from exc

    def create_refresh_token(self) -> RefreshTokenDTO:
        token = token_urlsafe(64)
        expires_at = datetime.now(UTC) + timedelta(
            minutes=self._refresh_token_expire_minutes
        )
        return RefreshTokenDTO(
            token=token,
            token_hash=self.hash_refresh_token(token),
            expires_at=expires_at,
        )

    def hash_refresh_token(self, token: str) -> str:
        return hmac.new(
            key=self._secret_key.encode(),
            msg=token.encode(),
            digestmod=hashlib.sha256,
        ).hexdigest()
