"""Remotive Public API Scraper for Worldwide Remote Python & Backend Roles."""

import logging
from typing import List, Optional
import httpx

from .models import JobItem, ScraperResult
from processing.salary_parser import parse_salary

logger = logging.getLogger("custom_scraper.remotive")

REMOTIVE_API_URL = "https://remotive.com/api/remote-jobs"


class RemotiveScraper:
    """Fetches high-quality worldwide remote software jobs from Remotive's official API."""

    def __init__(self, timeout: float = 15.0):
        self.timeout = timeout

    def scrape(
        self,
        search_term: str = "python",
        category: str = "software-dev",
        results_wanted: int = 25,
        hours_old: Optional[int] = 336,
    ) -> ScraperResult:
        collected: List[JobItem] = []
        try:
            params = {
                "category": category,
                "search": search_term,
            }
            logger.info(f"[Remotive] Querying official API for '{search_term}'...")
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.get(REMOTIVE_API_URL, params=params)
                resp.raise_for_status()
                data = resp.json()

            raw_jobs = data.get("jobs", [])
            for item in raw_jobs:
                if len(collected) >= results_wanted:
                    break

                cand_loc = (item.get("candidate_required_location") or "").lower()
                # Accept Worldwide, Anywhere, Global, India, or open remote
                is_accessible = any(k in cand_loc for k in ["worldwide", "anywhere", "global", "all locations", "india", "remote", "apac", "emea", "latam"]) or not cand_loc

                # Exclude country-locked US/UK/Canada only roles if not open to worldwide
                is_locked = any(l in cand_loc for l in ["usa only", "us only", "uk only", "canada only", "united states only"]) and not any(w in cand_loc for w in ["worldwide", "anywhere"])
                if is_locked or not is_accessible:
                    continue

                sal_min, sal_max, sal_curr = parse_salary(item.get("salary"))

                job_item = JobItem(
                    id=f"remotive_{item.get('id')}",
                    title=item.get("title", "Software Engineer"),
                    company=item.get("company_name", "Global Startup"),
                    source="remotive",
                    location=item.get("candidate_required_location") or "Worldwide Remote",
                    is_remote=True,
                    salary_raw=item.get("salary"),
                    salary_min=sal_min,
                    salary_max=sal_max,
                    salary_currency=sal_curr,
                    description=item.get("description"),
                    discovery_url=item.get("url"),
                    apply_url=item.get("url"),
                    posted_at=item.get("publication_date"),
                    company_logo=item.get("company_logo"),
                    tags=item.get("tags", []),
                    raw_data=item,
                )
                collected.append(job_item)

            logger.info(f"[Remotive] Successfully fetched {len(collected)} worldwide remote jobs.")
            return ScraperResult(
                platform="remotive",
                search_query=search_term,
                location="Worldwide Remote",
                total_found=len(collected),
                jobs=collected,
            )
        except Exception as e:
            logger.error(f"[Remotive] Scrape failed: {e}")
            return ScraperResult(
                platform="remotive",
                search_query=search_term,
                location="Worldwide Remote",
                total_found=0,
                jobs=[],
                errors=[str(e)],
            )
