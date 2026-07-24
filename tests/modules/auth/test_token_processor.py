from uuid import uuid4

import pytest

from yn.modules.auth.errors import AccessTokenExpiredError, InvalidAccessTokenError
from yn.modules.auth.token_processor import TokenProcessor


def make_token_processor(
    *,
    access_token_expire_minutes: int = 15,
) -> TokenProcessor:
    return TokenProcessor(
        secret_key="test-secret-that-is-at-least-32-bytes-long",
        algorithm="HS256",
        access_token_expire_minutes=access_token_expire_minutes,
        refresh_token_expire_minutes=60,
    )


def test_access_token_round_trip() -> None:
    processor = make_token_processor()
    user_id = uuid4()

    access_token = processor.create_access_token(user_id)

    assert processor.get_user_id_from_access_token(access_token.token) == user_id


def test_expired_access_token_is_rejected() -> None:
    processor = make_token_processor(access_token_expire_minutes=-1)
    access_token = processor.create_access_token(uuid4())

    with pytest.raises(AccessTokenExpiredError):
        processor.decode_access_token(access_token.token)


def test_invalid_access_token_is_rejected() -> None:
    processor = make_token_processor()

    with pytest.raises(InvalidAccessTokenError):
        processor.decode_access_token("not-a-jwt")


def test_refresh_token_is_opaque_and_hash_is_stable() -> None:
    processor = make_token_processor()

    refresh_token = processor.create_refresh_token()

    assert refresh_token.token != refresh_token.token_hash
    assert processor.hash_refresh_token(refresh_token.token) == refresh_token.token_hash
