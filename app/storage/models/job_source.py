from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from storage.models.base import Base

if TYPE_CHECKING:
    from storage.models.job import Job


class JobSource(Base):
    """Represents a specific platform sighting/posting for a canonical job."""

    __tablename__ = "job_sources"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_name: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    source_job_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    discovery_url: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    source_apply_url: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    source_posted_at: Mapped[str | None] = mapped_column(String(100), nullable=True)
    raw_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    job: Mapped["Job"] = relationship("Job", back_populates="sources")

    __table_args__ = (
        UniqueConstraint("source_name", "source_job_id", name="uq_source_posting"),
    )

    def __repr__(self) -> str:
        return f"<JobSource id={self.id} source='{self.source_name}' ext_id='{self.source_job_id}'>"
