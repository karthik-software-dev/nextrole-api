from datetime import datetime
from sqlalchemy import BigInteger, DateTime, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from storage.models.base import Base, TimestampMixin


class PipelineRun(Base, TimestampMixin):
    """Execution telemetry record for GitLab CI / local scraper pipeline runs."""

    __tablename__ = "pipeline_runs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    pipeline_id: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    pipeline_iid: Mapped[str | None] = mapped_column(String(50), nullable=True)
    pipeline_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    source: Mapped[str] = mapped_column(String(50), default="gitlab_ci", nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="running", index=True, nullable=False)
    triggered_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    jobs_collected: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    jobs_synced: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    duration_seconds: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    def __repr__(self) -> str:
        return f"<PipelineRun id={self.id} pipeline_id='{self.pipeline_id}' status='{self.status}'>"
