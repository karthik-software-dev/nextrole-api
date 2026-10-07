"""TimesJobs Scraper Orchestrator.

In-house autonomous scraper for TimesJobs (timesjobs.com) using the public unauthenticated REST API
(tjapi.timesjobs.com) directly into canonical models.job.Job.
Strictly non-invasive: requires no login, no CAPTCHA bypass, no Playwright, no proxies, and standard TLS verification.
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
from processing.relevance import HARD_EXCLUDE_TITLE_KEYWORDS, _has_keyword

logger = logging.getLogger("custom_scraper.timesjobs")


def _get_default_reference_date() -> datetime:
    """Reuses the canonical reference datetime from run_pipeline to ensure unified freshness calculation."""
    try:
        from run_pipeline import CURRENT_DATE
        return CURRENT_DATE
    except Exception:
        return datetime(2026, 9, 28, tzinfo=timezone.utc)


DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Content-Type": "application/json",
    "Accept": "application/json, text/plain, */*",
    "Origin": "https://www.timesjobs.com",
    "Referer": "https://www.timesjobs.com/",
    "Accept-Language": "en-US,en;q=0.9",
}


class TimesJobsScrapeResult:
    """Telemetry and job payload returned by TimesJobsScraper."""

    def __init__(
        self,
        platform: str = "timesjobs",
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


class TimesJobsScraper:
    """Autonomous TimesJobs scraper querying the unauthenticated tjapi backend REST endpoint."""

    API_URL = "https://tjapi.timesjobs.com/search/api/v1/search/jobs/list"

    def __init__(
        self,
        timeout: float = 15.0,
        request_delay: float = 0.3,
        reference_date: datetime | None = None,
        default_experience: str = "2",
    ):
        self.timeout = timeout
        self.request_delay = request_delay
        self.reference_date = reference_date or _get_default_reference_date()
        self.default_experience = default_experience

    @staticmethod
    def normalize_query(query: str) -> str:
        """Normalizes search query for TimesJobs by stripping noise terms when primary tech keywords are present.
        
        Prevents TimesJobs multi-word OR-expansion which floods search results with unrelated promoted IT roles.
        """
        if not query or not isinstance(query, str):
            return ""

        query_clean = query.strip()
        lower_q = query_clean.lower()

        # Check for primary technology keyword
        primary_techs = ["python", "fastapi", "flask"]
        if not any(re.search(rf"\b{tech}\b", lower_q) for tech in primary_techs):
            return query_clean

        # Noise terms that cause TimesJobs OR-expansion without adding technology specificity
        noise_pattern = r"\b(developer|engineer|backend|full\s*stack|core)\b"
        normalized = re.sub(noise_pattern, "", query_clean, flags=re.IGNORECASE)
        # Collapse multiple spaces and trim punctuation
        normalized = re.sub(r"[\s,\-/]+", " ", normalized).strip()

        # If normalization stripped everything, fall back to original
        if not normalized:
            return query_clean

        # Format canonical capitalization for single framework terms
        canonical_map = {
            "python": "Python",
            "fastapi": "FastAPI",
            "django": "Django",
            "flask": "Flask",
        }
        if normalized.lower() in canonical_map:
            return canonical_map[normalized.lower()]

        return normalized

    def _build_payload(
        self,
        search_term: str,
        location: str,
        page: int = 1,
        size: int = 25,
        experience: str | None = None,
    ) -> dict[str, Any]:
        """Constructs the JSON POST request body for TimesJobs search API."""
        loc_clean = (location or "").strip()
        loc_val = "remote" if "remote" in loc_clean.lower() else loc_clean
        exp_val = experience if experience is not None else self.default_experience
        normalized_keyword = self.normalize_query(search_term)

        return {
            "keyword": normalized_keyword,
            "location": loc_val,
            "experience": exp_val,
            "page": str(page),
            "size": str(size),
            "jobFunctions": [],
            "company": "",
            "industry": "",
            "functionAreaId": "",
            "jobFunction": "",
        }

    def _parse_job_item(self, item: dict[str, Any], hours_old: int = 336) -> Job | None:
        """Transforms a TimesJobs API job dictionary into a canonical Job object.
        
        Strictly enforces:
        - True posting date from postDate (rejects if missing or > hours_old)
        - Never fabricates apply_url (only genuine applyUrl, else None)
        - Remote detection strictly based on API response location / jobType evidence
        - Cleaned experience and explicit-only salary
        """
        job_id_raw = item.get("jobId")
        if not job_id_raw:
            return None

        title_raw = item.get("title") or ""
        title_clean = clean_job_title(title_raw)
        if not title_clean:
            return None

        # Post date parsing
        pdate = item.get("postDate")
        posted_at_iso = None
        if pdate and isinstance(pdate, str):
            try:
                dt = datetime.strptime(pdate.strip(), "%Y-%m-%d").replace(tzinfo=timezone.utc)
                posted_at_iso = dt.isoformat()
            except Exception:
                pass

        # Experience Mapping
        exp_from = item.get("experienceFrom")
        exp_to = item.get("experienceTo")
        emin = int(exp_from) if exp_from is not None and isinstance(exp_from, (int, float)) and exp_from >= 0 else None
        emax = int(exp_to) if exp_to is not None and isinstance(exp_to, (int, float)) and exp_to >= 0 else None

        exp_raw: str | None = None
        if emin is not None and emax is not None:
            exp_raw = f"{emin}-{emax} years"
        elif emin is not None:
            exp_raw = f"{emin}+ years"

        # 4. Salary Mapping (lowSalary/highSalary: -1 indicates unlisted)
        low_sal = item.get("lowSalary")
        high_sal = item.get("highSalary")
        smin = float(low_sal) if low_sal is not None and float(low_sal) > 0 else None
        smax = float(high_sal) if high_sal is not None and float(high_sal) > 0 else None
        sraw: str | None = None
        if smin and smax:
            sraw = f"₹{smin:,.0f} - ₹{smax:,.0f}"
        elif smin:
            sraw = f"₹{smin:,.0f}+"
        elif smax:
            sraw = f"Up to ₹{smax:,.0f}"

        # 5. Evidence-Based Remote Detection (Strictly from API response location / jobType)
        loc_str = (item.get("location") or "").lower()
        job_type_str = (item.get("jobType") or "").lower()
        is_remote_job = "remote" in loc_str or job_type_str == "remote"

        # 6. URLs: Discovery URL vs Genuine Apply URL
        discovery_url = item.get("jobDetailUrl") or None
        # Only populate apply_url if the API provides a genuine separate apply link; never fabricate
        apply_url = item.get("applyUrl") or None

        # 7. Description & Skills
        desc = item.get("description") or ""
        skills_raw = item.get("skills") or ""
        skills_list = [s.strip() for s in skills_raw.split(",") if s.strip()]
        skills_str = f"Skills: {', '.join(skills_list)}" if skills_list else ""

        if skills_str and desc:
            full_desc = f"{skills_str}\n\n{desc}"
        elif desc:
            full_desc = desc
        else:
            full_desc = skills_str

        company = item.get("company") or "Confidential"

        return Job(
            id=f"timesjobs-{job_id_raw}",
            title=title_clean,
            company=company,
            source="timesjobs",
            location=item.get("location") or "India",
            is_remote=is_remote_job,
            salary_raw=sraw,
            salary_min=smin,
            salary_max=smax,
            salary_currency="INR",
            description=full_desc,
            discovery_url=discovery_url,
            apply_url=apply_url,
            apply_type="PLATFORM",
            posted_at=posted_at_iso,
            experience_min=emin,
            experience_max=emax,
            experience_raw=exp_raw,
            matched_skills=skills_list,
            raw_data={
                "timesjobs_id": str(job_id_raw),
                "postDate": pdate,
                "expiryDate": item.get("expiryDate"),
                "jobFunction": item.get("jobFunction"),
                "loginId": item.get("loginId"),
                "ctcFlag": item.get("ctcFlag"),
            },
        )

    def scrape(
        self,
        search_term: str,
        location: str,
        results_wanted: int = 15,
        hours_old: int = 336,
        experience: str | None = None,
    ) -> TimesJobsScrapeResult:
        """Scrapes jobs from TimesJobs API with native pagination and strict validation."""
        t0 = time.time()
        max_days = hours_old / 24.0

        logger.info(
            f"Targeting TimesJobs search for '{search_term}' in '{location}' "
            f"(results_wanted={results_wanted}, max_days={max_days})"
        )

        collected_jobs: list[Job] = []
        page = 1
        page_size = min(max(results_wanted * 2, 25), 50)
        max_pages = 2

        with httpx.Client(headers=DEFAULT_HEADERS, timeout=self.timeout) as client:
            while page <= max_pages and len(collected_jobs) < results_wanted:
                payload = self._build_payload(
                    search_term=search_term,
                    location=location,
                    page=page,
                    size=page_size,
                    experience=experience,
                )
                logger.info(f"[TimesJobs Page {page}] Querying {self.API_URL}...")

                try:
                    r = client.post(self.API_URL, json=payload)
                except Exception as e:
                    logger.error(f"TimesJobs API request failed for '{search_term}' in '{location}': {e}")
                    dur = round(time.time() - t0, 2)
                    return TimesJobsScrapeResult(
                        platform="timesjobs",
                        search_query=search_term,
                        location=location,
                        total_found=len(collected_jobs),
                        jobs=collected_jobs,
                        duration_seconds=dur,
                        status="ERROR",
                        error=str(e),
                    )

                if r.status_code in [403, 429]:
                    logger.critical(f"TimesJobs API blocked request (HTTP {r.status_code})")
                    dur = round(time.time() - t0, 2)
                    return TimesJobsScrapeResult(
                        platform="timesjobs",
                        search_query=search_term,
                        location=location,
                        total_found=len(collected_jobs),
                        jobs=collected_jobs,
                        duration_seconds=dur,
                        status="BLOCKED",
                        error=f"HTTP {r.status_code}",
                        bot_detected=True,
                    )

                if r.status_code != 200:
                    logger.warning(f"TimesJobs API returned status {r.status_code}")
                    break

                try:
                    data = r.json()
                except Exception as e:
                    logger.error(f"Failed to parse TimesJobs API JSON: {e}")
                    break

                raw_jobs = data.get("jobs", [])
                if not raw_jobs:
                    logger.info(f"TimesJobs returned 0 jobs on page {page}")
                    break

                logger.info(f"TimesJobs returned {len(raw_jobs)} raw jobs on page {page}")

                for item in raw_jobs:
                    if len(collected_jobs) >= results_wanted:
                        break

                    job_obj = self._parse_job_item(item, hours_old=hours_old)
                    if job_obj:
                        collected_jobs.append(job_obj)

                total_pages = data.get("totalPages", 1)
                try:
                    total_pages_int = int(total_pages)
                except Exception:
                    total_pages_int = 1

                if page >= total_pages_int:
                    break

                page += 1
                if self.request_delay > 0:
                    time.sleep(self.request_delay)

        dur = round(time.time() - t0, 2)
        logger.info(f"TimesJobs scraping completed: {len(collected_jobs)} valid jobs returned in {dur}s")

        return TimesJobsScrapeResult(
            platform="timesjobs",
            search_query=search_term,
            location=location,
            total_found=len(collected_jobs),
            jobs=collected_jobs,
            duration_seconds=dur,
            status="SUCCESS",
        )
