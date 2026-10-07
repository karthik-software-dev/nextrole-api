"""Arbeitnow Public API Scraper for Global & European Remote Engineering Roles."""

from datetime import datetime, timezone
import logging
from typing import List, Optional
import httpx

from .models import JobItem, ScraperResult
from processing.salary_parser import parse_salary

logger = logging.getLogger("custom_scraper.arbeitnow")

ARBEITNOW_API_URL = "https://www.arbeitnow.com/api/job-board-api"


class ArbeitnowScraper:
    """Fetches remote software engineering jobs from Arbeitnow's official API."""

    def __init__(self, timeout: float = 15.0):
        self.timeout = timeout

    def scrape(
        self,
        search_term: str = "python",
        results_wanted: int = 25,
        hours_old: Optional[int] = 336,
    ) -> ScraperResult:
        collected: List[JobItem] = []
        try:
            logger.info(f"[Arbeitnow] Querying official API for '{search_term}'...")
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.get(ARBEITNOW_API_URL)
                resp.raise_for_status()
                data = resp.json()

            raw_jobs = data.get("data", [])
            term_lower = search_term.lower()

            for item in raw_jobs:
                if len(collected) >= results_wanted:
                    break

                is_remote = bool(item.get("remote", False))
                has_visa = bool(item.get("visa_sponsorship", False))
                # Only accept remote roles or explicit visa-sponsored roles
                if not is_remote and not has_visa:
                    continue

                title = item.get("title", "")
                desc = item.get("description", "")
                tags = [t.lower() for t in item.get("tags", [])]

                # Match search term in title, description, or tags
                matches_term = (
                    term_lower in title.lower()
                    or term_lower in desc.lower()
                    or any(term_lower in t for t in tags)
                )
                if not matches_term:
                    continue

                loc = item.get("location") or ("Remote" if is_remote else "Europe")
                loc_str = f"Global Remote ({loc})" if is_remote else loc

                created_ts = item.get("created_at")
                posted_iso = None
                if created_ts:
                    try:
                        posted_iso = datetime.fromtimestamp(created_ts, timezone.utc).isoformat()
                    except (ValueError, TypeError, OSError):
                        pass

                sal_min, sal_max, sal_curr = parse_salary(desc)

                job_item = JobItem(
                    id=f"arbeitnow_{item.get('slug', str(abs(hash(title))))}",
                    title=title,
                    company=item.get("company_name", "Tech Company"),
                    source="arbeitnow",
                    location=loc_str,
                    is_remote=is_remote,
                    salary_raw=None,
                    salary_min=sal_min,
                    salary_max=sal_max,
                    salary_currency=sal_curr,
                    description=desc,
                    discovery_url=item.get("url"),
                    apply_url=item.get("url"),
                    posted_at=posted_iso,
                    tags=item.get("tags", []),
                    raw_data=item,
                )
                collected.append(job_item)

            logger.info(f"[Arbeitnow] Successfully fetched {len(collected)} remote/visa jobs.")
            return ScraperResult(
                platform="arbeitnow",
                search_query=search_term,
                location="Worldwide Remote",
                total_found=len(collected),
                jobs=collected,
            )
        except Exception as e:
            logger.error(f"[Arbeitnow] Scrape failed: {e}")
            return ScraperResult(
                platform="arbeitnow",
                search_query=search_term,
                location="Worldwide Remote",
                total_found=0,
                jobs=[],
                errors=[str(e)],
            )
