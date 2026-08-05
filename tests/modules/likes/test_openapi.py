from yn.main import app


def test_minimal_like_routes_are_exposed_and_protected() -> None:
    paths = app.openapi()["paths"]
    item_path = paths["/likes/{target_type}/{target_id}"]
    status_path = paths["/likes/{target_type}/{target_id}/status"]["get"]

    assert item_path["post"]["responses"]["201"]
    assert "delete" in item_path
    for operation in (item_path["post"], item_path["delete"], status_path):
        assert operation["security"] == [{"OAuth2PasswordBearer": []}]


def test_like_target_type_is_an_enum() -> None:
    schema = app.openapi()["components"]["schemas"]["TargetType"]

    assert schema["enum"] == [
        "track",
        "release",
        "playlist",
        "post",
        "commentary",
    ]
