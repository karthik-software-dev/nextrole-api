from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class JobSourceOut(BaseModel):
    """Platform sighting details for a job."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    source_name: str
    source_job_id: str | None = None
    discovery_url: str | None = None
    source_apply_url: str | None = None
    source_posted_at: str | None = None
    first_seen_at: datetime
    last_seen_at: datetime


class JobCompanyOut(BaseModel):
    """Company summary attached to a job."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    normalized_name: str
    website: str | None = None
    career_url: str | None = None
    ats_provider: str | None = None
    is_target: bool = False


class JobSummaryOut(BaseModel):
    """Compact job representation for listing/feed views."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int
    company_name: str
    title: str
    location: str | None = None
    city: str | None = None
    location_bucket: str = "OTHER"
    is_remote: bool = False
    experience_min: int | None = None
    experience_max: int | None = None
    experience_raw: str | None = None
    salary_raw: str | None = None
    salary_min: float | None = None
    salary_max: float | None = None
    currency: str = "INR"
    canonical_apply_url: str | None = None
    apply_type: str = "UNKNOWN"
    ats_provider: str | None = None
    relevance_score: float = 0.0
    matched_skills: list[str] = Field(default_factory=list)
    priority_score: float = 0.0
    priority_tier: str = "TIER 3"
    match_percentage: int = 50
    status: str = "discovered"
    application_status: str | None = None
    source_count: int = 1
    is_active: bool = True
    tags: list[str] = Field(default_factory=list)
    description_snippet: str | None = None
    first_seen_at: datetime
    last_seen_at: datetime


class FilterCountItem(BaseModel):
    key: str
    label: str
    count: int


class FilterCountsOut(BaseModel):
    work_modes: list[FilterCountItem]
    locations: list[FilterCountItem]
    experience_buckets: list[FilterCountItem]
    salary_buckets: list[FilterCountItem]


class JobDetailOut(JobSummaryOut):
    """Comprehensive job details including full description and all discovery sources."""

    description: str | None = None
    company: JobCompanyOut | None = None
    sources: list[JobSourceOut] = Field(default_factory=list)
    application_status: str | None = None
    metadata_json: dict = Field(default_factory=dict)
