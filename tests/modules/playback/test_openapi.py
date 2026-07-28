from yn.main import app


def test_spotify_style_player_routes_are_exposed() -> None:
    paths = app.openapi()["paths"]
    assert "/me/player" in paths
    assert "/me/player/play" in paths
    assert "/me/player/progress" in paths
    assert "/me/player/queue" in paths
    assert "/playback/start" not in paths
