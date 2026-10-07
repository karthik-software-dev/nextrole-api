"""Adapter to convert custom scraper JobItem instances to Job Agent canonical Job models."""

from typing import Optional, Any
from .models import JobItem


def to_job_agent_model(item: JobItem, job_cls: Optional[Any] = None) -> Any:
    """Converts a JobItem into the Job Agent's internal Job dataclass.

    If job_cls is not supplied, dynamically imports Job from models.job.
    """
    if job_cls is None:
        try:
            from models.job import Job
            job_cls = Job
        except ImportError:
            # Fallback if models.job is not in sys.path
            return item.to_dict()

    return job_cls(
        id=item.id,
        title=item.title,
        company=item.company,
        source=item.source,
        location=item.location,
        is_remote=item.is_remote,
        salary_raw=item.salary_raw,
        salary_min=item.salary_min,
        salary_max=item.salary_max,
        salary_currency=item.salary_currency,
        description=item.description,
        discovery_url=item.discovery_url,
        apply_url=item.apply_url,
        posted_at=item.posted_at,
        experience_min=item.experience_min,
        experience_max=item.experience_max,
        experience_raw=item.experience_raw,
        raw_data=item.raw_data,
    )
