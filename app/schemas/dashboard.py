from datetime import datetime
from pydantic import BaseModel


class LocationBreakdownOut(BaseModel):
    """Breakdown of opportunities by location quota bucket."""

    bangalore: int = 0
    chennai: int = 0
    remote: int = 0
    abroad: int = 0
    other: int = 0


class ApplicationStatusBreakdownOut(BaseModel):
    """Count of applications across hiring stages."""

    drafted: int = 0
    applied: int = 0
    under_review: int = 0
    interviewing: int = 0
    offered: int = 0
    rejected: int = 0


class SourceBreakdownItemOut(BaseModel):
    """Breakdown of discovered jobs by origin platform or ATS provider."""

    name: str
    count: int


class DiscoveryTrendItemOut(BaseModel):
    """Daily or periodic trend of discovered jobs."""

    date: str
    count: int


class LocationStatItemOut(BaseModel):
    """Aggregated opportunity counts by location name."""

    name: str
    count: int


class RecentActivityItemOut(BaseModel):
    """Real audit log or discovery event record."""

    id: str
    title: str
    description: str | None = None
    timestamp: datetime
    activity_type: str


from schemas.analytics import ExperienceDistributionOut, SalaryDistributionOut


class DashboardSummaryOut(BaseModel):
    """High-level metrics for dashboard cards and pipeline charts."""

    total_jobs: int
    active_jobs: int
    inactive_jobs: int
    tier1_jobs: int
    tier2_jobs: int
    total_companies: int
    total_sources: int
    location_breakdown: LocationBreakdownOut
    application_breakdown: ApplicationStatusBreakdownOut
    sources_breakdown: list[SourceBreakdownItemOut] = []
    new_jobs: int = 0
    discovery_trend: list[DiscoveryTrendItemOut] = []
    locations_breakdown: list[LocationStatItemOut] = []
    recent_activities: list[RecentActivityItemOut] = []
    experience_distribution: list[ExperienceDistributionOut] = []
    salary_distribution: list[SalaryDistributionOut] = []
