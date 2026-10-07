"""Cutshort Scraper Orchestrator.

In-house autonomous scraper for Cutshort using public server-rendered SEO and category pages.
Parses the initial Next.js React Query dehydrated state directly into canonical models.job.Job.
Strictly non-invasive: requires no login, no CAPTCHA bypass, and no private internal APIs.
"""

import json
import logging
import re
import time
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

from models.job import Job
from processing.deduplication import clean_job_title

logger = logging.getLogger("custom_scraper.cutshort")

REFERENCE_DATE = datetime(2026, 9, 28, tzinfo=timezone.utc)

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Sec-Ch-Ua": '"Chromium";v="130", "Google Chrome";v="130"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
}


class CutshortScrapeResult:
    """Telemetry and job payload returned by CutshortScraper."""

    def __init__(
        self,
        platform: str = "cutshort",
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


class CutshortScraper:
    """Autonomous Cutshort scraper leveraging pre-rendered Next.js React Query state."""

    BASE_URL = "https://cutshort.io"

    def __init__(
        self,
        timeout: float = 15.0,
        request_delay: float = 0.5,
    ):
        self.timeout = timeout
        self.request_delay = request_delay

    def _resolve_target_url(self, search_term: str, location: str) -> tuple[str, bool]:
        """Resolves target SEO page URL and remote-filtering requirement based on query and location."""
        loc_lower = (location or "").lower()
        query_lower = (search_term or "").lower()

        is_python_framework_or_backend = (
            any(k in query_lower for k in ["django", "fastapi", "flask"])
            or ("backend" in query_lower and ("python" in query_lower or "api" in query_lower))
        )
        is_remote = "remote" in loc_lower or "remote" in query_lower

        # Remote routing
        if is_remote:
            return f"{self.BASE_URL}/jobs/remote-python-jobs", True

        # Bangalore / Bengaluru routing
        if "bangalore" in loc_lower or "bengaluru" in loc_lower:
            if "backend" in query_lower or any(k in query_lower for k in ["ai", "machine learning", "ml", "genai", "fastapi"]):
                return f"{self.BASE_URL}/jobs/backend-developer-jobs-in-bangalore-bengaluru", False
            return f"{self.BASE_URL}/jobs/python-jobs-in-bangalore-bengaluru", False

        # Chennai routing
        if "chennai" in loc_lower:
            if "backend" in query_lower or any(k in query_lower for k in ["ai", "machine learning", "ml", "genai", "fastapi"]):
                return f"{self.BASE_URL}/jobs/backend-developer-jobs-in-chennai", False
            return f"{self.BASE_URL}/jobs/python-jobs-in-chennai", False

        # Default fallback
        if "backend" in query_lower or any(k in query_lower for k in ["ai", "machine learning", "ml", "genai", "fastapi"]):
            return f"{self.BASE_URL}/jobs/backend-developer-jobs-in-bangalore-bengaluru", False
        return f"{self.BASE_URL}/jobs/python-jobs-in-bangalore-bengaluru", False

    def scrape(
        self,
        search_term: str,
        location: str,
        results_wanted: int = 15,
        hours_old: int = 336,
    ) -> CutshortScrapeResult:
        """Scrapes jobs from Cutshort's server-rendered public pages."""
        t0 = time.time()
        target_url, require_remote = self._resolve_target_url(search_term, location)
        logger.info(f"Targeting Cutshort URL: {target_url} for '{search_term}' in '{location}' (require_remote={require_remote})")

        try:
            with httpx.Client(headers=DEFAULT_HEADERS, follow_redirects=True, timeout=self.timeout) as client:
                resp = client.get(target_url)

            duration = round(time.time() - t0, 2)

            if (
                resp.status_code == 403
                or "<title>security check" in resp.text.lower()
                or "cf-challenge" in resp.text.lower()
                or "challenge-platform" in resp.text.lower()
                or "just a moment..." in resp.text.lower()
            ):
                logger.warning(f"Cutshort challenge/block on {target_url}")
                return CutshortScrapeResult(
                    search_query=search_term,
                    location=location,
                    duration_seconds=duration,
                    status="BLOCKED",
                    error="Cloudflare challenge / 403",
                    bot_detected=True,
                )

            if resp.status_code != 200:
                logger.warning(f"Cutshort returned status {resp.status_code} for {target_url}")
                return CutshortScrapeResult(
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
                return CutshortScrapeResult(
                    search_query=search_term,
                    location=location,
                    duration_seconds=duration,
                    status="FAILED",
                    error="Missing __NEXT_DATA__ payload",
                )

            try:
                data = json.loads(m.group(1))
            except Exception as json_err:
                logger.warning(f"Failed to parse __NEXT_DATA__ JSON from {target_url}: {json_err}")
                return CutshortScrapeResult(
                    search_query=search_term,
                    location=location,
                    duration_seconds=duration,
                    status="FAILED",
                    error=f"Invalid JSON: {json_err}",
                )

            props = data.get("props") if isinstance(data, dict) else {}
            page_props = props.get("pageProps") if isinstance(props, dict) else {}
            dehydrated = page_props.get("dehydratedState") if isinstance(page_props, dict) else {}
            queries = dehydrated.get("queries", []) if isinstance(dehydrated, dict) else []

            raw_jobs: list[dict[str, Any]] = []
            if isinstance(queries, list):
                for q in queries:
                    if not isinstance(q, dict):
                        continue
                    state = q.get("state")
                    if not isinstance(state, dict):
                        continue
                    q_data = state.get("data")
                    if not isinstance(q_data, dict):
                        continue
                    inner_data = q_data.get("data")
                    if not isinstance(inner_data, dict):
                        continue
                    page_data = inner_data.get("pageData")
                    if not isinstance(page_data, dict):
                        continue
                    q_jobs = page_data.get("jobs")
                    if isinstance(q_jobs, list) and q_jobs:
                        raw_jobs = q_jobs
                        break

            if not raw_jobs:
                logger.info(f"No jobs found in dehydratedState for {target_url}")
                return CutshortScrapeResult(
                    search_query=search_term,
                    location=location,
                    total_found=0,
                    jobs=[],
                    duration_seconds=duration,
                    status="SUCCESS",
                )

            candidate_jobs: list[Job] = []

            for item in raw_jobs:
                if not isinstance(item, dict):
                    continue
                job_id = f"cs-{item.get('_id', 'unknown')}"
                raw_title = item.get("headline", "") or ""
                cleaned_title = clean_job_title(raw_title)

                company_details = item.get("companyDetails") if isinstance(item.get("companyDetails"), dict) else {}
                company_id = item.get("companyId") if isinstance(item.get("companyId"), dict) else {}

                co_name = (
                    company_details.get("name")
                    or company_id.get("name")
                    or "Unknown Company"
                ).strip()

                loc_list = item.get("locations") if isinstance(item.get("locations"), list) else []
                remote_type = item.get("remoteType") or ""
                is_job_remote = remote_type in ["remote_okay", "remote_only"]

                # Location formatting
                if loc_list:
                    loc_str = ", ".join(str(l) for l in loc_list if l)
                    if is_job_remote and "remote" not in loc_str.lower():
                        loc_str += " (Remote Okay)"
                elif is_job_remote:
                    loc_str = "Remote"
                else:
                    loc_str = location

                # Salary range
                sal_range = item.get("salaryRange") if isinstance(item.get("salaryRange"), dict) else {}
                sal_text = item.get("salaryRangeText")
                sal_min = float(sal_range.get("min", 0)) if sal_range.get("min") is not None else None
                sal_max = float(sal_range.get("max", 0)) if sal_range.get("max") is not None else None
                sal_currency = sal_range.get("currency", "INR") or "INR"

                # Experience range
                exp_range = item.get("expRange") if isinstance(item.get("expRange"), dict) else {}
                exp_min = exp_range.get("min")
                exp_max = exp_range.get("max")
                exp_raw_str = None
                if exp_min is not None and exp_max is not None:
                    exp_raw_str = f"{exp_min}-{exp_max} years"
                elif exp_min is not None:
                    exp_raw_str = f"{exp_min}+ years"

                # Description
                desc_html = item.get("sanitizedComment", "") or ""
                desc_text = re.sub(r'<[^>]+>', ' ', desc_html).strip()

                # Posted date (ISO timestamp)
                job_fact = item.get("jobFactSummary") if isinstance(item.get("jobFactSummary"), dict) else {}
                posted_iso_full = job_fact.get("postedDate")
                posted_date_str = None
                if posted_iso_full:
                    posted_date_str = str(posted_iso_full)[:10]  # YYYY-MM-DD

                # URLs
                public_url = item.get("publicUrl") or f"{self.BASE_URL}/job/{item.get('_id')}"
                apply_url = public_url

                skills = item.get("allSkills") if isinstance(item.get("allSkills"), list) else []
                company_links = company_details.get("links") if isinstance(company_details.get("links"), dict) else {}

                canonical_job = Job(
                    id=job_id,
                    title=cleaned_title,
                    company=co_name,
                    source="cutshort",
                    location=loc_str,
                    is_remote=is_job_remote,
                    salary_raw=sal_text,
                    salary_min=sal_min,
                    salary_max=sal_max,
                    salary_currency=sal_currency,
                    description=desc_text,
                    discovery_url=public_url,
                    apply_url=apply_url,
                    posted_at=posted_date_str,
                    experience_min=exp_min,
                    experience_max=exp_max,
                    experience_raw=exp_raw_str,
                    raw_data={
                        "cutshort_id": item.get("_id"),
                        "raw_posted_iso": posted_iso_full,
                        "posted_label": job_fact.get("postedDateLabel"),
                        "all_skills": skills,
                        "remote_type": remote_type,
                        "company_website": company_links.get("website"),
                        "company_size": company_details.get("size"),
                        "company_type": company_details.get("type"),
                    },
                )
                candidate_jobs.append(canonical_job)

            selected_jobs = candidate_jobs[:results_wanted]
            logger.info(f"Cutshort scrape complete: retrieved {len(selected_jobs)} jobs from {target_url} in {duration}s")

            return CutshortScrapeResult(
                platform="cutshort",
                search_query=search_term,
                location=location,
                total_found=len(candidate_jobs),
                jobs=selected_jobs,
                duration_seconds=duration,
                status="SUCCESS",
            )

        except Exception as e:
            duration = round(time.time() - t0, 2)
            logger.error(f"Cutshort scrape failed for '{search_term}': {e}")
            return CutshortScrapeResult(
                search_query=search_term,
                location=location,
                duration_seconds=duration,
                status="FAILED",
                error=str(e),
            )
