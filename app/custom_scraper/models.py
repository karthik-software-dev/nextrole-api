"""Data models for custom scraper outputs."""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Optional


@dataclass
class JobItem:
    """Canonical representation of a scraped job listing."""

    id: str
    title: str
    company: str
    source: str = "indeed"
    location: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    is_remote: bool = False
    
    # Compensation
    salary_raw: Optional[str] = None
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    salary_currency: str = "INR"
    salary_period: Optional[str] = None  # YEAR, MONTH, HOUR
    
    # Description & Content
    description: Optional[str] = None
    description_html: Optional[str] = None
    
    # URLs
    discovery_url: Optional[str] = None
    apply_url: Optional[str] = None
    company_url: Optional[str] = None
    company_website: Optional[str] = None
    company_logo: Optional[str] = None
    
    # Dates & Metadata
    posted_at: Optional[str] = None
    job_type: Optional[str] = None
    experience_min: Optional[int] = None
    experience_max: Optional[int] = None
    experience_raw: Optional[str] = None
    
    # Company Extra
    company_employees: Optional[str] = None
    company_industry: Optional[str] = None
    
    # Tags & Raw
    tags: list[str] = field(default_factory=list)
    raw_data: dict[str, Any] = field(default_factory=dict, repr=False)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary without heavy raw_data."""
        d = asdict(self)
        d.pop("raw_data", None)
        return d


@dataclass
class ScraperResult:
    """Result summary for a scraping session."""

    platform: str
    search_query: str
    location: str
    total_found: int
    jobs: list[JobItem] = field(default_factory=list)
    duration_seconds: float = 0.0
    errors: list[str] = field(default_factory=list)
