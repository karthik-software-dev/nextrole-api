from pydantic import BaseModel


class DiscoveryRunIn(BaseModel):
    """Parameters to trigger a background job discovery run."""

    source: str = "all"
    location: str = "all"
    use_cache: bool = True


class DiscoveryStatusOut(BaseModel):
    """Status of discovery engine scraper runs."""

    is_running: bool = False
    last_run_at: str | None = None
    last_status: str = "idle"
    last_jobs_found: int = 0
    last_jobs_synced: int = 0
    last_error: str | None = None
    last_duration_seconds: float = 0.0
    total_runs: int = 0


class DiscoverySourceOut(BaseModel):
    """Authoritative representation of a single job source engine."""

    id: int
    name: str
    slug: str
    engine_type: str
    status: str
    last_yield: int
    latency: str
    ats_detection: str
    enabled: bool
    priority: str
    total_scraped: int = 0
    tier1_count: int = 0
    last_synced_at: str | None = None


class DiscoveryLogOut(BaseModel):
    """Real-time log message emitted by the scraper engine."""

    id: str
    timestamp: str
    level: str
    tag: str
    message: str


