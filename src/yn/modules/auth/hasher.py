from passlib.context import CryptContext
from passlib.exc import UnknownHashError


class PasswordHasher:
    def __init__(self) -> None:
        self._context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def hash_password(self, plain_password: str) -> str:
        return self._context.hash(plain_password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        try:
            return self._context.verify(plain_password, hashed_password)
        except (TypeError, ValueError, UnknownHashError):
            return False
