from sqlalchemy import func, select
from sqlalchemy.orm import Session

from schemas.dashboard import (
    ApplicationStatusBreakdownOut,
    DashboardSummaryOut,
    LocationBreakdownOut,
)
from storage.models.application import Application
from storage.repositories.job_repository import JobRepository


class DashboardService:
    """Service computing aggregated metrics and KPI statistics."""

    @staticmethod
    def get_summary(session: Session) -> DashboardSummaryOut:
        """Calculates discovery engine and application pipeline statistics."""
        # 1. Job & Company stats
        job_stats = JobRepository.get_database_stats(session)

        # 2. Application breakdown by status
        app_counts = dict(
            session.execute(
                select(Application.status, func.count(Application.id))
                .where(Application.is_active.is_(True))
                .group_by(Application.status)
            ).all()
        )

        app_breakdown = ApplicationStatusBreakdownOut(
            drafted=app_counts.get("drafted", 0),
            applied=app_counts.get("applied", 0),
            under_review=app_counts.get("under_review", 0),
            interviewing=app_counts.get("interviewing", 0),
            offered=app_counts.get("offered", 0),
            rejected=app_counts.get("rejected", 0),
        )

        loc_breakdown = LocationBreakdownOut(
            bangalore=job_stats.get("bangalore_jobs", 0),
            chennai=job_stats.get("chennai_jobs", 0),
            remote=job_stats.get("remote_jobs", 0),
            other=job_stats.get("other_jobs", 0),
        )

        return DashboardSummaryOut(
            total_jobs=job_stats["total_jobs"],
            active_jobs=job_stats["active_jobs"],
            inactive_jobs=job_stats["inactive_jobs"],
            tier1_jobs=job_stats["tier1_jobs"],
            tier2_jobs=job_stats["tier2_jobs"],
            total_companies=job_stats["total_companies"],
            total_sources=job_stats["total_sources"],
            location_breakdown=loc_breakdown,
            application_breakdown=app_breakdown,
            sources_breakdown=job_stats.get("sources_breakdown", []),
        )
