"""Hirist Scraper Orchestrator.

In-house autonomous scraper for Hirist (hirist.tech) using public structured JSON endpoints.
Leverages Gladiator API search and detail routes directly into canonical models.job.Job.
Strictly non-invasive: requires no login, no CAPTCHA bypass, no Playwright, and no private internal APIs.
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

logger = logging.getLogger("custom_scraper.hirist")

REFERENCE_DATE = datetime(2026, 9, 28, tzinfo=timezone.utc)

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Origin": "https://www.hirist.tech",
    "Referer": "https://www.hirist.tech/",
    "Accept-Language": "en-US,en;q=0.9",
}


class HiristScrapeResult:
    """Telemetry and job payload returned by HiristScraper."""

    def __init__(
        self,
        platform: str = "hirist",
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


class HiristScraper:
    """Autonomous Hirist scraper leveraging public Gladiator search and detail JSON APIs."""

    BASE_URL = "https://www.hirist.tech"
    API_BASE_URL = "https://gladiator.hirist.tech"

    def __init__(
        self,
        timeout: float = 15.0,
        request_delay: float = 0.3,
        reference_date: datetime | None = None,
    ):
        self.timeout = timeout
        self.request_delay = request_delay
        self.reference_date = reference_date or REFERENCE_DATE

    def _resolve_location_id(self, location: str) -> tuple[int | None, bool]:
        """Maps target location string to Hirist location ID and remote requirement.
        
        Hirist taxonomy:
        - Bangalore = 3
        - Chennai = 6
        - Remote = 132
        """
        loc_lower = (location or "").lower().strip()
        if "bangalore" in loc_lower or "bengaluru" in loc_lower:
            return 3, False
        if "chennai" in loc_lower:
            return 6, False
        if "remote" in loc_lower:
            return 132, True
        return None, False

    def scrape(
        self,
        search_term: str,
        location: str,
        results_wanted: int = 15,
        hours_old: int = 336,
    ) -> HiristScrapeResult:
        """Scrapes jobs from Hirist using search API, early freshness & exclusion filters, and detail enrichment."""
        t0 = time.time()
        loc_id, require_remote = self._resolve_location_id(location)
        max_days = hours_old / 24.0

        logger.info(
            f"Targeting Hirist search for '{search_term}' in '{location}' "
            f"(loc_id={loc_id}, require_remote={require_remote}, max_days={max_days})"
        )

        search_url = f"{self.API_BASE_URL}/job/search/"
        params: dict[str, Any] = {
            "query": search_term,
            "minexp": 1,
            "maxexp": 5,
            "page": 0,
            "size": min(max(results_wanted * 2, 20), 40),
        }
        if loc_id is not None:
            params["loc"] = loc_id

        try:
            with httpx.Client(headers=DEFAULT_HEADERS, follow_redirects=True, timeout=self.timeout) as client:
                resp = client.get(search_url, params=params)

                duration = round(time.time() - t0, 2)

                if (
                    resp.status_code == 403
                    or "<title>security check" in resp.text.lower()
                    or "cf-challenge" in resp.text.lower()
                    or "challenge-platform" in resp.text.lower()
                    or "just a moment..." in resp.text.lower()
                ):
                    logger.warning(f"Hirist bot challenge / 403 on {search_url}")
                    return HiristScrapeResult(
                        search_query=search_term,
                        location=location,
                        duration_seconds=duration,
                        status="BLOCKED",
                        error="Cloudflare challenge / 403",
                        bot_detected=True,
                    )

                if resp.status_code != 200:
                    logger.warning(f"Hirist returned status {resp.status_code} for {search_url}")
                    return HiristScrapeResult(
                        search_query=search_term,
                        location=location,
                        duration_seconds=duration,
                        status="FAILED",
                        error=f"HTTP {resp.status_code}",
                    )

                try:
                    data = resp.json()
                except Exception as e:
                    logger.error(f"Failed to parse Hirist JSON: {e}")
                    return HiristScrapeResult(
                        search_query=search_term,
                        location=location,
                        duration_seconds=duration,
                        status="FAILED",
                        error="Invalid JSON response",
                    )

                raw_jobs = data.get("data", [])
                if not raw_jobs:
                    logger.info(f"No jobs returned by Hirist for '{search_term}' in '{location}'")
                    return HiristScrapeResult(
                        search_query=search_term,
                        location=location,
                        total_found=0,
                        jobs=[],
                        duration_seconds=duration,
                        status="SUCCESS",
                    )

                # Step 2 & 3: Filter candidates by early freshness and lightweight exclusions
                surviving_items: list[dict[str, Any]] = []

                for item in raw_jobs:
                    surviving_items.append(item)
                    if len(surviving_items) >= results_wanted:
                        break

                # Step 4: Detail Enrichment & Canonical Job Creation
                candidate_jobs: list[Job] = []

                for item in surviving_items:
                    job_id_num = item.get("id")
                    job_id = f"hirist-{job_id_num}"
                    raw_title = item.get("title", "")

                    # Determine initial company name
                    comp_data = item.get("companyData") or {}
                    comp_name = (
                        comp_data.get("companyName")
                        or item.get("careerCompanyName")
                        or "Unknown Company"
                    ).strip()

                    # Handle titles formatted as "Company - Title" when company is placeholder
                    cleaned_title = raw_title
                    if (comp_name.lower() in ["hirist.tech", "unknown company", ""]) and " - " in raw_title:
                        parts = raw_title.split(" - ", 1)
                        comp_name = parts[0].strip()
                        cleaned_title = parts[1].strip()

                    cleaned_title = clean_job_title(cleaned_title)

                    # Location string
                    loc_objects = item.get("locations") or []
                    loc_names = [l.get("name") for l in loc_objects if isinstance(l, dict) and l.get("name")]
                    is_wfh = item.get("workFromHome") == 1
                    is_job_remote = is_wfh or any("remote" in ln.lower() for ln in loc_names) or loc_id == 132

                    if loc_names:
                        loc_str = ", ".join(loc_names)
                        if is_job_remote and "remote" not in loc_str.lower():
                            loc_str += " (Remote Okay)"
                    elif is_job_remote:
                        loc_str = "Remote"
                    else:
                        loc_str = location

                    # Dates
                    created_ms = item.get("createdTimeMs") or item.get("createdTime")
                    posted_date_str = None
                    if created_ms:
                        p_dt = datetime.fromtimestamp(created_ms / 1000.0, tz=timezone.utc)
                        posted_date_str = p_dt.strftime("%Y-%m-%d")

                    # Salary: hideSal == 1 -> None, hideSal == 0 -> valid positive values
                    hide_sal = item.get("hideSal", 1)
                    sal_min_val = item.get("minSal")
                    sal_max_val = item.get("maxSal")
                    salary_min = None
                    salary_max = None
                    salary_raw = None

                    if hide_sal == 0:
                        if sal_min_val is not None and float(sal_min_val) > 0:
                            salary_min = float(sal_min_val)
                        if sal_max_val is not None and float(sal_max_val) > 0:
                            salary_max = float(sal_max_val)
                        if salary_min and salary_max:
                            salary_raw = f"₹{salary_min:,.0f} - ₹{salary_max:,.0f}"
                        elif salary_min:
                            salary_raw = f"₹{salary_min:,.0f}+"
                        elif salary_max:
                            salary_raw = f"Up to ₹{salary_max:,.0f}"

                    # Experience
                    exp_min = item.get("min")
                    exp_max = item.get("max")
                    exp_raw_str = None
                    if exp_min is not None and exp_max is not None:
                        exp_raw_str = f"{exp_min}-{exp_max} years"
                    elif exp_min is not None:
                        exp_raw_str = f"{exp_min}+ years"

                    # Tags / Skills
                    tags_list = item.get("tags") or []
                    tag_names = [t.get("name") for t in tags_list if isinstance(t, dict) and t.get("name")]

                    # URLs
                    public_url = item.get("jobDetailUrl") or f"{self.BASE_URL}/j/{job_id_num}"
                    apply_url = item.get("applyUrl") or public_url

                    # Step 5: Detail enrichment for full HTML description and verified company
                    intro_text = ""
                    detail_raw = {}
                    if job_id_num:
                        try:
                            if self.request_delay > 0:
                                time.sleep(self.request_delay)
                            detail_url = f"{self.API_BASE_URL}/job/detail?jobcode={job_id_num}"
                            r_det = client.get(detail_url, timeout=min(self.timeout, 8.0))
                            if r_det.status_code == 200:
                                det_json = r_det.json()
                                detail_raw = det_json.get("data") or {}
                                intro_text = detail_raw.get("introText") or ""
                                det_comp = detail_raw.get("companyData", {}).get("companyName")
                                if det_comp and det_comp.lower() not in ["hirist.tech", "unknown company"]:
                                    comp_name = det_comp.strip()
                        except Exception as det_err:
                            logger.debug(f"Detail fetch failed for {job_id_num}, using search card: {det_err}")

                    # Description clean-up
                    desc_body = re.sub(r'<[^>]+>', ' ', intro_text).strip() if intro_text else ""
                    skills_header = f"Skills: {', '.join(tag_names)}" if tag_names else ""
                    if skills_header and desc_body:
                        full_description = f"{skills_header}\n\n{desc_body}"
                    elif desc_body:
                        full_description = desc_body
                    else:
                        full_description = skills_header

                    canonical_job = Job(
                        id=job_id,
                        title=cleaned_title,
                        company=comp_name,
                        source="hirist",
                        location=loc_str,
                        is_remote=is_job_remote,
                        salary_raw=salary_raw,
                        salary_min=salary_min,
                        salary_max=salary_max,
                        salary_currency="INR",
                        description=full_description,
                        discovery_url=public_url,
                        apply_url=apply_url,
                        apply_type="PLATFORM",
                        posted_at=posted_date_str,
                        experience_min=exp_min,
                        experience_max=exp_max,
                        experience_raw=exp_raw_str,
                        raw_data={
                            "hirist_id": job_id_num,
                            "createdTimeMs": created_ms,
                            "tags": tag_names,
                            "hideSal": hide_sal,
                            "workFromHome": item.get("workFromHome"),
                            "ats": detail_raw.get("ats") or item.get("ats"),
                            "creatorDomainName": detail_raw.get("creatorDomainName"),
                        },
                    )
                    candidate_jobs.append(canonical_job)

            duration = round(time.time() - t0, 2)
            logger.info(
                f"Hirist scrape complete: retrieved {len(candidate_jobs)} jobs "
                f"for '{search_term}' in '{location}' in {duration}s"
            )

            return HiristScrapeResult(
                platform="hirist",
                search_query=search_term,
                location=location,
                total_found=len(candidate_jobs),
                jobs=candidate_jobs,
                duration_seconds=duration,
                status="SUCCESS",
            )

        except Exception as e:
            duration = round(time.time() - t0, 2)
            logger.error(f"Hirist scrape failed for '{search_term}': {e}")
            return HiristScrapeResult(
                search_query=search_term,
                location=location,
                duration_seconds=duration,
                status="FAILED",
                error=str(e),
            )
