"""SmartRecruiters ATS Scraper Orchestrator.

Reusable autonomous adapter for querying official public unauthenticated SmartRecruiters
Candidate Experience REST APIs (api.smartrecruiters.com/v1/companies/{company}/postings)
across registered enterprise employers.
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

logger = logging.getLogger("custom_scraper.smartrecruiters")


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
}


class SmartRecruitersScrapeResult:
    """Telemetry and job payload returned by SmartRecruitersScraper."""

    def __init__(
        self,
        platform: str = "smartrecruiters",
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


class SmartRecruitersScraper:
    """Production-grade SmartRecruiters ATS adapter."""

    def __init__(
        self,
        reference_date: Optional[datetime] = None,
        companies: Optional[List[Dict[str, Any]]] = None,
        timeout: float = 12.0,
        request_delay: float = 0.1,
    ):
        self.reference_date = reference_date or _get_pipeline_reference_date()
        self.companies = companies if companies is not None else get_companies_by_ats("smartrecruiters")
        self.timeout = timeout
        self.request_delay = request_delay

    def _parse_authoritative_date(
        self,
        released_date_str: Optional[str],
        *args: Any,
        **kwargs: Any,
    ) -> Tuple[Optional[str], bool]:
        """Parses authoritative releasedDate ISO 8601 timestamp to UTC ISO string.
        
        Freshness decisions are handled centrally by CentralJobProcessor.
        """
        if not released_date_str or not isinstance(released_date_str, str):
            return None, False

        try:
            # Handle ISO string with trailing Z or offset
            clean_str = released_date_str.strip()
            if clean_str.endswith("Z"):
                clean_str = clean_str[:-1] + "+00:00"
            dt = datetime.fromisoformat(clean_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            dt_utc = dt.astimezone(timezone.utc)
            return dt_utc.isoformat(), True
        except (ValueError, TypeError, OverflowError):
            return None, False

    def _detect_remote(self, location_dict: Optional[Dict[str, Any]]) -> bool:
        """Determines remote status based solely on SmartRecruiters structured location payload.
        
        Strict rules:
        - location.remote is True -> True
        - location.hybrid is True -> False (hybrid is not fully remote)
        - Structured location string inspection fallback
        - No remote inference from title or description.
        """
        if not location_dict or not isinstance(location_dict, dict):
            return False

        if location_dict.get("remote") is True:
            return True

        if location_dict.get("hybrid") is True:
            return False

        # Structured location text pattern fallback
        city = str(location_dict.get("city") or "").strip().lower()
        region = str(location_dict.get("region") or "").strip().lower()
        full_loc = str(location_dict.get("fullLocation") or "").strip().lower()

        combined = f"{city} {region} {full_loc}"
        if (
            city == "remote"
            or city.startswith("remote -")
            or city.endswith("- remote")
            or "remote" in full_loc
        ):
            return True

        return False

    def _matches_target_geography(
        self,
        location_dict: Optional[Dict[str, Any]],
        is_remote: bool,
        target_location_filter: Optional[str] = None,
    ) -> Tuple[bool, bool]:
        """Evaluates whether the job matches the project's target geography (Bangalore, Chennai, Remote).
        
        Returns:
            tuple[matches: bool, is_remote: bool]
        """
        if not location_dict or not isinstance(location_dict, dict):
            return (True, True) if is_remote else (False, False)

        city = str(location_dict.get("city") or "").strip().lower()
        region = str(location_dict.get("region") or "").strip().lower()
        full_loc = str(location_dict.get("fullLocation") or "").strip().lower()
        country = str(location_dict.get("country") or "").strip().lower()

        combined = f"{city} {region} {full_loc}"

        is_blr = any(b in combined for b in ["bangalore", "bengaluru"])
        is_maa = "chennai" in combined

        # Country level India with no specific city:
        if (country in ["in", "india"] or full_loc == "india") and not (is_blr or is_maa or is_remote):
            return False, is_remote

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
    ) -> SmartRecruitersScrapeResult:
        """Queries registered SmartRecruiters employers, parses tech postings, and standardizes to Job."""
        t_start = time.time()
        collected_jobs: List[Job] = []
        max_days = hours_old / 24.0
        seen_job_ids = set()

        with httpx.Client(headers=DEFAULT_HEADERS, timeout=self.timeout, follow_redirects=True) as client:
            for comp in self.companies:
                if len(collected_jobs) >= results_wanted:
                    break

                company_name = comp.get("company", "Unknown")
                company_id = comp.get("ats_identifier", "")

                if not company_id:
                    logger.warning(f"SmartRecruiters company '{company_name}' missing ats_identifier. Skipping.")
                    continue

                # Broad query parameter: use Python for tech role discovery
                catalog_url = f"https://api.smartrecruiters.com/v1/companies/{company_id}/postings"
                params: Dict[str, Any] = {
                    "limit": 100,
                    "offset": 0,
                    "q": "Python",
                }

                try:
                    resp = client.get(catalog_url, params=params)
                except httpx.TimeoutException:
                    logger.warning(f"SmartRecruiters catalog timeout for {company_name}")
                    continue
                except Exception as e:
                    logger.warning(f"SmartRecruiters network error for {company_name}: {e}")
                    continue

                if resp.status_code == 404:
                    logger.warning(f"SmartRecruiters company '{company_id}' returned 404. Skipping.")
                    continue
                elif resp.status_code == 429:
                    logger.warning(f"SmartRecruiters rate limit (429) for '{company_id}'. Skipping.")
                    continue
                elif resp.status_code != 200:
                    logger.warning(f"SmartRecruiters catalog returned HTTP {resp.status_code} for {company_name}")
                    continue

                try:
                    data = resp.json()
                except Exception as e:
                    logger.warning(f"Malformed JSON from SmartRecruiters catalog for {company_name}: {e}")
                    continue

                postings = data.get("content", [])
                if not isinstance(postings, list):
                    continue

                for p in postings:
                    if len(collected_jobs) >= results_wanted:
                        break

                    posting_id = p.get("id")
                    if not posting_id:
                        continue

                    dedup_id = f"sr_{company_id}_{posting_id}"
                    if dedup_id in seen_job_ids:
                        continue
                    seen_job_ids.add(dedup_id)

                    # Authoritative timestamp extraction
                    released_date_str = p.get("releasedDate")
                    posted_at_iso, _ = self._parse_authoritative_date(released_date_str)

                    # Title extraction
                    raw_title = p.get("name", "")
                    title_clean = clean_job_title(raw_title)
                    if not title_clean:
                        continue

                    # Remote detection from structured location
                    loc_dict = p.get("location") or {}
                    is_remote = self._detect_remote(loc_dict)

                    # Detail API to retrieve complete jobAd sections and canonical applyUrl
                    detail_url = f"https://api.smartrecruiters.com/v1/companies/{company_id}/postings/{posting_id}"
                    time.sleep(self.request_delay)
                    try:
                        det_resp = client.get(detail_url)
                    except Exception as e:
                        logger.warning(f"Error fetching detail for {title_clean} ({company_name}): {e}")
                        continue

                    if det_resp.status_code != 200:
                        logger.warning(f"SmartRecruiters detail returned HTTP {det_resp.status_code} for {title_clean}")
                        continue

                    try:
                        det_data = det_resp.json()
                    except Exception as e:
                        logger.warning(f"Malformed detail JSON for {title_clean}: {e}")
                        continue

                    job_ad = det_data.get("jobAd", {})
                    sections = job_ad.get("sections", {}) if isinstance(job_ad, dict) else {}
                    desc_parts = []
                    for sec_key in ["jobDescription", "qualifications", "additionalInformation", "companyDescription"]:
                        sec = sections.get(sec_key, {})
                        if isinstance(sec, dict) and sec.get("text"):
                            desc_parts.append(sec.get("text"))
                    full_desc_html = "\n".join(desc_parts)

                    clean_desc = re.sub(r"<[^>]+>", " ", full_desc_html).strip() if full_desc_html else title_clean
                    clean_desc = html.unescape(clean_desc)

                    # Experience parsing
                    exp_min, exp_max, exp_raw = self._parse_experience(clean_desc)
                    if exp_min is not None and exp_min >= 5:
                        continue

                    # Application URLs
                    apply_url = det_data.get("applyUrl") or det_data.get("postingUrl") or f"https://jobs.smartrecruiters.com/{company_id}/{posting_id}"
                    discovery_url = det_data.get("postingUrl") or apply_url

                    loc_display = loc_dict.get("city") or loc_dict.get("fullLocation") or ("Remote" if is_remote else "Bangalore")

                    job = Job(
                        id=dedup_id,
                        title=title_clean,
                        company=company_name,
                        source="smartrecruiters",
                        location=str(loc_display),
                        is_remote=is_remote,
                        salary_raw=None,
                        salary_min=None,
                        salary_max=None,
                        salary_currency="INR",
                        experience_raw=exp_raw,
                        experience_min=exp_min,
                        experience_max=exp_max,
                        posted_at=posted_at_iso,
                        apply_url=apply_url,
                        apply_type="ATS",
                        discovery_url=discovery_url,
                        description=clean_desc,
                        ats_provider="smartrecruiters",
                        raw_data=det_data,
                    )
                    collected_jobs.append(job)

        duration = round(time.time() - t_start, 2)
        return SmartRecruitersScrapeResult(
            platform="smartrecruiters",
            search_query=search_term,
            location=location,
            total_found=len(collected_jobs),
            jobs=collected_jobs,
            duration_seconds=duration,
            status="SUCCESS",
        )


def scrape_smartrecruiters_jobs(
    search_term: str = "",
    location: str = "",
    results_wanted: int = 15,
    hours_old: int = 336,
    reference_date: Optional[datetime] = None,
) -> SmartRecruitersScrapeResult:
    """Convenience helper to scrape SmartRecruiters jobs."""
    scraper = SmartRecruitersScraper(reference_date=reference_date)
    return scraper.scrape(
        search_term=search_term,
        location=location,
        results_wanted=results_wanted,
        hours_old=hours_old,
    )
