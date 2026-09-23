from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

from schemas.job import JobSummaryOut


class CompanyOut(BaseModel):
    """Company summary representation."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    normalized_name: str
    website: str | None = None
    career_url: str | None = None
    ats_provider: str | None = None
    is_target: bool = False
    is_active: bool = True
    active_jobs_count: int = 0
    created_at: datetime


class CompanyDetailOut(CompanyOut):
    """Company profile with list of currently active open vacancies."""

    open_jobs: list[JobSummaryOut] = Field(default_factory=list)
    metadata_json: dict = Field(default_factory=dict)
