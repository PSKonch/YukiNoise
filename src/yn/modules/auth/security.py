from dataclasses import dataclass

from yn.modules.auth.hasher import PasswordHasher
from yn.modules.auth.token_processor import TokenProcessor


@dataclass(frozen=True, slots=True)
class SecurityManager:
    password_hasher: PasswordHasher
    token_processor: TokenProcessor
