from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from api.deps import get_db_session
from schemas.application import (
    ApplicationCreateIn,
    ApplicationOut,
    ApplicationUpdateIn,
)
from services.application_service import ApplicationService

router = APIRouter(prefix="/applications", tags=["Applications"])


@router.get(
    "",
    response_model=list[ApplicationOut],
    summary="List tracked applications with optional status filter",
)
def list_applications(
    status_filter: str | None = Query(None, alias="status", description="Filter by status (e.g. applied, interviewing)"),
    user_id: int = Query(1, description="User ID"),
    db: Session = Depends(get_db_session),
) -> list[ApplicationOut]:
    """Retrieves all tracked applications for the user."""
    return ApplicationService.list_applications(session=db, status=status_filter, user_id=user_id)


@router.post(
    "",
    response_model=ApplicationOut,
    status_code=status.HTTP_201_CREATED,
    summary="Track a new job application",
)
def create_application(
    payload: ApplicationCreateIn,
    db: Session = Depends(get_db_session),
) -> ApplicationOut:
    """Creates a new application entry for a canonical job."""
    try:
        return ApplicationService.create_application(session=db, data=payload)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.get(
    "/{application_id}",
    response_model=ApplicationOut,
    summary="Get application details and status audit timeline",
)
def get_application(
    application_id: int,
    db: Session = Depends(get_db_session),
) -> ApplicationOut:
    """Fetches application information, attached job details, and status history logs."""
    app = ApplicationService.get_application_by_id(session=db, application_id=application_id)
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application with ID {application_id} was not found.",
        )
    return app


@router.patch(
    "/{application_id}",
    response_model=ApplicationOut,
    summary="Update application status, notes, or resume",
)
def update_application(
    application_id: int,
    payload: ApplicationUpdateIn,
    db: Session = Depends(get_db_session),
) -> ApplicationOut:
    """Updates application details and appends transition event to audit history."""
    updated = ApplicationService.update_application(session=db, application_id=application_id, data=payload)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application with ID {application_id} was not found.",
        )
    return updated


@router.delete(
    "/job/{job_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete or unsave application for a job",
)
def delete_application_by_job(
    job_id: int,
    user_id: int = Query(1, description="User ID"),
    db: Session = Depends(get_db_session),
):
    """Deletes or un-saves a job application (primarily for drafted/saved opportunities)."""
    ApplicationService.delete_application_by_job_id(session=db, job_id=job_id, user_id=user_id)
    return None
