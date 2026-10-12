from datetime import datetime, timezone
import logging
from sqlalchemy import select
from sqlalchemy.orm import Session

from storage.models.pipeline_run import PipelineRun

logger = logging.getLogger(__name__)


class PipelineRepository:
    """Data access repository for tracking CI and local execution telemetry."""

    @staticmethod
    def start_pipeline_run(
        session: Session,
        pipeline_id: str | None,
        pipeline_iid: str | None = None,
        pipeline_url: str | None = None,
        source: str = "gitlab_ci",
        triggered_by: str | None = None,
    ) -> PipelineRun:
        """Records the initiation of a scraper pipeline run."""
        now = datetime.now(timezone.utc)
        run = PipelineRun(
            pipeline_id=pipeline_id,
            pipeline_iid=pipeline_iid,
            pipeline_url=pipeline_url,
            source=source,
            status="running",
            triggered_by=triggered_by,
            jobs_collected=0,
            jobs_synced=0,
            started_at=now,
        )
        session.add(run)
        session.flush()
        return run

    @staticmethod
    def finish_pipeline_run(
        session: Session,
        run_id: int,
        status: str,
        jobs_collected: int,
        jobs_synced: int,
        duration_seconds: float | None = None,
        error_message: str | None = None,
    ) -> PipelineRun | None:
        """Completes and records results for a pipeline run."""
        stmt = select(PipelineRun).where(PipelineRun.id == run_id)
        run = session.scalar(stmt)
        if not run:
            return None

        run.status = status
        run.jobs_collected = jobs_collected
        run.jobs_synced = jobs_synced
        run.duration_seconds = duration_seconds
        run.error_message = error_message
        run.completed_at = datetime.now(timezone.utc)
        session.flush()
        try:
            from services.dashboard_service import DashboardService
            DashboardService.clear_cache()
        except Exception:
            pass
        return run

    @staticmethod
    def get_latest_pipeline_run(session: Session) -> PipelineRun | None:
        """Retrieves the most recent pipeline execution record."""
        stmt = select(PipelineRun).order_by(PipelineRun.id.desc()).limit(1)
        return session.scalar(stmt)

    @staticmethod
    def get_recent_pipeline_runs(session: Session, limit: int = 5) -> list[PipelineRun]:
        """Retrieves the latest N pipeline execution records."""
        stmt = select(PipelineRun).order_by(PipelineRun.id.desc()).limit(limit)
        return session.scalars(stmt).all()
