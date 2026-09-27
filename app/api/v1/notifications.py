from fastapi import APIRouter, HTTPException, status

from schemas.notification import NotificationListOut
from services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get(
    "",
    response_model=NotificationListOut,
    summary="Get user notifications and unread count",
)
def get_notifications(limit: int = 30) -> NotificationListOut:
    """Returns recent system notifications, discovery updates, and unread count."""
    return NotificationService.get_notifications(limit=limit)


@router.post(
    "/{notification_id}/read",
    summary="Mark single notification as read",
)
def mark_notification_as_read(notification_id: int) -> dict[str, str]:
    """Marks a single notification as read."""
    success = NotificationService.mark_as_read(notification_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )
    return {"status": "ok", "message": "Notification marked as read"}


@router.post(
    "/mark-all-read",
    summary="Mark all notifications as read",
)
def mark_all_notifications_as_read() -> dict[str, str | int]:
    """Marks all unread notifications as read."""
    updated = NotificationService.mark_all_as_read()
    return {"status": "ok", "marked_read_count": updated}
