from dataclasses import dataclass, field
from typing import Any


@dataclass
class Job:
    """Canonical internal representation of a job opportunity across all sources."""

    id: str
    title: str
    company: str
    source: str = "indeed"
    location: str | None = None
    is_remote: bool = False
    salary_raw: str | None = None
    description: str | None = None
    discovery_url: str | None = None
    apply_url: str | None = None
    posted_at: str | None = None
    relevance_score: float = 0.0
    matched_skills: list[str] = field(default_factory=list)
    duplicate_count: int = 1
    apply_type: str = "UNKNOWN"
    ats_provider: str | None = None
    priority_score: float = 0.0
    priority_tier: str = "TIER 3"
    experience_min: int | None = None
    experience_max: int | None = None
    experience_raw: str | None = None
    raw_data: dict[str, Any] = field(default_factory=dict, repr=False)
