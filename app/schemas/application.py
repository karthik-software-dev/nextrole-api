from datetime import date, datetime
from pydantic import BaseModel, ConfigDict, Field

from schemas.job import JobSummaryOut


class ApplicationHistoryOut(BaseModel):
    """Audit log entry for an application status change."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    previous_status: str | None = None
    new_status: str
    changed_at: datetime
    note: str | None = None


class ApplicationCreateIn(BaseModel):
    """Request schema to track an application for a job."""

    job_id: int
    user_id: int = 1
    resume_version: str | None = None
    portal_type: str | None = None
    notes: str | None = None
    initial_status: str = "drafted"


class ApplicationUpdateIn(BaseModel):
    """Request schema to update application status, resume, or notes."""

    status: str | None = None
    resume_version: str | None = None
    portal_type: str | None = None
    notes: str | None = None
    follow_up_date: date | None = None
    note_for_history: str | None = None


class ApplicationOut(BaseModel):
    """Full application response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    job_id: int
    status: str
    applied_at: datetime | None = None
    resume_version: str | None = None
    portal_type: str | None = None
    notes: str | None = None
    follow_up_date: date | None = None
    is_active: bool = True
    job: JobSummaryOut | None = None
    history: list[ApplicationHistoryOut] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
