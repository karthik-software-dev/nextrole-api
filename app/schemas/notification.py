from datetime import datetime
from pydantic import BaseModel, ConfigDict


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    message: str
    type: str
    is_read: bool
    link: str | None = None
    created_at: datetime


class NotificationListOut(BaseModel):
    items: list[NotificationOut]
    unread_count: int
