from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import (
    ARRAY,
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from storage.models.base import ActiveMixin, Base, TimestampMixin

if TYPE_CHECKING:
    from storage.models.application import Application
    from storage.models.company import Company
    from storage.models.job_source import JobSource


class Job(Base, TimestampMixin, ActiveMixin):
    """Canonical, deduplicated job opportunity."""

    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Titles
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    normalized_title: Mapped[str] = mapped_column(String(300), index=True, nullable=False)

    # Deterministic Deduplication Key
    dedup_hash: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        index=True,
        nullable=False,
    )

    # Location & Remote
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), index=True, nullable=True)
    location_bucket: Mapped[str] = mapped_column(
        String(20),
        default="OTHER",
        index=True,
        nullable=False,
    )
    is_remote: Mapped[bool] = mapped_column(Boolean, default=False, index=True, nullable=False)

    # Experience Requirements
    experience_min: Mapped[int | None] = mapped_column(SmallInteger, index=True, nullable=True)
    experience_max: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    experience_raw: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Compensation
    salary_min: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    salary_max: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(10), default="INR", nullable=False)
    salary_raw: Mapped[str | None] = mapped_column(String(150), nullable=True)

    # Description & Content
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Application URLs & ATS Provider
    canonical_apply_url: Mapped[str | None] = mapped_column(String(2000), index=True, nullable=True)
    apply_type: Mapped[str] = mapped_column(
        String(30),
        default="UNKNOWN",
        index=True,
        nullable=False,
    )
    ats_provider: Mapped[str | None] = mapped_column(String(100), index=True, nullable=True)

    # Scoring & Prioritization
    relevance_score: Mapped[float] = mapped_column(
        Numeric(5, 2),
        default=0.0,
        index=True,
        nullable=False,
    )
    matched_skills: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    priority_score: Mapped[float] = mapped_column(
        Numeric(5, 2),
        default=0.0,
        index=True,
        nullable=False,
    )
    priority_tier: Mapped[str] = mapped_column(
        String(40),
        default="TIER 3",
        index=True,
        nullable=False,
    )

    # Status & Source Count
    status: Mapped[str] = mapped_column(
        String(20),
        default="discovered",
        index=True,
        nullable=False,
    )
    source_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Extensible Filter Attributes
    tags: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    # Discovery Lifecycle Timestamps
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

    # Relationships
    company: Mapped["Company"] = relationship("Company", back_populates="jobs")
    sources: Mapped[list["JobSource"]] = relationship(
        "JobSource",
        back_populates="job",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    application: Mapped["Application | None"] = relationship(
        "Application",
        back_populates="job",
        uselist=False,
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("idx_jobs_priority_ranking", "priority_tier", "priority_score"),
        Index("idx_jobs_active_priority", "is_active", "priority_score"),
        Index("idx_jobs_company_normalized_title", "company_id", "normalized_title"),
        Index("idx_jobs_matched_skills_gin", "matched_skills", postgresql_using="gin"),
    )

    def __repr__(self) -> str:
        return f"<Job id={self.id} title='{self.title}' tier='{self.priority_tier}' active={self.is_active}>"
