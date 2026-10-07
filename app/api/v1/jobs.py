from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from api.deps import get_db_session
from schemas.common import PaginatedResponse
from schemas.job import FilterCountsOut, JobDetailOut, JobSummaryOut
from services.job_service import JobService

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.get(
    "/filters",
    response_model=FilterCountsOut,
    summary="Get live filter counts for sidebar facets",
)
def get_job_filter_counts(
    db: Session = Depends(get_db_session),
) -> FilterCountsOut:
    """Returns dynamic counts for work modes, locations, experience, and salary bands."""
    return JobService.get_filter_counts(session=db)


@router.get(
    "",
    response_model=PaginatedResponse[JobSummaryOut],
    summary="List, search, and filter job opportunities",
)
def list_jobs(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    location: str | None = Query(None, description="Location bucket (BANGALORE, CHENNAI, OTHER)"),
    tier: str | None = Query(None, description="Priority tier filter (e.g. TIER 1, TIER 2)"),
    is_remote: bool | None = Query(None, description="Filter for remote positions"),
    work_mode: str | None = Query(None, description="Work mode filter (office, remote/wfh, hybrid, abroad)"),
    max_exp: int | None = Query(None, description="Max required experience in years (e.g. 3)"),
    min_score: float | None = Query(None, description="Minimum relevance score threshold"),
    search: str | None = Query(None, description="Search keyword in title, company, or description"),
    tag: str | None = Query(None, description="Filter by tag (e.g. FastAPI)"),
    active_only: bool = Query(True, description="Exclude soft-deleted / inactive jobs"),
    db: Session = Depends(get_db_session),
) -> PaginatedResponse[JobSummaryOut]:
    """Retrieves paginated, filtered, and ranked jobs."""
    return JobService.get_jobs(
        session=db,
        page=page,
        page_size=page_size,
        location_bucket=location,
        priority_tier=tier,
        is_remote=is_remote,
        work_mode=work_mode,
        max_exp=max_exp,
        min_score=min_score,
        search=search,
        tag=tag,
        active_only=active_only,
    )


@router.get(
    "/{job_id}",
    response_model=JobDetailOut,
    summary="Get complete details for a job opportunity",
)
def get_job(
    job_id: int,
    db: Session = Depends(get_db_session),
) -> JobDetailOut:
    """Fetches full job description, all discovery sources, and application status."""
    job = JobService.get_job_by_id(session=db, job_id=job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID {job_id} was not found.",
        )
    return job


@router.patch(
    "/{job_id}/deactivate",
    summary="Soft-delete/deactivate a job opportunity",
)
def deactivate_job(
    job_id: int,
    db: Session = Depends(get_db_session),
) -> dict[str, Any]:
    """Marks a job as inactive (soft-deleted). Data and history are preserved."""
    success = JobService.deactivate_job(session=db, job_id=job_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID {job_id} was not found.",
        )
    db.commit()
    return {
        "message": f"Job #{job_id} successfully deactivated (soft-deleted).",
        "job_id": job_id,
        "is_active": False,
    }
