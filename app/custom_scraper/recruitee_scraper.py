"""Recruitee ATS Scraper Orchestrator.

Reusable autonomous adapter for querying official public unauthenticated Recruitee
Offers APIs (https://{company}.recruitee.com/api/offers/) across registered tech employers.
Single-phase ingestion: retrieves complete job descriptions and metadata in a single request.
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

logger = logging.getLogger("custom_scraper.recruitee")


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


class RecruiteeScrapeResult:
    """Telemetry and job payload returned by RecruiteeScraper."""

    def __init__(
        self,
        platform: str = "recruitee",
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


class RecruiteeScraper:
    """Production-grade Recruitee ATS adapter leveraging single-phase public Offers API."""

    def __init__(
        self,
        reference_date: Optional[datetime] = None,
        companies: Optional[List[Dict[str, Any]]] = None,
        timeout: float = 12.0,
        request_delay: float = 0.1,
    ):
        self.reference_date = reference_date or _get_pipeline_reference_date()
        self.companies = companies if companies is not None else get_companies_by_ats("recruitee")
        self.timeout = timeout
        self.request_delay = request_delay

    def _parse_authoritative_date(
        self,
        published_at_str: Optional[str],
        *args: Any,
        **kwargs: Any,
    ) -> Tuple[Optional[str], bool]:
        """Parses authoritative published_at timestamp to UTC ISO string.
        
        Freshness decisions are handled centrally by CentralJobProcessor.
        """
        if not published_at_str or not isinstance(published_at_str, str):
            return None, False

        clean_str = published_at_str.strip()
        dt: Optional[datetime] = None

        # Format 1: "2026-09-28 15:15:25 UTC"
        if clean_str.endswith("UTC"):
            try:
                date_part = clean_str[:-3].strip()
                dt = datetime.strptime(date_part, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
            except Exception:
                pass

        # Format 2: ISO 8601
        if dt is None:
            try:
                iso_clean = clean_str.replace("Z", "+00:00")
                dt = datetime.fromisoformat(iso_clean)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
            except Exception:
                pass

        if dt is None:
            return None, False

        return dt.astimezone(timezone.utc).isoformat(), True

    def _detect_remote(self, offer: Dict[str, Any]) -> bool:
        """Determines remote status based solely on Recruitee's structured remote field."""
        if offer.get("remote") is True:
            return True

        # Check location fields fallback
        city = str(offer.get("city") or "").strip().lower()
        country = str(offer.get("country") or "").strip().lower()
        loc_str = str(offer.get("location") or "").strip().lower()

        combined = f"{city} {country} {loc_str}"
        if "remote" in combined:
            return True

        return False

    def _matches_target_geography(
        self,
        offer: Dict[str, Any],
        is_remote: bool,
        target_location_filter: Optional[str] = None,
    ) -> Tuple[bool, bool]:
        """Evaluates whether the job matches the project's target geography (Bangalore, Chennai, Remote)."""
        city = str(offer.get("city") or "").strip().lower()
        country = str(offer.get("country") or "").strip().lower()
        loc_str = str(offer.get("location") or "").strip().lower()

        combined = f"{city} {country} {loc_str}"

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
        """Parses experience requirement deterministically via processing.experience_parser."""
        return extract_experience(text)

    def scrape(
        self,
        search_term: str = "",
        location: str = "",
        results_wanted: int = 15,
        hours_old: int = 336,
    ) -> RecruiteeScrapeResult:
        """Queries registered Recruitee employers, parses tech offers, and standardizes to Job."""
        t_start = time.time()
        collected_jobs: List[Job] = []
        max_days = hours_old / 24.0
        seen_job_ids = set()

        with httpx.Client(headers=DEFAULT_HEADERS, timeout=self.timeout, follow_redirects=True) as client:
            for comp in self.companies:
                if len(collected_jobs) >= results_wanted:
                    break

                company_name = comp.get("company", "Unknown")
                slug = comp.get("ats_identifier", "")

                if not slug:
                    logger.warning(f"Recruitee employer '{company_name}' missing ats_identifier. Skipping.")
                    continue

                api_url = f"https://{slug}.recruitee.com/api/offers/"

                try:
                    resp = client.get(api_url)
                except httpx.TimeoutException:
                    logger.warning(f"Recruitee timeout for {company_name}")
                    continue
                except Exception as e:
                    logger.warning(f"Recruitee network error for {company_name}: {e}")
                    continue

                if resp.status_code == 404:
                    logger.warning(f"Recruitee slug '{slug}' for '{company_name}' returned 404. Skipping.")
                    continue
                elif resp.status_code == 429:
                    logger.warning(f"Recruitee rate limited (429) for '{company_name}'. Skipping.")
                    continue
                elif resp.status_code != 200:
                    logger.warning(f"Recruitee returned HTTP {resp.status_code} for {company_name}")
                    continue

                try:
                    data = resp.json()
                except Exception as e:
                    logger.warning(f"Malformed JSON from Recruitee for {company_name}: {e}")
                    continue

                offers = data.get("offers", [])
                if not isinstance(offers, list):
                    continue

                for o in offers:
                    if len(collected_jobs) >= results_wanted:
                        break

                    offer_id = o.get("id")
                    if not offer_id:
                        continue

                    # Only process published offers
                    status = str(o.get("status") or "").lower()
                    if status and status != "published":
                        continue

                    dedup_id = f"recruitee_{slug}_{offer_id}"
                    if dedup_id in seen_job_ids:
                        continue
                    seen_job_ids.add(dedup_id)

                    # Freshness: published_at preferred, fallback to created_at
                    pub_str = o.get("published_at") or o.get("created_at")
                    posted_at_iso, _ = self._parse_authoritative_date(pub_str)

                    # Title extraction
                    raw_title = o.get("title", "")
                    title_clean = clean_job_title(raw_title)
                    if not title_clean:
                        continue

                    # Remote detection from native boolean
                    is_remote = self._detect_remote(o)

                    # Description: embedded directly in the single-phase payload
                    desc_html = o.get("description", "") or ""
                    req_html = o.get("requirements", "") or ""
                    full_desc = f"{desc_html}\n{req_html}".strip()

                    clean_desc = re.sub(r"<[^>]+>", " ", full_desc).strip() if full_desc else title_clean
                    clean_desc = html.unescape(clean_desc)

                    # Experience parsing
                    exp_min, exp_max, exp_raw = self._parse_experience(clean_desc)
                    if exp_min is not None and exp_min >= 5:
                        continue

                    # Application & Discovery URLs
                    careers_url = o.get("careers_url") or f"https://{slug}.recruitee.com/o/{offer_id}"

                    city_disp = o.get("city") or o.get("location") or ("Remote" if is_remote else "Bangalore")

                    job = Job(
                        id=dedup_id,
                        title=title_clean,
                        company=company_name,
                        source="recruitee",
                        location=str(city_disp),
                        is_remote=is_remote,
                        salary_raw=None,
                        salary_min=None,
                        salary_max=None,
                        salary_currency="INR",
                        experience_raw=exp_raw,
                        experience_min=exp_min,
                        experience_max=exp_max,
                        posted_at=posted_at_iso,
                        apply_url=careers_url,
                        apply_type="ATS",
                        discovery_url=careers_url,
                        description=clean_desc,
                        ats_provider="recruitee",
                        raw_data=o,
                    )
                    collected_jobs.append(job)

                time.sleep(self.request_delay)

        duration = round(time.time() - t_start, 2)
        return RecruiteeScrapeResult(
            platform="recruitee",
            search_query=search_term,
            location=location,
            total_found=len(collected_jobs),
            jobs=collected_jobs,
            duration_seconds=duration,
            status="SUCCESS",
        )


def scrape_recruitee_jobs(
    search_term: str = "",
    location: str = "",
    results_wanted: int = 15,
    hours_old: int = 336,
    reference_date: Optional[datetime] = None,
) -> RecruiteeScrapeResult:
    """Convenience helper to scrape Recruitee jobs."""
    scraper = RecruiteeScraper(reference_date=reference_date)
    return scraper.scrape(
        search_term=search_term,
        location=location,
        results_wanted=results_wanted,
        hours_old=hours_old,
    )
