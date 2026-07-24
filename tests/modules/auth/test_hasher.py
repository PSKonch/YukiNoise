from yn.modules.auth.hasher import PasswordHasher


def test_password_hash_round_trip() -> None:
    hasher = PasswordHasher()
    hashed_password = hasher.hash_password("correct horse battery staple")

    assert hashed_password != "correct horse battery staple"
    assert hasher.verify_password(
        "correct horse battery staple",
        hashed_password,
    )
    assert not hasher.verify_password("wrong password", hashed_password)


def test_unknown_password_hash_is_rejected() -> None:
    hasher = PasswordHasher()

    assert not hasher.verify_password("password", "not-a-supported-hash")
