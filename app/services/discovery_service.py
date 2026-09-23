from datetime import datetime, timezone
import logging
from typing import Any

from processing.deduplication import deduplicate_jobs
from processing.prioritization import prioritize_jobs, select_by_location_quota
from processing.relevance import filter_relevant_jobs
from processing.url_validator import validate_job_urls
from schemas.discovery import DiscoveryStatusOut
from sources.ats_source import fetch_target_company_jobs
from sources.google_jobs_source import fetch_google_jobs
from sources.indeed_source import fetch_indeed_jobs
from sources.linkedin_source import fetch_linkedin_jobs
from sources.naukri_source import fetch_naukri_jobs
from sources.wellfound_source import fetch_wellfound_jobs
from storage.database import get_db
from storage.repositories.job_repository import JobRepository

logger = logging.getLogger(__name__)


class DiscoveryService:
    """Service orchestrating background scraper runs and tracking execution status."""

    # In-memory execution state
    _is_running: bool = False
    _last_run_at: datetime | None = None
    _last_status: str = "idle"
    _last_jobs_found: int = 0
    _last_jobs_synced: int = 0
    _last_error: str | None = None

    @classmethod
    def get_status(cls) -> DiscoveryStatusOut:
        """Returns the current background scraper status."""
        return DiscoveryStatusOut(
            is_running=cls._is_running,
            last_run_at=cls._last_run_at.isoformat() if cls._last_run_at else None,
            last_status=cls._last_status,
            last_jobs_found=cls._last_jobs_found,
            last_jobs_synced=cls._last_jobs_synced,
            last_error=cls._last_error,
        )

    @classmethod
    def run_pipeline(
        cls,
        source: str = "all",
        location: str = "all",
        use_cache: bool = True,
    ) -> None:
        """Runs the complete discovery pipeline and persists results into PostgreSQL."""
        if cls._is_running:
            logger.warning("Discovery pipeline is already running. Skipping concurrent run.")
            return

        cls._is_running = True
        cls._last_status = "running"
        cls._last_error = None

        try:
            logger.info(f"Starting discovery run (source={source}, location={location}, cache={use_cache})")
            jobs = []

            source_fetchers = [
                ("indeed", ("indeed", "all"), fetch_indeed_jobs),
                ("naukri", ("naukri", "all"), fetch_naukri_jobs),
                ("linkedin", ("linkedin", "all"), fetch_linkedin_jobs),
                ("wellfound", ("wellfound", "all"), fetch_wellfound_jobs),
                ("google_jobs", ("google_jobs", "google", "all"), fetch_google_jobs),
                ("ats", ("ats", "careers", "target_companies", "all"), fetch_target_company_jobs),
            ]

            for name, triggers, fetcher in source_fetchers:
                if source in triggers:
                    try:
                        fetched = fetcher(use_cache=use_cache)
                        logger.info(f"[{name.upper()}] Fetched {len(fetched)} postings.")
                        jobs.extend(fetched)
                    except Exception as src_err:
                        logger.warning(f"[{name.upper()}] Fetch encountered error: {src_err}. Proceeding with remaining sources.")

            cls._last_jobs_found = len(jobs)

            # Processing pipeline
            relevant_jobs = filter_relevant_jobs(jobs)
            unique_jobs = deduplicate_jobs(relevant_jobs)
            validated_jobs = validate_job_urls(unique_jobs)
            prioritized_jobs = prioritize_jobs(validated_jobs)

            # Location filtering or quota
            loc_lower = location.lower()
            if loc_lower in ("bangalore", "bengaluru", "blr"):
                prioritized_jobs = [j for j in prioritized_jobs if any(k in (j.location or "").lower() for k in ["bengaluru", "bangalore", "karnataka"])]
            elif loc_lower in ("chennai", "maa"):
                prioritized_jobs = [j for j in prioritized_jobs if any(k in (j.location or "").lower() for k in ["chennai", "tamil nadu"])]
            elif loc_lower in ("other", "remote", "hyd", "hyderabad", "pune"):
                prioritized_jobs = [j for j in prioritized_jobs if not any(k in (j.location or "").lower() for k in ["bengaluru", "bangalore", "karnataka", "chennai"])]
            else:
                prioritized_jobs = select_by_location_quota(prioritized_jobs, target_total=100)

            # Persist to PostgreSQL safely using nested transaction savepoints
            synced_count = 0
            with get_db() as session:
                for job in prioritized_jobs:
                    try:
                        with session.begin_nested():
                            JobRepository.upsert_job(session, job)
                        synced_count += 1
                    except Exception as job_err:
                        logger.warning(f"Failed to upsert job '{job.title}' ({job.id}): {job_err}")

            cls._last_jobs_synced = synced_count
            cls._last_run_at = datetime.now(timezone.utc)
            cls._last_status = "completed"
            logger.info(f"Discovery completed successfully. Synced {synced_count} jobs.")

        except Exception as e:
            cls._last_status = "failed"
            cls._last_error = str(e)
            logger.error(f"Discovery pipeline failed: {e}", exc_info=True)
        finally:
            cls._is_running = False
