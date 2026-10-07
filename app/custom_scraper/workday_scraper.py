"""Workday ATS Scraper Orchestrator.

Reusable autonomous adapter for querying official public unauthenticated Workday
Candidate Experience Services (CXS) REST APIs across registered enterprise employers.
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
from .company_registry import get_companies_by_ats

logger = logging.getLogger("custom_scraper.workday")


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


class WorkdayScrapeResult:
    """Telemetry and job payload returned by WorkdayScraper."""

    def __init__(
        self,
        platform: str = "workday",
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


class WorkdayScraper:
    """Production-grade Workday ATS adapter leveraging public Candidate Experience Services (CXS)."""

    def __init__(
        self,
        reference_date: Optional[datetime] = None,
        companies: Optional[List[Dict[str, Any]]] = None,
        timeout: float = 12.0,
    ):
        self.reference_date = reference_date or _get_pipeline_reference_date()
        self.companies = companies if companies is not None else get_companies_by_ats("workday")
        self.timeout = timeout

    def _is_catalog_fresh(self, posted_on: Optional[str]) -> bool:
        """Pre-filters candidate listings based on relative postedOn string to avoid N+1 queries.
        
        Only allows listings that could plausibly be <= 7 days old.
        """
        if not posted_on or not isinstance(posted_on, str):
            return False

        p_lower = posted_on.strip().lower()

        # Reject obvious stale designations
        if "30+" in p_lower or "30 plus" in p_lower or "30 +" in p_lower:
            return False

        # Accept explicit fresh markers
        if any(k in p_lower for k in ["today", "yesterday"]):
            return True

        # Check for "Posted X Days Ago"
        m = re.search(r"posted\s+(\d+)\s+days?\s+ago", p_lower)
        if m:
            days = int(m.group(1))
            return days <= 7

        return False

    def _parse_authoritative_date(
        self,
        start_date_str: Optional[str],
        *args: Any,
        **kwargs: Any,
    ) -> Tuple[Optional[str], bool]:
        """Parses authoritative startDate (YYYY-MM-DD or ISO 8601) to UTC ISO string.
        
        Freshness decisions are handled centrally by CentralJobProcessor.
        """
        if not start_date_str or not isinstance(start_date_str, str):
            return None, False

        try:
            dt = datetime.fromisoformat(start_date_str.strip())
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            dt_utc = dt.astimezone(timezone.utc)
            return dt_utc.isoformat(), True
        except (ValueError, TypeError, OverflowError):
            return None, False

    def _detect_remote(
        self,
        location: Optional[str],
        additional_locations: Optional[List[str]],
    ) -> bool:
        """Determines if the posting is explicitly remote based solely on Workday structured location fields.
        
        Strict approved rules:
        - Evaluates only location and additionalLocations.
        - Checks for allowed structured enterprise patterns:
          'remote', 'remote - ...', 'remote, ...', 'remote/...', '... - remote',
          '... / remote', '...(remote)', 'offsite/home', 'virtual'.
        - No remote inference from job title or description.
        - Ambiguous cases strictly default to False.
        """
        candidates: List[str] = []
        if location and isinstance(location, str):
            candidates.append(location.strip().lower())
        if additional_locations and isinstance(additional_locations, list):
            for loc in additional_locations:
                if loc and isinstance(loc, str):
                    candidates.append(loc.strip().lower())

        for loc in candidates:
            if (
                loc == "remote"
                or loc.startswith("remote -")
                or loc.startswith("remote,")
                or loc.startswith("remote/")
                or loc.endswith("- remote")
                or loc.endswith("/ remote")
                or loc.endswith("(remote)")
                or "offsite/home" in loc
                or "virtual" in loc
            ):
                return True

        return False

    def _matches_target_geography(
        self,
        location: Optional[str],
        additional_locations: Optional[List[str]],
        is_remote: bool,
        target_location_filter: Optional[str] = None,
    ) -> Tuple[bool, bool]:
        """Evaluates whether the job matches the project's target geography (Bangalore, Chennai, Remote).
        
        Returns:
            tuple[matches: bool, is_remote: bool]
        """
        all_locs: List[str] = []
        if location and isinstance(location, str):
            all_locs.append(location.strip().lower())
        if additional_locations and isinstance(additional_locations, list):
            for al in additional_locations:
                if al and isinstance(al, str):
                    all_locs.append(al.strip().lower())

        combined_locs = " ".join(all_locs)

        # Check for Bangalore / Bengaluru
        is_blr = any(b in combined_locs for b in ["bangalore", "bengaluru"])
        # Check for Chennai
        is_maa = "chennai" in combined_locs

        # Handle broad country-level "India" without city:
        if combined_locs == "india" and not (is_blr or is_maa or is_remote):
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
        """Parses experience requirement deterministically from description text using canonical parser."""
        return extract_experience(text)

    def scrape(
        self,
        search_term: str = "",
        location: str = "",
        results_wanted: int = 15,
        hours_old: int = 336,
    ) -> WorkdayScrapeResult:
        """Queries registered Workday company career sites, parses open tech roles, and standardizes to Job."""
        t_start = time.time()
        collected_jobs: List[Job] = []
        max_days = hours_old / 24.0
        seen_job_ids = set()

        with httpx.Client(headers=DEFAULT_HEADERS, timeout=self.timeout, follow_redirects=True) as client:
            for comp in self.companies:
                if len(collected_jobs) >= results_wanted:
                    break

                company_name = comp.get("company", "Unknown")
                tenant = comp.get("ats_identifier", "")
                datacenter = comp.get("workday_datacenter", "")
                site = comp.get("workday_site", "")

                if not tenant or not datacenter or not site:
                    logger.warning(f"Workday employer '{company_name}' missing tenant, datacenter, or site parameter. Skipping.")
                    continue

                catalog_url = f"https://{tenant}.{datacenter}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs"
                base_site_url = f"https://{tenant}.{datacenter}.myworkdayjobs.com/wday/cxs/{tenant}/{site}"

                # Normalize query for Workday search index
                s_lower = (search_term or "").strip().lower()
                if "python" in s_lower:
                    base_kw = "Python"
                elif "fastapi" in s_lower or "flask" in s_lower or "api" in s_lower:
                    base_kw = "Python"
                elif "backend" in s_lower:
                    base_kw = "Backend"
                elif "engineer" in s_lower or "developer" in s_lower or "software" in s_lower:
                    base_kw = "Engineer"
                elif s_lower:
                    base_kw = search_term.strip()
                else:
                    base_kw = "Python"

                loc_clean = (location or "").strip()
                query_text = f"{base_kw} {loc_clean}" if loc_clean else base_kw

                catalog_payload = {
                    "appliedFacets": {},
                    "limit": 20,
                    "offset": 0,
                    "searchText": query_text,
                }

                try:
                    resp = client.post(catalog_url, json=catalog_payload)
                except httpx.TimeoutException:
                    logger.warning(f"Workday catalog request timed out for {company_name}")
                    continue
                except Exception as e:
                    logger.warning(f"Workday network error for {company_name}: {e}")
                    continue

                if resp.status_code == 404:
                    logger.warning(f"Workday site '{site}' for '{company_name}' returned 404. Skipping.")
                    continue
                elif resp.status_code == 422:
                    logger.warning(f"Workday parameters for '{company_name}' unprocessable (422). Skipping.")
                    continue
                elif resp.status_code == 429:
                    logger.warning(f"Workday rate limited (429) on '{company_name}'. Skipping.")
                    continue
                elif resp.status_code != 200:
                    logger.warning(f"Workday catalog returned HTTP {resp.status_code} for {company_name}")
                    continue

                try:
                    data = resp.json()
                except Exception as e:
                    logger.warning(f"Malformed JSON from Workday catalog for {company_name}: {e}")
                    continue

                job_postings = data.get("jobPostings", [])
                if not isinstance(job_postings, list):
                    continue

                for posting in job_postings:
                    if len(collected_jobs) >= results_wanted:
                        break

                    external_path = posting.get("externalPath")
                    if not external_path:
                        continue

                    # Preliminary Title check
                    raw_title = posting.get("title", "")
                    title_clean = clean_job_title(raw_title)
                    if not title_clean:
                        continue

                    # Phase 2: Fetch Detail API to obtain authoritative startDate, full description, and canonical apply URL
                    detail_url = f"{base_site_url}{external_path}"
                    try:
                        time.sleep(0.05)  # Polite execution delay between detail calls
                        det_resp = client.get(detail_url)
                    except Exception as e:
                        logger.warning(f"Error fetching detail for {title_clean} ({company_name}): {e}")
                        continue

                    if det_resp.status_code != 200:
                        logger.warning(f"Detail request returned HTTP {det_resp.status_code} for {title_clean}")
                        continue

                    try:
                        det_data = det_resp.json()
                    except Exception as e:
                        logger.warning(f"Malformed JSON in detail response for {title_clean}: {e}")
                        continue

                    job_info = det_data.get("jobPostingInfo", {})
                    if not isinstance(job_info, dict):
                        continue

                    # Authoritative timestamp extraction
                    start_date_str = job_info.get("startDate")
                    posted_at_iso, _ = self._parse_authoritative_date(start_date_str)

                    # Deduplication ID: prefer jobReqId, fallback to externalPath slug
                    job_req_id = job_info.get("jobReqId") or ""
                    if not job_req_id:
                        # Extract from bulletFields if available
                        bullet_fields = posting.get("bulletFields", [])
                        if bullet_fields and isinstance(bullet_fields, list):
                            job_req_id = str(bullet_fields[0]).strip()

                    if not job_req_id:
                        # Fallback to slug in externalPath
                        slug = external_path.rstrip("/").split("/")[-1]
                        job_req_id = slug

                    dedup_id = f"workday_{tenant}_{site}_{job_req_id}"
                    if dedup_id in seen_job_ids:
                        continue
                    seen_job_ids.add(dedup_id)

                    # Structured Remote Detection
                    detail_loc = job_info.get("location", "")
                    add_locs = job_info.get("additionalLocations", [])
                    is_remote = self._detect_remote(detail_loc, add_locs)

                    # Content & Description
                    desc_html = job_info.get("jobDescription", "")
                    clean_desc = re.sub(r"<[^>]+>", " ", desc_html).strip() if desc_html else title_clean
                    clean_desc = html.unescape(clean_desc)

                    # Experience parsing from description
                    exp_min, exp_max, exp_raw = self._parse_experience(clean_desc)
                    if exp_min is not None and exp_min >= 5:
                        # Seniority gate (Rule D)
                        continue

                    # Application & Discovery URLs (Genuine externalUrl without fabrication)
                    external_url = job_info.get("externalUrl")
                    if not external_url:
                        # Fallback to public portal URL constructed with exact externalPath
                        external_url = f"https://{tenant}.{datacenter}.myworkdayjobs.com/{site}{external_path}"

                    job = Job(
                        id=dedup_id,
                        title=title_clean,
                        company=company_name,
                        source="workday",
                        location=detail_loc or ("Remote" if is_remote else "Bangalore"),
                        is_remote=is_remote,
                        salary_raw=None,
                        salary_min=None,
                        salary_max=None,
                        salary_currency="INR",
                        experience_raw=exp_raw,
                        experience_min=exp_min,
                        experience_max=exp_max,
                        posted_at=posted_at_iso,
                        apply_url=external_url,
                        apply_type="ATS",
                        discovery_url=external_url,
                        description=clean_desc,
                        ats_provider="workday",
                        raw_data=job_info,
                    )
                    collected_jobs.append(job)

        duration = time.time() - t_start
        return WorkdayScrapeResult(
            platform="workday",
            search_query=search_term,
            location=location,
            total_found=len(collected_jobs),
            jobs=collected_jobs,
            duration_seconds=duration,
            status="SUCCESS",
        )


def scrape_workday_jobs(
    search_term: str = "",
    location: str = "",
    results_wanted: int = 15,
    hours_old: int = 336,
    reference_date: Optional[datetime] = None,
) -> WorkdayScrapeResult:
    """Convenience helper to scrape Workday jobs."""
    scraper = WorkdayScraper(reference_date=reference_date)
    return scraper.scrape(
        search_term=search_term,
        location=location,
        results_wanted=results_wanted,
        hours_old=hours_old,
    )

