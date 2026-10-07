"""Y Combinator "Work at a Startup" Scraper Orchestrator.

In-house autonomous scraper for early-stage Y Combinator startups via public
server-rendered Inertia.js pages on workatastartup.com.
Specializes in 5-50 person early-stage, seed, and Series A/B engineering opportunities.
Strictly non-invasive: requires no login, no CAPTCHA bypass, and no private internal APIs.
"""

import json
import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any, Optional

import httpx
from bs4 import BeautifulSoup

from models.job import Job
from processing.deduplication import clean_job_title

logger = logging.getLogger("custom_scraper.yc")

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Sec-Ch-Ua": '"Chromium";v="130", "Google Chrome";v="130"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
}


class YCWorkAtAStartupScrapeResult:
    """Telemetry and job payload returned by YCWorkAtAStartupScraper."""

    def __init__(
        self,
        platform: str = "yc",
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


class YCWorkAtAStartupScraper:
    """Autonomous scraper extracting early-stage startup jobs from Y Combinator's Work at a Startup portal."""

    BASE_URL = "https://www.workatastartup.com"

    def __init__(
        self,
        timeout: float = 12.0,
        max_workers: int = 5,
    ):
        self.timeout = timeout
        self.max_workers = max_workers

    def _fetch_job_detail(
        self, client: httpx.Client, job_id: Any
    ) -> tuple[dict[str, Any], dict[str, Any], Optional[str]]:
        """Fetches full job description, skills, and company metadata for a single YC posting."""
        try:
            url = f"{self.BASE_URL}/jobs/{job_id}"
            res = client.get(url, timeout=self.timeout)
            if res.status_code != 200:
                return {}, {}, None

            soup = BeautifulSoup(res.text, "html.parser")
            div = soup.find("div", id=lambda x: x and "react-component" in x)
            if div and "data-page" in div.attrs:
                data = json.loads(div["data-page"])
                props = data.get("props", {})
                job = props.get("job") or props.get("jobListing") or {}
                company = props.get("company") or {}
                apply_url = props.get("applyUrl")
                return job, company, apply_url
        except Exception as e:
            logger.debug(f"Failed fetching YC job detail {job_id}: {e}")
        return {}, {}, None

    def scrape(
        self,
        search_term: str = "Software Engineer",
        location: str = "all",
        results_wanted: int = 25,
        hours_old: int = 336,
    ) -> YCWorkAtAStartupScrapeResult:
        """Scrapes engineering jobs from Y Combinator's official Work at a Startup portal."""
        t0 = time.time()
        target_url = f"{self.BASE_URL}/jobs/l/software-engineer"

        try:
            with httpx.Client(
                headers=DEFAULT_HEADERS,
                follow_redirects=True,
                timeout=self.timeout,
            ) as client:
                resp = client.get(target_url)

                duration = round(time.time() - t0, 2)
                if resp.status_code != 200:
                    logger.warning(f"YC Work at a Startup returned status {resp.status_code}")
                    return YCWorkAtAStartupScrapeResult(
                        search_query=search_term,
                        location=location,
                        duration_seconds=duration,
                        status="FAILED",
                        error=f"HTTP {resp.status_code}",
                    )

                soup = BeautifulSoup(resp.text, "html.parser")
                div = soup.find("div", id=lambda x: x and "JobsV2Page" in x)
                if not div or "data-page" not in div.attrs:
                    logger.warning("No Inertia data-page found on YC Work at a Startup")
                    return YCWorkAtAStartupScrapeResult(
                        search_query=search_term,
                        location=location,
                        duration_seconds=duration,
                        status="FAILED",
                        error="Missing Inertia data-page payload",
                    )

                page_data = json.loads(div["data-page"])
                raw_jobs = page_data.get("props", {}).get("jobs", [])

                if not raw_jobs:
                    return YCWorkAtAStartupScrapeResult(
                        search_query=search_term,
                        location=location,
                        total_found=0,
                        jobs=[],
                        duration_seconds=duration,
                        status="SUCCESS",
                    )

                candidate_jobs_to_fetch = raw_jobs[:results_wanted]
                job_details: list[tuple[dict[str, Any], dict[str, Any], Optional[str]]] = []

                with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                    future_to_job = {
                        executor.submit(self._fetch_job_detail, client, item.get("id")): item
                        for item in candidate_jobs_to_fetch
                        if item.get("id")
                    }
                    for future in as_completed(future_to_job):
                        try:
                            j_detail, c_detail, apply_u = future.result()
                            if j_detail:
                                job_details.append((j_detail, c_detail, apply_u))
                        except Exception as e:
                            logger.debug(f"Error resolving YC job future: {e}")

                canonical_jobs: list[Job] = []
                for j_dict, c_dict, apply_url in job_details:
                    jid = f"yc-{j_dict.get('id')}"
                    raw_title = j_dict.get("title") or ""
                    cleaned_title = clean_job_title(raw_title)

                    co_name = c_dict.get("name") or "YC Startup"
                    loc = j_dict.get("location") or "Remote"
                    is_rem = "remote" in loc.lower()

                    desc_html = j_dict.get("descriptionHtml") or ""
                    desc_text = re.sub(r"<[^>]+>", " ", desc_html).strip()
                    skills = j_dict.get("skills") or []
                    if skills:
                        desc_text = f"{desc_text} Skills: {', '.join(skills)}"

                    team_size = c_dict.get("teamSize")
                    if isinstance(team_size, (int, float)):
                        if team_size <= 10:
                            size_label = f"1-10 employees ({int(team_size)})"
                        elif team_size <= 50:
                            size_label = f"11-50 employees ({int(team_size)})"
                        else:
                            size_label = f"{int(team_size)} employees"
                    elif isinstance(team_size, str) and team_size.strip().isdigit():
                        t_val = int(team_size.strip())
                        if t_val <= 10:
                            size_label = f"1-10 employees ({t_val})"
                        elif t_val <= 50:
                            size_label = f"11-50 employees ({t_val})"
                        else:
                            size_label = f"{team_size} employees"
                    elif team_size:
                        size_label = f"{team_size} employees"
                    else:
                        size_label = "1-10 employees"

                    batch = c_dict.get("batch")
                    if batch:
                        desc_text = f"{desc_text} YC Batch: {batch}."

                    salary_raw = j_dict.get("salaryRange")
                    min_exp_raw = j_dict.get("minExperience")
                    min_exp = None
                    if isinstance(min_exp_raw, (int, float)):
                        min_exp = int(min_exp_raw)
                    elif isinstance(min_exp_raw, str):
                        m_exp = re.search(r"\d+", min_exp_raw)
                        if m_exp:
                            min_exp = int(m_exp.group(0))

                    discovery_url = f"{self.BASE_URL}/jobs/{j_dict.get('id')}"
                    final_apply = apply_url or discovery_url

                    job_obj = Job(
                        id=jid,
                        title=cleaned_title,
                        company=co_name,
                        source="yc",
                        location=loc,
                        is_remote=is_rem,
                        salary_raw=salary_raw,
                        experience_min=min_exp,
                        description=desc_text,
                        discovery_url=discovery_url,
                        apply_url=final_apply,
                        raw_data={
                            "company_size": size_label,
                            "company_size_label": size_label,
                            "yc_batch": c_dict.get("batch"),
                            "company_slug": c_dict.get("slug"),
                            "all_skills": skills,
                            "team_size": team_size,
                            "sponsors_visa": j_dict.get("sponsorsVisa"),
                            "company_website": c_dict.get("website"),
                        },
                    )
                    canonical_jobs.append(job_obj)

                duration = round(time.time() - t0, 2)
                logger.info(
                    f"YC Work at a Startup scrape complete: retrieved {len(canonical_jobs)} jobs in {duration}s"
                )

                return YCWorkAtAStartupScrapeResult(
                    platform="yc",
                    search_query=search_term,
                    location=location,
                    total_found=len(canonical_jobs),
                    jobs=canonical_jobs,
                    duration_seconds=duration,
                    status="SUCCESS",
                )

        except Exception as e:
            duration = round(time.time() - t0, 2)
            logger.error(f"YC Work at a Startup scrape failed: {e}")
            return YCWorkAtAStartupScrapeResult(
                search_query=search_term,
                location=location,
                duration_seconds=duration,
                status="FAILED",
                error=str(e),
            )
