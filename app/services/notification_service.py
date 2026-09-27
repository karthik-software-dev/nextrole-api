from datetime import datetime, timezone
import logging
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from schemas.notification import NotificationListOut, NotificationOut
from storage.database import get_db
from storage.models.notification import Notification

logger = logging.getLogger(__name__)


class NotificationService:
    """Service managing system notifications and user alerts."""

    @classmethod
    def get_notifications(cls, limit: int = 30) -> NotificationListOut:
        """Fetches recent notifications and calculates unread count."""
        with get_db() as session:
            stmt = (
                select(Notification)
                .order_by(Notification.created_at.desc())
                .limit(limit)
            )
            records = session.scalars(stmt).all()

            unread_stmt = (
                select(func.count(Notification.id))
                .where(Notification.is_read.is_(False))
            )
            unread_count = session.scalar(unread_stmt) or 0

            items = [
                NotificationOut.model_validate(rec)
                for rec in records
            ]
            return NotificationListOut(items=items, unread_count=unread_count)

    @classmethod
    def mark_as_read(cls, notification_id: int) -> bool:
        """Marks a specific notification as read."""
        with get_db() as session:
            stmt = (
                update(Notification)
                .where(Notification.id == notification_id)
                .values(is_read=True)
            )
            res = session.execute(stmt)
            return res.rowcount > 0

    @classmethod
    def mark_all_as_read(cls) -> int:
        """Marks all notifications as read."""
        with get_db() as session:
            stmt = (
                update(Notification)
                .where(Notification.is_read.is_(False))
                .values(is_read=True)
            )
            res = session.execute(stmt)
            return res.rowcount

    @classmethod
    def create_notification(
        cls,
        title: str,
        message: str,
        type: str = "discovery",
        link: str | None = None,
    ) -> NotificationOut | None:
        """Creates and persists a new notification."""
        try:
            with get_db() as session:
                rec = Notification(
                    title=title,
                    message=message,
                    type=type,
                    is_read=False,
                    link=link,
                )
                session.add(rec)
                session.flush()
                session.refresh(rec)
                return NotificationOut.model_validate(rec)
        except Exception as e:
            logger.error(f"Failed to create notification '{title}': {e}", exc_info=True)
            return None
