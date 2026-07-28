import pytest

from yn.modules.tracks.route import parse_byte_range


@pytest.mark.parametrize(
    ("header", "expected"),
    [
        (None, (200, 0, 999)),
        ("bytes=0-99", (206, 0, 99)),
        ("bytes=500-", (206, 500, 999)),
        ("bytes=-100", (206, 900, 999)),
        ("bytes=900-2000", (206, 900, 999)),
    ],
)
def test_parse_byte_range(header: str | None, expected: tuple[int, int, int]) -> None:
    assert parse_byte_range(header, 1000) == expected


@pytest.mark.parametrize(
    "header", ["bytes=1000-", "items=0-1", "bytes=5-4", "bytes=0-1,3-4"]
)
def test_parse_byte_range_rejects_unsatisfiable_ranges(header: str) -> None:
    with pytest.raises(ValueError):
        parse_byte_range(header, 1000)
