"""Ashby ATS Scraper Orchestrator.

Reusable autonomous adapter for querying official public unauthenticated Ashby
Job Posting APIs (api.ashbyhq.com/posting-api/job-board/{slug}) across registered tech employers.
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

logger = logging.getLogger("custom_scraper.ashby")


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


class AshbyScrapeResult:
    """Telemetry and job payload returned by AshbyScraper."""

    def __init__(
        self,
        platform: str = "ashby",
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


class AshbyScraper:
    """Standardized, generic adapter for public Ashby Job Posting APIs."""

    BASE_API_URL = "https://api.ashbyhq.com/posting-api/job-board"

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
        self.companies = companies if companies is not None else get_companies_by_ats("ashby")

    def _parse_date(self, published_at_str: Optional[str], *args: Any, **kwargs: Any) -> Tuple[Optional[str], bool]:
        """Parses authoritative publishedAt ISO timestamp to UTC ISO string.
        
        Freshness decisions are handled centrally by CentralJobProcessor.
        """
        if not published_at_str or not isinstance(published_at_str, str):
            return None, False

        try:
            dt = datetime.fromisoformat(published_at_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            dt_utc = dt.astimezone(timezone.utc)
            return dt_utc.isoformat(), True
        except (ValueError, TypeError, OverflowError):
            return None, False

    def _detect_remote(self, is_remote: Optional[bool], workplace_type: Optional[str]) -> bool:
        """Determines if the posting is explicitly remote based solely on Ashby's structured fields.
        
        Strict approved rules:
        - isRemote is True -> True
        - workplaceType == "remote" -> True
        - workplaceType == "hybrid" -> False
        - workplaceType == "onpremises" / "onsite" -> False
        - missing/unknown -> False
        - No remote inference from location prefix/suffix, title, or description.
        """
        if is_remote is True:
            return True

        if workplace_type and isinstance(workplace_type, str):
            if workplace_type.strip().lower() == "remote":
                return True

        return False

    def _matches_target_geography(
        self,
        location_name: str,
        secondary_locations: Optional[List[Dict[str, Any]]],
        is_remote: bool,
        target_location_filter: Optional[str] = None,
    ) -> Tuple[bool, bool]:
        """Evaluates whether the job matches the project's target geography (Bangalore, Chennai, Remote).
        
        Returns:
            tuple[matches: bool, is_remote: bool]
        """
        loc = (location_name or "").strip().lower()

        # Check for Bangalore / Bengaluru
        is_blr = any(b in loc for b in ["bangalore", "bengaluru"])
        # Check for Chennai
        is_maa = "chennai" in loc

        # Inspect secondaryLocations if present
        if secondary_locations and isinstance(secondary_locations, list):
            for sl in secondary_locations:
                if isinstance(sl, dict):
                    sl_loc = str(sl.get("location") or "").strip().lower()
                    pa = sl.get("address", {}).get("postalAddress", {}) if isinstance(sl.get("address"), dict) else {}
                    sl_city = str(pa.get("addressLocality") or "").strip().lower()
                    sl_combined = f"{sl_loc} {sl_city}"

                    if any(b in sl_combined for b in ["bangalore", "bengaluru"]):
                        is_blr = True
                    if "chennai" in sl_combined:
                        is_maa = True

        # Handle broad country-level "India" without city:
        # Only accept if explicit remote or if verified city in BLR/MAA
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

    def _parse_compensation(self, comp_dict: Optional[Dict[str, Any]]) -> Tuple[Optional[int], Optional[int], Optional[str], Optional[str]]:
        """Parses structured salary compensation from Ashby's compensation payload.
        
        Returns:
            tuple[salary_min, salary_max, salary_currency, salary_raw]
        """
        if not comp_dict or not isinstance(comp_dict, dict):
            return None, None, None, None

        raw_summary = comp_dict.get("compensationTierSummary") or comp_dict.get("scrapeableCompensationSalarySummary")

        # Inspect summaryComponents for base salary
        components = comp_dict.get("summaryComponents", [])
        if isinstance(components, list):
            for comp in components:
                if isinstance(comp, dict) and comp.get("compensationType") == "Salary":
                    cur = comp.get("currencyCode")
                    min_val = comp.get("minValue")
                    max_val = comp.get("maxValue")

                    try:
                        s_min = int(min_val) if min_val is not None else None
                        s_max = int(max_val) if max_val is not None else None
                        s_cur = str(cur).upper() if cur else None
                        return s_min, s_max, s_cur, raw_summary
                    except (ValueError, TypeError):
                        pass

        # Inspect compensationTiers components fallback
        tiers = comp_dict.get("compensationTiers", [])
        if isinstance(tiers, list):
            for tier in tiers:
                if isinstance(tier, dict):
                    t_comps = tier.get("components", [])
                    if isinstance(t_comps, list):
                        for comp in t_comps:
                            if isinstance(comp, dict) and comp.get("compensationType") == "Salary":
                                cur = comp.get("currencyCode")
                                min_val = comp.get("minValue")
                                max_val = comp.get("maxValue")
                                try:
                                    s_min = int(min_val) if min_val is not None else None
                                    s_max = int(max_val) if max_val is not None else None
                                    s_cur = str(cur).upper() if cur else None
                                    return s_min, s_max, s_cur, raw_summary
                                except (ValueError, TypeError):
                                    pass

        return None, None, None, None

    def _parse_experience(self, text: str) -> Tuple[Optional[int], Optional[int], Optional[str]]:
        """Parses experience requirement deterministically via processing.experience_parser."""
        return extract_experience(text)

    def scrape(
        self,
        search_term: str = "",
        location: str = "",
        results_wanted: int = 15,
        hours_old: int = 336,
    ) -> AshbyScrapeResult:
        """Queries registered Ashby company career boards, parses open tech roles, and standardizes to Job."""
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

                catalog_url = f"{self.BASE_API_URL}/{company_slug}?includeCompensation=true"
                logger.info(f"Querying Ashby board: '{company_name}' ({company_slug})")

                try:
                    resp = client.get(catalog_url)
                except Exception as e:
                    logger.warning(f"Ashby network error for board '{company_slug}': {e}")
                    continue

                if resp.status_code == 404:
                    logger.warning(f"Ashby board '{company_slug}' returned 404 (not found). Skipping.")
                    continue
                elif resp.status_code != 200:
                    logger.warning(f"Ashby board '{company_slug}' returned HTTP {resp.status_code}")
                    continue

                try:
                    data = resp.json()
                except Exception as e:
                    logger.warning(f"Malformed JSON from Ashby board '{company_slug}': {e}")
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

                    dedup_id = f"ashby_{company_slug}_{job_id}"
                    if dedup_id in seen_job_ids:
                        continue
                    seen_job_ids.add(dedup_id)

                    # Exclude unlisted jobs deterministically
                    if j.get("isListed") is False:
                        continue

                    # Title & Hard exclusion check
                    raw_title = j.get("title", "")
                    title_clean = clean_job_title(raw_title)
                    if not title_clean:
                        continue

                    # Structured Remote Detection
                    is_remote_flag = j.get("isRemote")
                    workplace_type = j.get("workplaceType")
                    is_remote = self._detect_remote(is_remote_flag, workplace_type)

                    # Location string extraction
                    loc_name = j.get("location", "")

                    # Authoritative timestamp extraction
                    published_at_str = j.get("publishedAt")
                    posted_at_iso, _ = self._parse_date(published_at_str)

                    # Content & Description
                    desc_plain = j.get("descriptionPlain", "")
                    desc_html = j.get("descriptionHtml", "")
                    content_str = desc_plain or desc_html or ""

                    # Experience parsing from description
                    exp_min, exp_max, exp_raw = self._parse_experience(content_str)

                    # Compensation parsing
                    comp_data = j.get("compensation")
                    s_min, s_max, s_cur, s_raw = self._parse_compensation(comp_data)

                    # Application & Discovery URLs (Genuine Ashby URLs without fabrication)
                    apply_url = j.get("applyUrl")
                    job_url = j.get("jobUrl")
                    if not apply_url:
                        apply_url = f"https://jobs.ashbyhq.com/{company_slug}/{job_id}/application"
                    if not job_url:
                        job_url = f"https://jobs.ashbyhq.com/{company_slug}/{job_id}"

                    # Clean plain text description
                    clean_desc = desc_plain.strip() if desc_plain else (re.sub(r"<[^>]+>", " ", desc_html).strip() if desc_html else title_clean)

                    job = Job(
                        id=dedup_id,
                        title=title_clean,
                        company=company_name,
                        source="ashby",
                        location=loc_name or ("Remote" if is_remote else "Bangalore"),
                        is_remote=is_remote,
                        salary_raw=s_raw,
                        salary_min=s_min,
                        salary_max=s_max,
                        salary_currency=s_cur,
                        experience_raw=exp_raw,
                        experience_min=exp_min,
                        experience_max=exp_max,
                        posted_at=posted_at_iso,
                        apply_url=apply_url,
                        apply_type="ATS",
                        discovery_url=job_url,
                        description=clean_desc,
                        raw_data=j,
                    )
                    collected_jobs.append(job)

                time.sleep(self.request_delay)

        duration = round(time.time() - t_start, 2)
        return AshbyScrapeResult(
            platform="ashby",
            search_query=search_term,
            location=location,
            total_found=len(collected_jobs),
            jobs=collected_jobs,
            duration_seconds=duration,
            status="SUCCESS",
        )


def scrape_ashby_jobs(
    search_term: str = "",
    location: str = "",
    results_wanted: int = 15,
    hours_old: int = 336,
    reference_date: Optional[datetime] = None,
) -> AshbyScrapeResult:
    """Convenience helper to scrape Ashby jobs."""
    scraper = AshbyScraper(reference_date=reference_date)
    return scraper.scrape(
        search_term=search_term,
        location=location,
        results_wanted=results_wanted,
        hours_old=hours_old,
    )
