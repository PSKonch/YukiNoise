from yn.main import app


def test_follow_routes_are_exposed() -> None:
    paths = app.openapi()["paths"]

    assert "/follows/{artist_id}/followers" in paths
    assert "/follows/{artist_id}/following" in paths
    assert "/follows/{artist_id}/status" in paths
    assert paths["/follows/{artist_id}"]["post"]["responses"]["201"]
    assert "delete" in paths["/follows/{artist_id}"]


def test_follow_write_routes_require_authentication() -> None:
    paths = app.openapi()["paths"]

    assert paths["/follows/{artist_id}"]["post"]["security"] == [
        {"OAuth2PasswordBearer": []}
    ]
    assert paths["/follows/{artist_id}"]["delete"]["security"] == [
        {"OAuth2PasswordBearer": []}
    ]
