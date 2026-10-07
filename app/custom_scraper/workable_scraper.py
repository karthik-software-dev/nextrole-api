"""Workable ATS Scraper Orchestrator.

Reusable autonomous adapter for querying official public unauthenticated Workday/Workable
Candidate API (apply.workable.com/api/v3/accounts/{subdomain}/jobs) across registered tech employers.
Strictly non-invasive: requires no login, no CAPTCHA bypass, no Playwright, no proxies.
"""

import html
import logging
import re
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import httpx

from models.job import Job
from processing.deduplication import clean_job_title
from processing.experience_parser import extract_experience
from processing.relevance import HARD_EXCLUDE_TITLE_KEYWORDS, _has_keyword
from .company_registry import get_companies_by_ats

logger = logging.getLogger("custom_scraper.workable")


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
    "Accept": "application/json",
    "Content-Type": "application/json",
}


class WorkableScrapeResult:
    """Telemetry and job payload returned by WorkableScraper."""

    def __init__(
        self,
        platform: str = "workable",
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


class WorkableScraper:
    """Production-grade Workable ATS adapter leveraging public Candidate APIs."""

    def __init__(
        self,
        reference_date: Optional[datetime] = None,
        companies: Optional[List[Dict[str, Any]]] = None,
        timeout: float = 12.0,
        request_delay: float = 0.1,
    ):
        self.reference_date = reference_date or _get_pipeline_reference_date()
        self.companies = companies if companies is not None else get_companies_by_ats("workable")
        self.timeout = timeout
        self.request_delay = request_delay

    def _parse_authoritative_date(
        self,
        published_str: Optional[str],
        *args: Any,
        **kwargs: Any,
    ) -> Tuple[Optional[str], bool]:
        """Parses authoritative published ISO 8601 timestamp to UTC ISO string.
        
        Freshness decisions are handled centrally by CentralJobProcessor.
        """
        if not published_str or not isinstance(published_str, str):
            return None, False

        try:
            clean_str = published_str.strip().replace("Z", "+00:00")
            dt = datetime.fromisoformat(clean_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc).isoformat(), True
        except (ValueError, TypeError, OverflowError):
            return None, False

    def _detect_remote(self, workplace_enum: Optional[str], job_data: Dict[str, Any]) -> bool:
        """Determines remote status based strictly on Workable's structured workplace enum.
        
        Strict rules:
        - workplace == "remote" -> True
        - workplace == "hybrid" -> False
        - workplace == "on_site" -> False
        """
        wpt = str(workplace_enum or "").strip().lower()
        if wpt == "remote":
            return True
        if wpt in ["hybrid", "on_site", "onsite"]:
            return False

        if job_data.get("remote") is True:
            return True

        return False

    def _matches_target_geography(
        self,
        job_data: Dict[str, Any],
        is_remote: bool,
        target_location_filter: Optional[str] = None,
    ) -> Tuple[bool, bool]:
        """Evaluates whether the job matches the project's target geography (Bangalore, Chennai, Remote)."""
        city = str(job_data.get("city") or "").strip().lower()
        country = str(job_data.get("country") or "").strip().lower()
        state = str(job_data.get("state") or "").strip().lower()

        # Check secondary locations list if present
        all_locs = [f"{city} {state} {country}"]
        for loc_item in job_data.get("locations", []) or []:
            if isinstance(loc_item, dict):
                c = str(loc_item.get("city") or "").strip().lower()
                s = str(loc_item.get("state") or "").strip().lower()
                co = str(loc_item.get("country") or "").strip().lower()
                all_locs.append(f"{c} {s} {co}")

        combined = " ".join(all_locs)

        is_blr = any(b in combined for b in ["bangalore", "bengaluru"])
        is_maa = "chennai" in combined

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
        """Parses experience requirement deterministically from description text using canonical parser."""
        return extract_experience(text)

    def scrape(
        self,
        search_term: str = "",
        location: str = "",
        results_wanted: int = 15,
        hours_old: int = 336,
    ) -> WorkableScrapeResult:
        """Queries registered Workable employers, parses tech roles, and standardizes to Job."""
        t_start = time.time()
        collected_jobs: List[Job] = []
        max_days = hours_old / 24.0
        seen_job_ids = set()

        with httpx.Client(headers=DEFAULT_HEADERS, timeout=self.timeout, follow_redirects=True) as client:
            for comp in self.companies:
                if len(collected_jobs) >= results_wanted:
                    break

                company_name = comp.get("company", "Unknown")
                subdomain = comp.get("ats_identifier", "")

                if not subdomain:
                    logger.warning(f"Workable company '{company_name}' missing ats_identifier. Skipping.")
                    continue

                catalog_url = f"https://apply.workable.com/api/v3/accounts/{subdomain}/jobs"

                # Broad catalog retrieval: fetch company's open postings without narrow title constraint
                payload = {
                    "query": "",
                    "location": [],
                    "department": [],
                    "worktype": [],
                    "remote": [],
                }

                try:
                    resp = client.post(catalog_url, json=payload)
                except httpx.TimeoutException:
                    logger.warning(f"Workable catalog timeout for {company_name}")
                    continue
                except Exception as e:
                    logger.warning(f"Workable network error for {company_name}: {e}")
                    continue

                if resp.status_code == 404:
                    logger.warning(f"Workable subdomain '{subdomain}' returned 404. Skipping.")
                    continue
                elif resp.status_code == 429:
                    logger.warning(f"Workable rate limited (429) on '{subdomain}'. Skipping.")
                    continue
                elif resp.status_code != 200:
                    logger.warning(f"Workable catalog returned HTTP {resp.status_code} for {company_name}")
                    continue

                try:
                    data = resp.json()
                except Exception as e:
                    logger.warning(f"Malformed JSON from Workable for {company_name}: {e}")
                    continue

                results = data.get("results", [])
                if not isinstance(results, list):
                    continue

                for r in results:
                    if len(collected_jobs) >= results_wanted:
                        break

                    shortcode = r.get("shortcode")
                    if not shortcode:
                        continue

                    dedup_id = f"workable_{subdomain}_{shortcode}"
                    if dedup_id in seen_job_ids:
                        continue
                    seen_job_ids.add(dedup_id)

                    # Date parsing
                    published_str = r.get("published")
                    posted_at_iso, _ = self._parse_authoritative_date(published_str)

                    # Title extraction
                    raw_title = r.get("title", "")
                    title_clean = clean_job_title(raw_title)
                    if not title_clean:
                        continue

                    # Structured Remote Detection
                    wpt = r.get("workplace")
                    is_remote = self._detect_remote(wpt, r)

                    # Phase 2: Fetch detail endpoint for full description & structured compensation
                    detail_url = f"https://apply.workable.com/api/v1/accounts/{subdomain}/jobs/{shortcode}"
                    time.sleep(self.request_delay)
                    try:
                        det_resp = client.get(detail_url)
                    except Exception as e:
                        logger.warning(f"Error fetching detail for {title_clean} ({company_name}): {e}")
                        continue

                    if det_resp.status_code != 200:
                        logger.warning(f"Workable detail returned HTTP {det_resp.status_code} for {title_clean}")
                        continue

                    try:
                        det_data = det_resp.json()
                    except Exception as e:
                        logger.warning(f"Malformed detail JSON for {title_clean}: {e}")
                        continue

                    # Description extraction
                    desc_html = det_data.get("description", "") or ""
                    req_html = det_data.get("requirements", "") or ""
                    full_desc = f"{desc_html}\n{req_html}".strip()

                    clean_desc = re.sub(r"<[^>]+>", " ", full_desc).strip() if full_desc else title_clean
                    clean_desc = html.unescape(clean_desc)

                    # Experience parsing
                    exp_min, exp_max, exp_raw = self._parse_experience(clean_desc)

                    # Salary parsing from Workable structured fields
                    s_min = det_data.get("salary_from")
                    s_max = det_data.get("salary_to")
                    s_cur = det_data.get("salary_currency_iso_code") or "INR"
                    s_raw = None
                    if s_min is not None or s_max is not None:
                        s_raw = f"{s_cur} {s_min or ''} - {s_max or ''}".strip()

                    # Candidate apply URL
                    apply_url = f"https://apply.workable.com/{subdomain}/j/{shortcode}/"

                    city_disp = r.get("city") or ("Remote" if is_remote else "Bangalore")

                    job = Job(
                        id=dedup_id,
                        title=title_clean,
                        company=company_name,
                        source="workable",
                        location=str(city_disp),
                        is_remote=is_remote,
                        salary_raw=s_raw,
                        salary_min=float(s_min) if s_min is not None else None,
                        salary_max=float(s_max) if s_max is not None else None,
                        salary_currency=str(s_cur),
                        experience_raw=exp_raw,
                        experience_min=exp_min,
                        experience_max=exp_max,
                        posted_at=posted_at_iso,
                        apply_url=apply_url,
                        apply_type="ATS",
                        discovery_url=apply_url,
                        description=clean_desc,
                        ats_provider="workable",
                        raw_data=det_data,
                    )
                    collected_jobs.append(job)

        duration = round(time.time() - t_start, 2)
        return WorkableScrapeResult(
            platform="workable",
            search_query=search_term,
            location=location,
            total_found=len(collected_jobs),
            jobs=collected_jobs,
            duration_seconds=duration,
            status="SUCCESS",
        )


def scrape_workable_jobs(
    search_term: str = "",
    location: str = "",
    results_wanted: int = 15,
    hours_old: int = 336,
    reference_date: Optional[datetime] = None,
) -> WorkableScrapeResult:
    """Convenience helper to scrape Workable jobs."""
    scraper = WorkableScraper(reference_date=reference_date)
    return scraper.scrape(
        search_term=search_term,
        location=location,
        results_wanted=results_wanted,
        hours_old=hours_old,
    )
