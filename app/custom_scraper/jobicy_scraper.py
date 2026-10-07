"""Jobicy Public REST API Scraper for Worldwide Remote Python & Engineering Roles."""

import logging
from typing import List, Optional
import httpx

from .models import JobItem, ScraperResult
from processing.salary_parser import parse_salary

logger = logging.getLogger("custom_scraper.jobicy")

JOBICY_API_URL = "https://jobicy.com/api/v2/remote-jobs"


class JobicyScraper:
    """Fetches high-quality worldwide remote software jobs from Jobicy's official API."""

    def __init__(self, timeout: float = 15.0):
        self.timeout = timeout

    def scrape(
        self,
        search_term: str = "python",
        geo: str = "anywhere",
        results_wanted: int = 30,
        hours_old: Optional[int] = 336,
    ) -> ScraperResult:
        collected: List[JobItem] = []
        try:
            params = {
                "count": min(results_wanted * 2, 50),
                "geo": geo,
                "tag": search_term,
            }
            logger.info(f"[Jobicy] Querying official API for '{search_term}' (geo={geo})...")
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.get(JOBICY_API_URL, params=params)
                resp.raise_for_status()
                data = resp.json()

            raw_jobs = data.get("jobs", [])
            for item in raw_jobs:
                if len(collected) >= results_wanted:
                    break

                job_geo = item.get("jobGeo") or "Anywhere"
                geo_lower = job_geo.lower()

                # Filter for genuinely accessible remote locations (Anywhere, APAC, EMEA, Global, India)
                is_accessible = any(k in geo_lower for k in ["anywhere", "worldwide", "global", "india", "apac", "emea", "all locations"]) or not job_geo
                is_locked = any(l in geo_lower for l in ["usa only", "us only", "uk only", "canada only", "united states only"]) and not any(w in geo_lower for w in ["anywhere", "worldwide"])
                if is_locked or not is_accessible:
                    continue

                sal_min = item.get("annualSalaryMin")
                sal_max = item.get("annualSalaryMax")
                sal_curr = item.get("salaryCurrency") or "USD"
                sal_raw = None
                if sal_min or sal_max:
                    try:
                        s_min_f = float(sal_min) if sal_min else None
                        s_max_f = float(sal_max) if sal_max else None
                        if s_min_f and s_max_f:
                            sal_raw = f"${int(s_min_f):,} - ${int(s_max_f):,} {sal_curr} / yr"
                        elif s_max_f:
                            sal_raw = f"Up to ${int(s_max_f):,} {sal_curr} / yr"
                        elif s_min_f:
                            sal_raw = f"From ${int(s_min_f):,} {sal_curr} / yr"
                    except (ValueError, TypeError):
                        pass

                job_item = JobItem(
                    id=f"jobicy_{item.get('id')}",
                    title=item.get("jobTitle", "Software Engineer"),
                    company=item.get("companyName", "Tech Employer"),
                    source="jobicy",
                    location=f"Worldwide Remote ({job_geo})",
                    is_remote=True,
                    salary_raw=sal_raw,
                    salary_min=float(sal_min) if sal_min else None,
                    salary_max=float(sal_max) if sal_max else None,
                    salary_currency=sal_curr,
                    description=item.get("jobDescription") or item.get("jobExcerpt"),
                    discovery_url=item.get("url"),
                    apply_url=item.get("url"),
                    posted_at=item.get("pubDate"),
                    company_logo=item.get("companyLogo"),
                    tags=item.get("jobIndustry", []),
                    raw_data=item,
                )
                collected.append(job_item)

            logger.info(f"[Jobicy] Successfully fetched {len(collected)} worldwide remote jobs.")
            return ScraperResult(
                platform="jobicy",
                search_query=search_term,
                location="Worldwide Remote",
                total_found=len(collected),
                jobs=collected,
            )
        except Exception as e:
            logger.error(f"[Jobicy] Scrape failed: {e}")
            return ScraperResult(
                platform="jobicy",
                search_query=search_term,
                location="Worldwide Remote",
                total_found=0,
                jobs=[],
                errors=[str(e)],
            )
