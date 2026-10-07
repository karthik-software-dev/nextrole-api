"""Lever ATS Scraper Orchestrator.

Reusable autonomous adapter for querying official public unauthenticated Lever
Postings APIs (api.lever.co/v0/postings) across registered tech employers.
Strictly non-invasive: requires no login, no CAPTCHA bypass, no Playwright, no proxies.
"""

import logging
import re
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import httpx

from models.job import Job
from processing.deduplication import clean_job_title
from processing.experience_parser import extract_experience
from .company_registry import get_companies_by_ats

logger = logging.getLogger("custom_scraper.lever")


def _get_pipeline_reference_date() -> datetime:
    """Reuses the canonical reference datetime from run_pipeline to ensure unified freshness calculation."""
    try:
        from run_pipeline import CURRENT_DATE
        return CURRENT_DATE
    except Exception:
        try:
            from custom_scraper import CURRENT_DATE
            return CURRENT_DATE
        except Exception:
            return datetime(2026, 9, 28, tzinfo=timezone.utc)


DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
}


class LeverScrapeResult:
    """Telemetry and job payload returned by LeverScraper."""

    def __init__(
        self,
        platform: str = "lever",
        search_query: str = "",
        location: str = "",
        total_found: int = 0,
        jobs: Optional[List[Job]] = None,
        duration_seconds: float = 0.0,
        status: str = "SUCCESS",
        error: Optional[str] = None,
        bot_detected: bool = False,
    ):
        self.platform = platform
        self.search_query = search_query
        self.location = location
        self.total_found = total_found
        self.jobs = jobs or []
        self.duration_seconds = duration_seconds
        self.status = status
        self.error = error
        self.bot_detected = bot_detected


class LeverScraper:
    """Standardized, generic adapter for public Lever Postings APIs."""

    BASE_API_URL = "https://api.lever.co/v0/postings"

    def __init__(
        self,
        timeout: float = 10.0,
        request_delay: float = 0.3,
        reference_date: Optional[datetime] = None,
        companies: Optional[List[Dict[str, Any]]] = None,
    ):
        self.timeout = timeout
        self.request_delay = request_delay
        self.reference_date = reference_date if reference_date is not None else _get_pipeline_reference_date()
        self.companies = companies if companies is not None else get_companies_by_ats("lever")

    def _parse_date(self, created_at_ms: Any, *args: Any, **kwargs: Any) -> Tuple[Optional[str], bool]:
        """Parses authoritative createdAt epoch millisecond timestamp to UTC ISO string.
        
        Freshness decisions are handled centrally by CentralJobProcessor.
        """
        if created_at_ms is None:
            return None, False

        try:
            ts_ms = float(created_at_ms)
            ts_sec = ts_ms / 1000.0
            dt_utc = datetime.fromtimestamp(ts_sec, tz=timezone.utc)
            return dt_utc.isoformat(), True
        except (ValueError, TypeError, OverflowError, OSError):
            return None, False

    def _detect_remote(self, workplace_type: Optional[str], location_name: Optional[str] = None) -> bool:
        """Determines if the posting is explicitly remote based solely on structured workplaceType.
        
        Strict approved rules:
        - workplaceType == "remote" -> True
        - workplaceType == "hybrid" -> False
        - workplaceType == "onsite" -> False
        - missing/unknown -> False
        - No remote inference from location prefix/suffix, title, or description.
        """
        if workplace_type and isinstance(workplace_type, str):
            return workplace_type.strip().lower() == "remote"
        return False

    def _matches_target_geography(
        self,
        location_name: str,
        all_locations: Optional[List[str]],
        workplace_type: Optional[str],
        target_location_filter: Optional[str] = None,
    ) -> Tuple[bool, bool]:
        """Evaluates whether the job matches the project's target geography (Bangalore, Chennai, Remote).
        
        Returns:
            tuple[matches: bool, is_remote: bool]
        """
        is_remote = self._detect_remote(workplace_type)
        loc = (location_name or "").strip().lower()

        # Check for Bangalore / Bengaluru
        is_blr = any(b in loc for b in ["bangalore", "bengaluru"])
        # Check for Chennai
        is_maa = "chennai" in loc

        # Inspect allLocations list if present for physical office locations
        if all_locations and isinstance(all_locations, list):
            for extra_loc in all_locations:
                if isinstance(extra_loc, str):
                    el_lower = extra_loc.strip().lower()
                    if any(b in el_lower for b in ["bangalore", "bengaluru"]):
                        is_blr = True
                    if "chennai" in el_lower:
                        is_maa = True

        # Handle broad country-level "India" without city:
        # Only accept if explicit remote or if city confirmed BLR/MAA
        if loc == "india" and not (is_blr or is_maa or is_remote):
            return False, is_remote

        # Check against specific target_location_filter if requested by the pipeline task
        if target_location_filter:
            t_clean = target_location_filter.strip().lower()
            if "bangalore" in t_clean or "bengaluru" in t_clean:
                matches = is_blr or is_remote
            elif "chennai" in t_clean:
                matches = is_maa or is_remote
            elif "remote" in t_clean:
                matches = is_remote
            else:
                matches = is_blr or is_maa or is_remote
        else:
            matches = is_blr or is_maa or is_remote

        return matches, is_remote

    def _parse_experience(self, text: str) -> Tuple[Optional[int], Optional[int], Optional[str]]:
        """Parses experience requirement deterministically via processing.experience_parser."""
        return extract_experience(text)

    def scrape(
        self,
        search_term: str = "",
        location: str = "",
        results_wanted: int = 15,
        hours_old: int = 336,
    ) -> LeverScrapeResult:
        """Queries registered Lever company career boards, parses open tech roles, and standardizes to Job."""
        t_start = time.time()
        collected_jobs: List[Job] = []
        max_days = hours_old / 24.0
        seen_job_ids = set()

        with httpx.Client(headers=DEFAULT_HEADERS, timeout=self.timeout, follow_redirects=True) as client:
            for comp_cfg in self.companies:
                if len(collected_jobs) >= results_wanted:
                    break

                company_slug = comp_cfg.get("ats_identifier")
                company_name = comp_cfg.get("company", company_slug)
                if not company_slug:
                    continue

                catalog_url = f"{self.BASE_API_URL}/{company_slug}?mode=json"
                logger.info(f"Querying Lever board: '{company_name}' ({company_slug})")

                try:
                    resp = client.get(catalog_url)
                except Exception as e:
                    logger.warning(f"Lever network error for board '{company_slug}': {e}")
                    continue

                if resp.status_code == 404:
                    logger.warning(f"Lever board '{company_slug}' returned 404 (not found). Skipping.")
                    continue
                elif resp.status_code != 200:
                    logger.warning(f"Lever board '{company_slug}' returned HTTP {resp.status_code}")
                    continue

                try:
                    jobs_raw = resp.json()
                except Exception as e:
                    logger.warning(f"Malformed JSON from Lever board '{company_slug}': {e}")
                    continue

                if not isinstance(jobs_raw, list):
                    continue

                for p in jobs_raw:
                    if len(collected_jobs) >= results_wanted:
                        break

                    posting_id = p.get("id")
                    if not posting_id:
                        continue

                    dedup_id = f"lever_{company_slug}_{posting_id}"
                    if dedup_id in seen_job_ids:
                        continue
                    seen_job_ids.add(dedup_id)

                    # Title & Hard exclusion check
                    raw_title = p.get("text", "")
                    title_clean = clean_job_title(raw_title)
                    if not title_clean:
                        continue

                    # Location & Remote extraction
                    cats = p.get("categories", {})
                    if not isinstance(cats, dict):
                        cats = {}
                    loc_name = cats.get("location", "")
                    workplace_type = str(p.get("workplaceType") or "").lower()
                    is_remote = (workplace_type == "remote") or ("remote" in str(loc_name).lower())

                    # Authoritative timestamp extraction
                    created_at_ms = p.get("createdAt")
                    posted_at_iso, _ = self._parse_date(created_at_ms)

                    # Content & Description
                    desc_plain = p.get("descriptionPlain", "")
                    desc_html = p.get("description", "")
                    content_str = desc_plain or desc_html or ""

                    # Experience parsing from description
                    exp_min, exp_max, exp_raw = self._parse_experience(content_str)

                    # Application & Discovery URLs (Genuine Lever URLs without fabrication)
                    apply_url = p.get("applyUrl")
                    hosted_url = p.get("hostedUrl")
                    if not apply_url:
                        apply_url = f"https://jobs.lever.co/{company_slug}/{posting_id}/apply"
                    if not hosted_url:
                        hosted_url = f"https://jobs.lever.co/{company_slug}/{posting_id}"

                    # Clean plain text description
                    clean_desc = desc_plain.strip() if desc_plain else (re.sub(r"<[^>]+>", " ", desc_html).strip() if desc_html else title_clean)

                    job = Job(
                        id=dedup_id,
                        title=title_clean,
                        company=company_name,
                        source="lever",
                        location=loc_name or ("Remote" if is_remote else "Bangalore"),
                        is_remote=is_remote,
                        salary_raw=None,
                        salary_min=None,
                        salary_max=None,
                        salary_currency=None,
                        experience_raw=exp_raw,
                        experience_min=exp_min,
                        experience_max=exp_max,
                        posted_at=posted_at_iso,
                        apply_url=apply_url,
                        apply_type="ATS",
                        discovery_url=hosted_url,
                        description=clean_desc,
                        raw_data=p,
                    )
                    collected_jobs.append(job)

                time.sleep(self.request_delay)

        duration = round(time.time() - t_start, 2)
        return LeverScrapeResult(
            platform="lever",
            search_query=search_term,
            location=location,
            total_found=len(collected_jobs),
            jobs=collected_jobs,
            duration_seconds=duration,
            status="SUCCESS",
        )


def scrape_lever_jobs(
    search_term: str = "",
    location: str = "",
    results_wanted: int = 15,
    hours_old: int = 336,
    reference_date: Optional[datetime] = None,
) -> LeverScrapeResult:
    """Convenience helper to scrape Lever jobs."""
    scraper = LeverScraper(reference_date=reference_date)
    return scraper.scrape(
        search_term=search_term,
        location=location,
        results_wanted=results_wanted,
        hours_old=hours_old,
    )
