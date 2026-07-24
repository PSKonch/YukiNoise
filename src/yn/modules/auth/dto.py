from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class AccessTokenDTO:
    token: str
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class RefreshTokenDTO:
    token: str
    token_hash: str
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class TokenPairDTO:
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
