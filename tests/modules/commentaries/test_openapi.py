from yn.main import app


def test_commentary_routes_are_exposed() -> None:
    paths = app.openapi()["paths"]
    collection = paths["/posts/{post_id}/commentaries"]
    item = paths["/commentaries/{commentary_id}"]

    assert "get" in collection
    assert collection["post"]["responses"]["201"]
    assert "get" in item
    assert "put" in item
    assert item["delete"]["responses"]["204"]


def test_commentary_write_routes_require_authentication() -> None:
    paths = app.openapi()["paths"]
    operations = (
        paths["/posts/{post_id}/commentaries"]["post"],
        paths["/commentaries/{commentary_id}"]["put"],
        paths["/commentaries/{commentary_id}"]["delete"],
    )

    for operation in operations:
        assert operation["security"] == [{"OAuth2PasswordBearer": []}]


def test_commentary_content_is_bounded() -> None:
    schema = app.openapi()["components"]["schemas"]["CommentaryUpdate"]
    content = schema["properties"]["content"]

    assert content["minLength"] == 1
    assert content["maxLength"] == 5000
