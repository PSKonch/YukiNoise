from enum import StrEnum


class ReleaseStatus(StrEnum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"
    DELETED = "deleted"


class ReleaseType(StrEnum):
    SINGLE = "single"
    EP = "ep"
    ALBUM = "album"
