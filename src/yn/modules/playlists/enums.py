from enum import StrEnum


class PlaylistType(StrEnum):
    SYSTEM = "system"
    USER = "user"


class SystemPlaylistKey(StrEnum):
    TOP_DAY = "top_day"
    TOP_WEEK = "top_week"
    TOP_MONTH = "top_month"
