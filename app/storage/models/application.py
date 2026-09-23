from datetime import date, datetime
from typing import TYPE_CHECKING
from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from storage.models.base import ActiveMixin, Base, TimestampMixin

if TYPE_CHECKING:
    from storage.models.application_history import ApplicationHistory
    from storage.models.job import Job
    from storage.models.user import User


class Application(Base, TimestampMixin, ActiveMixin):
    """Personal job application tracking and submission lifecycle."""

    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    job_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Workflow Status (drafted, applied, under_review, interviewing, offered, rejected, withdrawn)
    status: Mapped[str] = mapped_column(
        String(30),
        default="drafted",
        index=True,
        nullable=False,
    )
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resume_version: Mapped[str | None] = mapped_column(String(255), nullable=True)
    portal_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    follow_up_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)

    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="applications")
    job: Mapped["Job"] = relationship("Job", back_populates="application")
    history: Mapped[list["ApplicationHistory"]] = relationship(
        "ApplicationHistory",
        back_populates="application",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="ApplicationHistory.changed_at.asc()",
    )

    __table_args__ = (
        UniqueConstraint("user_id", "job_id", name="uq_user_job_application"),
    )

    def __repr__(self) -> str:
        return f"<Application id={self.id} job_id={self.job_id} status='{self.status}'>"
