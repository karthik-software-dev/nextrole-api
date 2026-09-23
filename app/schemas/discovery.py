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
