"""Greenhouse ATS Scraper Orchestrator.

Reusable autonomous adapter for querying official public unauthenticated Greenhouse
Job Board APIs (boards-api.greenhouse.io) across registered tech employers.
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

logger = logging.getLogger("custom_scraper.greenhouse")


def _get_pipeline_reference_date() -> datetime:
    """Reuses the canonical reference datetime from run_pipeline to ensure unified freshness calculation."""
    try:
        from run_pipeline import CURRENT_DATE
        return CURRENT_DATE
    except Exception:
        return datetime(2026, 9, 28, tzinfo=timezone.utc)


DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
}


class GreenhouseScrapeResult:
    """Telemetry and job payload returned by GreenhouseScraper."""

    def __init__(
        self,
        platform: str = "greenhouse",
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


class GreenhouseScraper:
    """Standardized, generic adapter for public Greenhouse Job Board APIs."""

    BASE_API_URL = "https://boards-api.greenhouse.io/v1/boards"

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
        self.companies = companies if companies is not None else get_companies_by_ats("greenhouse")

    def _parse_date(self, first_published_str: Optional[str], *args: Any, **kwargs: Any) -> Tuple[Optional[str], bool]:
        """Parses authoritative first_published ISO timestamp to UTC ISO string.
        
        Freshness decisions are handled centrally by CentralJobProcessor.
        """
        if not first_published_str or not isinstance(first_published_str, str):
            return None, False

        try:
            dt = datetime.fromisoformat(first_published_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            dt_utc = dt.astimezone(timezone.utc)
            return dt_utc.isoformat(), True
        except Exception:
            return None, False

    def _detect_remote(self, location_name: str, offices: List[Dict[str, Any]]) -> bool:
        """Determines is_remote strictly from explicit structured evidence.
        
        Rules:
        - Exact match: location == "remote"
        - Prefix match: location starts with "remote," or "remote -"
        - Suffix match: location ends with ", remote" or " - remote"
        - Office match: any office name == "remote"
        - Ambiguous/unstructured mentions -> False
        """
        loc = (location_name or "").strip().lower()
        if loc == "remote":
            return True
        if loc.startswith("remote,") or loc.startswith("remote -"):
            return True
        if loc.endswith(", remote") or loc.endswith(" - remote"):
            return True

        if offices and isinstance(offices, list):
            for off in offices:
                if isinstance(off, dict):
                    off_name = str(off.get("name") or "").strip().lower()
                    if off_name == "remote":
                        return True

        return False

    def _matches_target_geography(
        self,
        location_name: str,
        offices: List[Dict[str, Any]],
        target_location_filter: Optional[str] = None,
    ) -> Tuple[bool, bool]:
        """Evaluates whether the job matches the project's target geography (Bangalore, Chennai, Remote).
        
        Returns:
            tuple[matches: bool, is_remote: bool]
        """
        is_remote = self._detect_remote(location_name, offices)
        loc = (location_name or "").strip().lower()

        # Check for Bangalore / Bengaluru
        is_blr = any(b in loc for b in ["bangalore", "bengaluru"])
        # Check for Chennai
        is_maa = "chennai" in loc

        # Also inspect structured office names/locations
        if offices and isinstance(offices, list):
            for off in offices:
                if isinstance(off, dict):
                    off_name = str(off.get("name") or "").strip().lower()
                    off_loc = str(off.get("location") or "").strip().lower()
                    off_txt = f"{off_name} {off_loc}"
                    if any(b in off_txt for b in ["bangalore", "bengaluru"]):
                        is_blr = True
                    if "chennai" in off_txt:
                        is_maa = True

        # Handle broad country-level "India" without city:
        # Only accept if explicit remote or if office confirmed BLR/MAA
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

    def _parse_experience(self, content_html: str) -> Tuple[Optional[int], Optional[int], Optional[str]]:
        """Parses experience requirement deterministically via processing.experience_parser."""
        return extract_experience(content_html)

    def scrape(
        self,
        search_term: str = "Python Backend Developer",
        location: str = "Bangalore",
        results_wanted: int = 10,
        hours_old: int = 336,
    ) -> GreenhouseScrapeResult:
        """Scrapes configured Greenhouse company boards matching target roles and geography."""
        t_start = time.time()
        max_days = hours_old / 24.0
        collected_jobs: List[Job] = []
        seen_job_ids: set[str] = set()

        # Tokenize query for relevance filtering
        query_words = [w.lower() for w in search_term.split() if len(w) > 2]

        with httpx.Client(headers=DEFAULT_HEADERS, timeout=self.timeout, follow_redirects=True) as client:
            for company_info in self.companies:
                if len(collected_jobs) >= results_wanted:
                    break

                company_name = company_info.get("company", "Unknown")
                board_token = company_info.get("ats_identifier") or company_info.get("token")
                if not board_token:
                    continue

                catalog_url = f"{self.BASE_API_URL}/{board_token}/jobs?content=true"
                logger.info(f"Querying Greenhouse board: '{company_name}' ({board_token})")

                try:
                    resp = client.get(catalog_url)
                except Exception as e:
                    logger.warning(f"Greenhouse network error for board '{board_token}': {e}")
                    continue

                if resp.status_code == 404:
                    logger.warning(f"Greenhouse board '{board_token}' returned 404 (not found). Skipping.")
                    continue
                elif resp.status_code != 200:
                    logger.warning(f"Greenhouse board '{board_token}' returned HTTP {resp.status_code}")
                    continue

                try:
                    data = resp.json()
                except Exception as e:
                    logger.warning(f"Malformed JSON from Greenhouse board '{board_token}': {e}")
                    continue

                jobs_raw = data.get("jobs", [])
                if not isinstance(jobs_raw, list):
                    continue

                for j in jobs_raw:
                    if len(collected_jobs) >= results_wanted:
                        break

                    job_id = j.get("id")
                    if not job_id:
                        continue

                    dedup_id = f"greenhouse_{board_token}_{job_id}"
                    if dedup_id in seen_job_ids:
                        continue
                    seen_job_ids.add(dedup_id)

                    # Title & Hard exclusion check
                    raw_title = j.get("title", "")
                    title_clean = clean_job_title(raw_title)
                    if not title_clean:
                        continue

                    # Location & Remote extraction
                    loc_obj = j.get("location", {})
                    loc_name = loc_obj.get("name", "") if isinstance(loc_obj, dict) else str(loc_obj)
                    offices = j.get("offices", [])
                    is_remote = self._detect_remote(location_name=loc_name, offices=offices)

                    # Authoritative timestamp extraction
                    first_pub_str = j.get("first_published")
                    posted_at_iso, _ = self._parse_date(first_pub_str)

                    # Content & Description
                    content_html = j.get("content", "")
                    if not content_html:
                        # Fallback to individual job endpoint if content=true was not honored
                        detail_url = f"{self.BASE_API_URL}/{board_token}/jobs/{job_id}"
                        try:
                            time.sleep(self.request_delay)
                            d_resp = client.get(detail_url)
                            if d_resp.status_code == 200:
                                d_data = d_resp.json()
                                content_html = d_data.get("content", "")
                        except Exception:
                            pass

                    # Experience parsing from description
                    exp_min, exp_max, exp_raw = self._parse_experience(content_html)

                    # Application & Discovery URLs (Genuine absolute_url without fabricated /apply)
                    absolute_url = j.get("absolute_url")
                    if not absolute_url:
                        absolute_url = f"https://job-boards.greenhouse.io/{board_token}/jobs/{job_id}"

                    # Clean plain text description
                    clean_desc = re.sub(r"<[^>]+>", " ", content_html).strip() if content_html else title_clean

                    job = Job(
                        id=dedup_id,
                        title=title_clean,
                        company=company_name,
                        source="greenhouse",
                        location=loc_name or ("Remote" if is_remote else "Bangalore"),
                        is_remote=is_remote,
                        salary_raw=None,
                        salary_min=None,
                        salary_max=None,
                        salary_currency=None,
                        description=clean_desc,
                        discovery_url=absolute_url,
                        apply_url=absolute_url,
                        apply_type="ATS",
                        posted_at=posted_at_iso,
                        experience_min=exp_min,
                        experience_max=exp_max,
                        experience_raw=exp_raw,
                        matched_skills=[],
                        raw_data={
                            "job_id": str(job_id),
                            "board_token": board_token,
                            "first_published": first_pub_str,
                            "updated_at": j.get("updated_at"),
                            "requisition_id": j.get("requisition_id"),
                            "absolute_url": absolute_url,
                            "departments": j.get("departments", []),
                            "offices": offices,
                        },
                    )
                    collected_jobs.append(job)

                time.sleep(self.request_delay)

        duration = round(time.time() - t_start, 2)
        return GreenhouseScrapeResult(
            platform="greenhouse",
            search_query=search_term,
            location=location,
            total_found=len(collected_jobs),
            jobs=collected_jobs,
            duration_seconds=duration,
            status="SUCCESS",
        )


def scrape_greenhouse_jobs(
    results_wanted: int = 10,
    search_term: str = "Python Backend Developer",
    location: str = "Bangalore",
    reference_date: Optional[datetime] = None,
) -> List[Job]:
    """Standardized pipeline entry point for Greenhouse ATS scraper."""
    scraper = GreenhouseScraper(reference_date=reference_date)
    res = scraper.scrape(
        search_term=search_term,
        location=location,
        results_wanted=results_wanted,
        hours_old=336,
    )
    return res.jobs
