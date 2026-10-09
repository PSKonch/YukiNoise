from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from yn.modules.notifications.enums import NotificationType


class NotificationRead(BaseModel):
    id: UUID
    type: NotificationType
    title: str
    message: str
    payload: dict[str, str]
    release_id: UUID | None
    created_at: datetime
    read_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class NotificationPage(BaseModel):
    items: list[NotificationRead]
    unread_count: int
    has_more: bool


class UnreadCount(BaseModel):
    unread_count: int


class MarkAllReadResult(BaseModel):
    updated_count: int
