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


class DailyCadenceRunOut(BaseModel):
    """Execution status and job ingestion count for a scheduled daily runner window."""

    run_number: int
    time_slot: str
    label: str
    status: str
    jobs_collected: int
    cumulative_jobs: int
    runner: str = "GitHub Actions Runner"


class TopHiringCompanyOut(BaseModel):
    """Company with active hiring volume and job counts."""

    name: str
    job_count: int
    locations: list[str] = []
    is_remote: bool = False


class DedupEfficiencyOut(BaseModel):
    """Cross-source deduplication and spam suppression efficiency metrics."""

    canonical_jobs: int
    multi_source_jobs: int
    duplicates_filtered: int
    suppression_rate_pct: float


from schemas.analytics import ExperienceDistributionOut, SalaryDistributionOut


class PipelineStatusOut(BaseModel):
    """Execution status and metadata for GitLab CI / scraper pipeline."""

    id: int | None = None
    pipeline_id: str | None = None
    pipeline_iid: str | None = None
    pipeline_url: str | None = None
    source: str = "gitlab_ci"
    status: str = "idle"
    triggered_by: str | None = None
    jobs_collected: int = 0
    jobs_synced: int = 0
    duration_seconds: float | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


class DiscoverySpeedBucketOut(BaseModel):
    key: str
    label: str
    tag: str
    count: int
    percentage: float


class DiscoverySpeedOut(BaseModel):
    captured_under_4h_pct: float
    avg_latency_hours: float
    total_measured_jobs: int
    buckets: list[DiscoverySpeedBucketOut] = []


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
    new_tier1_jobs: int = 0
    discovery_trend: list[DiscoveryTrendItemOut] = []
    locations_breakdown: list[LocationStatItemOut] = []
    recent_activities: list[RecentActivityItemOut] = []
    experience_distribution: list[ExperienceDistributionOut] = []
    salary_distribution: list[SalaryDistributionOut] = []
    daily_cadence: list[DailyCadenceRunOut] = []
    top_hiring_companies: list[TopHiringCompanyOut] = []
    dedup_efficiency: DedupEfficiencyOut | None = None
    latest_pipeline: PipelineStatusOut | None = None
    discovery_speed: DiscoverySpeedOut | None = None


