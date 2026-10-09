from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from yn.modules.auth.auth import get_current_user
from yn.modules.notifications.schemas import (
    MarkAllReadResult,
    NotificationPage,
    NotificationRead,
    UnreadCount,
)
from yn.modules.users.dto import UserDTO
from yn.shared.errors import AppError
from yn.shared.pagination import PaginationParams, get_pagination_params
from yn.shared.unit_of_work import UnitOfWork, get_uow

router = APIRouter(prefix="/notifications", tags=["notifications"])


class NotificationNotFoundError(AppError):
    status_code = 404
    code = "notification_not_found"
    detail = "Notification not found"


@router.get("")
async def list_notifications(
    current_user: Annotated[UserDTO, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    pagination: Annotated[PaginationParams, Depends(get_pagination_params)],
    unread_only: bool = False,
) -> NotificationPage:
    items = await uow.notifications.list_for_user(
        current_user.id,
        limit=pagination.limit + 1,
        offset=pagination.offset,
        unread_only=unread_only,
    )
    return NotificationPage(
        items=[
            NotificationRead.model_validate(item) for item in items[: pagination.limit]
        ],
        unread_count=await uow.notifications.unread_count(current_user.id),
        has_more=len(items) > pagination.limit,
    )


@router.get("/unread-count")
async def unread_count(
    current_user: Annotated[UserDTO, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> UnreadCount:
    return UnreadCount(
        unread_count=await uow.notifications.unread_count(current_user.id)
    )


@router.post("/read-all")
async def mark_all_read(
    current_user: Annotated[UserDTO, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> MarkAllReadResult:
    count = await uow.notifications.mark_all_read(current_user.id)
    await uow.commit()
    return MarkAllReadResult(updated_count=count)


@router.patch("/{notification_id:uuid}/read")
async def mark_read(
    notification_id: UUID,
    current_user: Annotated[UserDTO, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> NotificationRead:
    notification = await uow.notifications.mark_read(current_user.id, notification_id)
    if notification is None:
        raise NotificationNotFoundError
    await uow.commit()
    return NotificationRead.model_validate(notification)
