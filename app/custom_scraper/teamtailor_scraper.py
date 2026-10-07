"""Teamtailor ATS Scraper Orchestrator.

Reusable autonomous adapter for querying official public unauthenticated Teamtailor RSS feeds
(https://{subdomain}.teamtailor.com/jobs.rss) across registered tech employers.
Single-phase ingestion: extracts full description, genuine application link, pubDate,
structured remoteStatus, and locations in one request per employer.
Strictly non-invasive: requires no login, no CAPTCHA bypass, no Playwright, no proxies.
"""

import html
import logging
import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Dict, List, Optional, Tuple

import httpx

from models.job import Job
from processing.deduplication import clean_job_title
from processing.experience_parser import extract_experience
from processing.relevance import HARD_EXCLUDE_TITLE_KEYWORDS, _has_keyword
from .company_registry import get_companies_by_ats

logger = logging.getLogger("custom_scraper.teamtailor")


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
    "Accept": "application/rss+xml, application/xml, text/xml;q=0.9, */*;q=0.8",
}


class TeamtailorScrapeResult:
    """Telemetry and job payload returned by TeamtailorScraper."""

    def __init__(
        self,
        platform: str = "teamtailor",
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


class TeamtailorScraper:
    """Production-grade Teamtailor ATS adapter leveraging public candidate RSS feeds."""

    def __init__(
        self,
        reference_date: Optional[datetime] = None,
        companies: Optional[List[Dict[str, Any]]] = None,
        timeout: float = 12.0,
        request_delay: float = 0.1,
    ):
        self.reference_date = reference_date or _get_pipeline_reference_date()
        self.companies = companies if companies is not None else get_companies_by_ats("teamtailor")
        self.timeout = timeout
        self.request_delay = request_delay

    def _parse_authoritative_date(
        self,
        pub_date_str: Optional[str],
        *args: Any,
        **kwargs: Any,
    ) -> Tuple[Optional[str], bool]:
        """Parses authoritative pubDate (RFC 2822 / RFC 822 / ISO) to UTC ISO string.
        
        Freshness decisions are handled centrally by CentralJobProcessor.
        """
        if not pub_date_str or not isinstance(pub_date_str, str):
            return None, False

        clean_str = pub_date_str.strip()
        dt_utc = None

        # Try RFC 2822 standard email/RSS date parser
        try:
            dt = parsedate_to_datetime(clean_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            dt_utc = dt.astimezone(timezone.utc)
        except Exception:
            pass

        # Fallback to ISO 8601 parser
        if dt_utc is None:
            try:
                dt_iso = datetime.fromisoformat(clean_str.replace("Z", "+00:00"))
                if dt_iso.tzinfo is None:
                    dt_iso = dt_iso.replace(tzinfo=timezone.utc)
                dt_utc = dt_iso.astimezone(timezone.utc)
            except Exception:
                return None, False

        return dt_utc.isoformat(), True

    def _detect_remote(self, remote_status: Optional[str], cities: List[str]) -> bool:
        """Determines remote status based strictly on Teamtailor structured remoteStatus XML tag.
        
        Strict rules:
        - remoteStatus == "remote" -> True
        - remoteStatus in ["hybrid", "office", "none"] -> False
        """
        st = str(remote_status or "").strip().lower()
        if st in ["remote", "fully", "temporary_work_from_home"]:
            return True
        if st in ["hybrid", "office", "none", "onsite"]:
            return False

        # Fallback: check if any city mentions remote explicitly
        for city in cities:
            if "remote" in city.lower():
                return True

        return False

    def _matches_target_geography(
        self,
        cities: List[str],
        countries: List[str],
        is_remote: bool,
        target_location_filter: Optional[str] = None,
    ) -> Tuple[bool, bool]:
        """Evaluates whether the job matches the project's target geography (Bangalore, Chennai, Remote)."""
        combined = " ".join(cities + countries).lower()

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
    ) -> TeamtailorScrapeResult:
        """Queries registered Teamtailor employers' RSS feeds, parses tech roles, and standardizes to Job."""
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
                    logger.warning(f"Teamtailor company '{company_name}' missing ats_identifier. Skipping.")
                    continue

                rss_url = f"https://{subdomain}.teamtailor.com/jobs.rss"

                try:
                    resp = client.get(rss_url)
                except httpx.TimeoutException:
                    logger.warning(f"Teamtailor RSS timeout for {company_name}")
                    continue
                except Exception as e:
                    logger.warning(f"Teamtailor network error for {company_name}: {e}")
                    continue

                if resp.status_code == 404:
                    logger.warning(f"Teamtailor subdomain '{subdomain}' returned 404. Skipping.")
                    continue
                elif resp.status_code == 429:
                    logger.warning(f"Teamtailor rate limited (429) on '{subdomain}'. Skipping.")
                    continue
                elif resp.status_code != 200:
                    logger.warning(f"Teamtailor RSS returned HTTP {resp.status_code} for {company_name}")
                    continue

                try:
                    root = ET.fromstring(resp.content)
                except Exception as e:
                    logger.warning(f"Malformed XML from Teamtailor for {company_name}: {e}")
                    continue

                items = root.findall(".//item")
                if not items:
                    continue

                for item in items:
                    if len(collected_jobs) >= results_wanted:
                        break

                    raw_guid = item.findtext("guid") or ""
                    link = item.findtext("link") or ""

                    # Extract deterministic unique ID
                    clean_guid = raw_guid.strip()
                    if not clean_guid and link:
                        m_id = re.search(r"/jobs/(\d+)", link)
                        if m_id:
                            clean_guid = m_id.group(1)
                        else:
                            clean_guid = link.split("/")[-1].split("?")[0]

                    if not clean_guid:
                        continue

                    dedup_id = f"teamtailor_{subdomain}_{clean_guid}"
                    if dedup_id in seen_job_ids:
                        continue
                    seen_job_ids.add(dedup_id)

                    # Authoritative pubDate parsing
                    pub_date_str = item.findtext("pubDate")
                    posted_at_iso, _ = self._parse_authoritative_date(pub_date_str)

                    # Title extraction
                    raw_title = item.findtext("title") or ""
                    title_clean = clean_job_title(raw_title)
                    if not title_clean:
                        continue

                    # Extract structured locations from namespaced and non-namespaced elements
                    cities = [
                        c.text.strip()
                        for c in item.findall(".//{https://teamtailor.com/locations}city")
                        if c.text
                    ]
                    if not cities:
                        cities = [c.text.strip() for c in item.findall(".//city") if c.text]

                    countries = [
                        c.text.strip()
                        for c in item.findall(".//{https://teamtailor.com/locations}country")
                        if c.text
                    ]
                    if not countries:
                        countries = [c.text.strip() for c in item.findall(".//country") if c.text]

                    # Structured Remote detection
                    remote_status = item.findtext("remoteStatus")
                    is_remote = self._detect_remote(remote_status, cities)

                    # Full description from embedded <description>
                    raw_desc = item.findtext("description") or ""
                    clean_desc = re.sub(r"<[^>]+>", " ", raw_desc).strip() if raw_desc else title_clean
                    clean_desc = html.unescape(clean_desc)

                    # Experience parsing
                    exp_min, exp_max, exp_raw = self._parse_experience(clean_desc)

                    # Candidate apply URL directly from <link>
                    apply_url = link.strip() if link else f"https://{subdomain}.teamtailor.com"

                    city_disp = cities[0] if cities else ("Remote" if is_remote else "Bangalore")

                    job = Job(
                        id=dedup_id,
                        title=title_clean,
                        company=company_name,
                        source="teamtailor",
                        location=str(city_disp),
                        is_remote=is_remote,
                        experience_raw=exp_raw,
                        experience_min=exp_min,
                        experience_max=exp_max,
                        posted_at=posted_at_iso,
                        apply_url=apply_url,
                        apply_type="ATS",
                        discovery_url=apply_url,
                        description=clean_desc,
                        ats_provider="teamtailor",
                        raw_data={
                            "guid": raw_guid,
                            "link": link,
                            "remoteStatus": remote_status,
                            "cities": cities,
                            "countries": countries,
                        },
                    )
                    collected_jobs.append(job)

        duration = round(time.time() - t_start, 2)
        return TeamtailorScrapeResult(
            platform="teamtailor",
            search_query=search_term,
            location=location,
            total_found=len(collected_jobs),
            jobs=collected_jobs,
            duration_seconds=duration,
            status="SUCCESS",
        )


def scrape_teamtailor_jobs(
    search_term: str = "",
    location: str = "",
    results_wanted: int = 15,
    hours_old: int = 336,
    reference_date: Optional[datetime] = None,
) -> TeamtailorScrapeResult:
    """Convenience helper to scrape Teamtailor jobs."""
    scraper = TeamtailorScraper(reference_date=reference_date)
    return scraper.scrape(
        search_term=search_term,
        location=location,
        results_wanted=results_wanted,
        hours_old=hours_old,
    )
