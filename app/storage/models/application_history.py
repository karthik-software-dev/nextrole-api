from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import BigInteger, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from storage.models.base import Base

if TYPE_CHECKING:
    from storage.models.application import Application


class ApplicationHistory(Base):
    """Audit log of status changes for an application."""

    __tablename__ = "application_history"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    application_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    previous_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    new_status: Mapped[str] = mapped_column(String(30), nullable=False)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    application: Mapped["Application"] = relationship("Application", back_populates="history")

    def __repr__(self) -> str:
        return f"<ApplicationHistory app_id={self.application_id} {self.previous_status} -> {self.new_status}>"
