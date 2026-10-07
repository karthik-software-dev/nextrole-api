"""Wellfound (formerly AngelList Talent) Scraper Orchestrator.

In-house autonomous scraper for Wellfound using public server-rendered SEO and location pages.
Parses the initial Next.js Apollo state directly into canonical models.job.Job.
Strictly non-invasive: requires no login, no CAPTCHA bypass, and no private GraphQL endpoints.
"""

import json
import logging
import re
import time
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

from models.job import Job
from processing.experience_parser import extract_experience
from processing.salary_parser import parse_salary
from processing.deduplication import clean_job_title

logger = logging.getLogger("custom_scraper.wellfound")

REFERENCE_DATE = datetime(2026, 9, 28, tzinfo=timezone.utc)

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Sec-Ch-Ua": '"Chromium";v="130", "Google Chrome";v="130"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
}

def format_company_size(size_str: str | None) -> str | None:
    """Converts Wellfound internal size enums to readable team size labels."""
    if not size_str:
        return None
    mapping = {
        "SIZE_1_10": "1-10 employees",
        "SIZE_11_50": "11-50 employees",
        "SIZE_51_200": "51-200 employees",
        "SIZE_201_500": "201-500 employees",
        "SIZE_501_1000": "501-1000 employees",
        "SIZE_1001_5000": "1001-5000 employees",
        "SIZE_5000_PLUS": "5000+ employees",
    }
    return mapping.get(size_str, size_str.replace("SIZE_", "").replace("_", "-").lower())


class WellfoundScrapeResult:
    """Telemetry and job payload returned by WellfoundScraper."""

    def __init__(
        self,
        platform: str = "wellfound",
        search_query: str = "",
        location: str = "",
        total_found: int = 0,
        jobs: list[Job] | None = None,
        duration_seconds: float = 0.0,
        status: str = "SUCCESS",
        error: str | None = None,
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


class WellfoundScraper:
    """Autonomous Wellfound scraper leveraging pre-rendered Next.js Apollo state."""

    BASE_URL = "https://wellfound.com"

    def __init__(
        self,
        timeout: float = 15.0,
        request_delay: float = 1.0,
    ):
        self.timeout = timeout
        self.request_delay = request_delay

    def _resolve_target_url(self, search_term: str, location: str) -> tuple[str, bool]:
        """Resolves target SEO page URL and remote-filtering requirement based on query and location."""
        loc_lower = (location or "").lower()
        query_lower = (search_term or "").lower()

        # Bangalore / Bengaluru routing
        if "bangalore" in loc_lower or "bengaluru" in loc_lower:
            if any(k in query_lower for k in ["ai", "llm", "rag", "genai", "machine learning"]):
                return f"{self.BASE_URL}/role/l/ai-engineer/bangalore", False
            if "backend" in query_lower or "fastapi" in query_lower:
                return f"{self.BASE_URL}/role/l/backend-developer/bangalore", False
            return f"{self.BASE_URL}/role/l/python-developer/bangalore", False

        # Chennai routing (Wellfound uses the historical city slug 'madras')
        if "chennai" in loc_lower or "madras" in loc_lower:
            if any(k in query_lower for k in ["ai", "llm", "rag", "genai", "machine learning"]):
                return f"{self.BASE_URL}/role/l/ai-engineer/madras", False
            if "backend" in query_lower or "fastapi" in query_lower:
                return f"{self.BASE_URL}/role/l/backend-developer/madras", False
            if "python" in query_lower:
                return f"{self.BASE_URL}/role/l/python-developer/madras", False
            return f"{self.BASE_URL}/location/madras", False

        # Remote routing
        if "remote" in loc_lower or "remote" in query_lower:
            if any(k in query_lower for k in ["ai", "llm", "rag", "genai", "machine learning"]):
                return f"{self.BASE_URL}/role/ai-engineer", True
            if "backend" in query_lower or "fastapi" in query_lower:
                return f"{self.BASE_URL}/role/backend-developer", True
            return f"{self.BASE_URL}/role/python-developer", True

        # Default fallback
        if "ai" in query_lower:
            return f"{self.BASE_URL}/role/ai-engineer", False
        return f"{self.BASE_URL}/role/python-developer", False

    def scrape(
        self,
        search_term: str,
        location: str,
        results_wanted: int = 15,
        hours_old: int = 336,
    ) -> WellfoundScrapeResult:
        """Scrapes jobs from Wellfound's server-rendered public pages."""
        t0 = time.time()
        target_url, require_remote = self._resolve_target_url(search_term, location)
        logger.info(f"Targeting Wellfound URL: {target_url} for '{search_term}' in '{location}' (require_remote={require_remote})")

        try:
            with httpx.Client(headers=DEFAULT_HEADERS, follow_redirects=True, timeout=self.timeout) as client:
                resp = client.get(target_url)

            duration = round(time.time() - t0, 2)

            if resp.status_code == 403 or "security check" in resp.text.lower():
                logger.warning(f"Wellfound challenge/block on {target_url}")
                return WellfoundScrapeResult(
                    search_query=search_term,
                    location=location,
                    duration_seconds=duration,
                    status="BLOCKED",
                    error="Cloudflare challenge / 403",
                    bot_detected=True,
                )

            if resp.status_code != 200:
                logger.warning(f"Wellfound returned status {resp.status_code} for {target_url}")
                return WellfoundScrapeResult(
                    search_query=search_term,
                    location=location,
                    duration_seconds=duration,
                    status="FAILED",
                    error=f"HTTP {resp.status_code}",
                )

            # Extract __NEXT_DATA__
            m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', resp.text, re.DOTALL)
            if not m:
                logger.warning(f"No __NEXT_DATA__ script found on {target_url}")
                return WellfoundScrapeResult(
                    search_query=search_term,
                    location=location,
                    duration_seconds=duration,
                    status="FAILED",
                    error="Missing __NEXT_DATA__ payload",
                )

            data = json.loads(m.group(1))
            apollo = data.get("props", {}).get("pageProps", {}).get("apolloState", {}).get("data", {})

            # Map Startups by ref
            startups = {k: v for k, v in apollo.items() if isinstance(v, dict) and v.get("__typename") == "StartupResult"}

            candidate_jobs: list[Job] = []

            for s_key, s_data in startups.items():
                co_name = s_data.get("name", "Unknown Startup")
                co_slug = s_data.get("slug", "")
                co_desc = s_data.get("highConcept", "")
                co_size = s_data.get("companySize", "")

                for jref in s_data.get("highlightedJobListings", []):
                    job_key = jref.get("__ref", "")
                    j = apollo.get(job_key, {})
                    if not j or j.get("__typename") != "JobListingSearchResult":
                        continue

                    # Remote & Location extraction
                    is_job_remote = bool(j.get("remote", False) or any("remote" in l.lower() for l in j.get("locationNames", [])))
                    loc_names = j.get("locationNames", [])

                    job_id = f"wf-{j.get('id', 'unknown')}"
                    slug = j.get("slug", "")
                    job_url = f"{self.BASE_URL}/jobs/{j.get('id')}-{slug}" if slug else f"{self.BASE_URL}/jobs/{j.get('id')}"

                    title = clean_job_title(j.get("title", ""))
                    loc_str = ", ".join(loc_names) if loc_names else ("Remote" if is_job_remote else location)

                    desc = j.get("description", "") or ""
                    if co_desc:
                        desc = f"{co_desc}. {desc}".strip()

                    # Posted date from liveStartAt Unix timestamp
                    live_start = j.get("liveStartAt")
                    posted_at_iso = None
                    if live_start and isinstance(live_start, (int, float)):
                        posted_at_iso = datetime.fromtimestamp(live_start, tz=timezone.utc).strftime("%Y-%m-%d")

                    comp = j.get("compensation", "")
                    sal_min, sal_max, _ = parse_salary(comp) if comp else (None, None, "INR")

                    exp_min = j.get("yearsExperienceMin")
                    exp_max = j.get("yearsExperienceMax")
                    exp_raw = None
                    if exp_min is not None and exp_max is not None:
                        exp_raw = f"{exp_min}-{exp_max} years"
                    elif exp_min is not None:
                        exp_raw = f"{exp_min}+ years"

                    canonical_job = Job(
                        id=job_id,
                        title=title,
                        company=co_name,
                        location=loc_str,
                        is_remote=is_job_remote,
                        description=desc,
                        salary_raw=comp if comp else None,
                        salary_min=sal_min,
                        salary_max=sal_max,
                        experience_raw=exp_raw,
                        experience_min=exp_min,
                        experience_max=exp_max,
                        apply_url=job_url,
                        discovery_url=job_url,
                        source="wellfound",
                        posted_at=posted_at_iso,
                        matched_skills=[],
                        raw_data={
                            "ats_source": j.get("atsSource"),
                            "company_size": co_size,
                            "company_size_label": format_company_size(co_size),
                            "live_start_at": live_start,
                        },
                    )
                    candidate_jobs.append(canonical_job)

            selected_jobs = candidate_jobs[:results_wanted]
            logger.info(f"Wellfound scrape complete: retrieved {len(selected_jobs)} jobs from {target_url} in {duration}s")

            return WellfoundScrapeResult(
                platform="wellfound",
                search_query=search_term,
                location=location,
                total_found=len(candidate_jobs),
                jobs=selected_jobs,
                duration_seconds=duration,
                status="SUCCESS",
            )

        except Exception as e:
            duration = round(time.time() - t0, 2)
            logger.error(f"Wellfound scrape failed for '{search_term}': {e}")
            return WellfoundScrapeResult(
                search_query=search_term,
                location=location,
                duration_seconds=duration,
                status="FAILED",
                error=str(e),
            )
