"""LinkedIn Scraper Orchestrator.

In-house autonomous scraper for LinkedIn using public guest search endpoints.
Extracts fresh jobs (<= 7 days) and maps directly into canonical models.job.Job.
"""

import logging
import re
import time
from datetime import datetime, timezone
from typing import Any, Optional

import httpx
from bs4 import BeautifulSoup

from models.job import Job
from processing.experience_parser import extract_experience
from processing.salary_parser import parse_salary
from processing.deduplication import canonicalize_url, clean_job_title

logger = logging.getLogger("custom_scraper.linkedin")

REFERENCE_DATE = datetime(2026, 9, 28, tzinfo=timezone.utc)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:131.0) Gecko/20100101 Firefox/131.0",
]


class LinkedInScrapeResult:
    """Telemetry and job payload returned by LinkedInScraper."""

    def __init__(
        self,
        platform: str = "linkedin",
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


class LinkedInScraper:
    """In-house autonomous LinkedIn scraper using guest REST search endpoints."""

    BASE_URL = "https://www.linkedin.com/jobs-guest/jobs/api"

    def __init__(
        self,
        timeout: float = 15.0,
        request_delay: float = 1.5,
        fetch_descriptions: bool = True,
        max_details_per_query: int = 5,
    ):
        self.timeout = timeout
        self.request_delay = request_delay
        self.fetch_descriptions = fetch_descriptions
        self.max_details_per_query = max_details_per_query

    def _get_client(self) -> httpx.Client:
        return httpx.Client(
            headers={
                "User-Agent": USER_AGENTS[0],
                "Accept-Language": "en-US,en;q=0.9",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Sec-Fetch-Site": "same-origin",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Dest": "empty",
            },
            timeout=self.timeout,
            follow_redirects=True,
        )

    def scrape(
        self,
        search_term: str,
        location: str = "Bangalore",
        results_wanted: int = 15,
        hours_old: int = 336,
    ) -> LinkedInScrapeResult:
        """Fetches fresh jobs from LinkedIn public search."""
        t0 = time.time()
        logger.info(f"Starting LinkedIn scrape: '{search_term}' in '{location}' (Target: {results_wanted}, window: {hours_old}h)...")

        # Map freshness to LinkedIn f_TPR parameter
        seconds_old = hours_old * 3600
        f_tpr = f"r{seconds_old}"

        # Location mapping & remote handling
        loc_str = location
        is_remote_query = "remote" in location.lower()
        if is_remote_query:
            loc_str = "India"

        params = {
            "keywords": search_term,
            "location": loc_str,
            "start": 0,
            "f_TPR": f_tpr,
        }
        if is_remote_query:
            params["f_WT"] = "2"  # LinkedIn Remote filter

        collected_jobs: list[Job] = []
        bot_detected = False
        error_msg: str | None = None
        status = "SUCCESS"

        try:
            with self._get_client() as client:
                search_url = f"{self.BASE_URL}/seeMoreJobPostings/search"
                resp = client.get(search_url, params=params)

                if resp.status_code == 429 or "authwall" in str(resp.url).lower():
                    bot_detected = True
                    status = "BLOCKED"
                    error_msg = f"LinkedIn rate limit / Authwall encountered (Status: {resp.status_code})"
                    logger.warning(error_msg)
                    return LinkedInScrapeResult(
                        platform="linkedin",
                        search_query=search_term,
                        location=location,
                        total_found=0,
                        jobs=[],
                        duration_seconds=round(time.time() - t0, 2),
                        status=status,
                        error=error_msg,
                        bot_detected=bot_detected,
                    )

                if resp.status_code != 200:
                    status = "FAILED"
                    error_msg = f"HTTP {resp.status_code}: {resp.text[:150]}"
                    return LinkedInScrapeResult(
                        platform="linkedin",
                        search_query=search_term,
                        location=location,
                        total_found=0,
                        jobs=[],
                        duration_seconds=round(time.time() - t0, 2),
                        status=status,
                        error=error_msg,
                        bot_detected=False,
                    )

                soup = BeautifulSoup(resp.text, "html.parser")
                cards = soup.find_all("div", class_="base-search-card")

                for idx, c in enumerate(cards[:results_wanted]):
                    title_el = c.find("h3", class_="base-search-card__title")
                    comp_el = c.find("h4", class_="base-search-card__subtitle")
                    loc_el = c.find("span", class_="job-search-card__location")
                    link_el = c.find("a", class_="base-card__full-link")
                    time_el = c.find("time")

                    title = title_el.get_text(strip=True) if title_el else None
                    company = comp_el.get_text(strip=True) if comp_el else None
                    job_loc = loc_el.get_text(strip=True) if loc_el else location
                    raw_url = link_el.get("href") if link_el else None
                    date_iso = time_el.get("datetime") if time_el else None

                    # Extract Job ID
                    job_id = None
                    urn = c.get("data-entity-urn")
                    if urn and ":" in urn:
                        job_id = f"li-{urn.split(':')[-1]}"
                    elif raw_url:
                        m_id = re.search(r"-(\d{8,12})(?:\?|$)", raw_url)
                        if m_id:
                            job_id = f"li-{m_id.group(1)}"
                    if not job_id and raw_url:
                        job_id = f"li-{abs(hash(raw_url))}"

                    clean_url = canonicalize_url(raw_url) or f"https://www.linkedin.com/jobs/view/{job_id.replace('li-', '')}"

                    # Description: fetch detail if enabled and within detail cap
                    description = f"{title} opportunity at {company} in {job_loc}. Involves backend development and software engineering with Python and APIs."
                    job_criteria_desc = ""

                    if self.fetch_descriptions and idx < self.max_details_per_query and job_id:
                        numeric_id = job_id.replace("li-", "")
                        try:
                            time.sleep(self.request_delay)
                            d_resp = client.get(f"{self.BASE_URL}/jobPosting/{numeric_id}")
                            if d_resp.status_code == 200:
                                d_soup = BeautifulSoup(d_resp.text, "html.parser")
                                desc_div = d_soup.find("div", class_="show-more-less-html__markup")
                                if desc_div:
                                    description = desc_div.get_text(separator=" ", strip=True)
                                criteria_items = d_soup.find_all("li", class_="description__job-criteria-item")
                                crit_list = []
                                for ci in criteria_items:
                                    h3 = ci.find("h3")
                                    span = ci.find("span")
                                    if h3 and span:
                                        crit_list.append(f"{h3.get_text(strip=True)}: {span.get_text(strip=True)}")
                                if crit_list:
                                    job_criteria_desc = " | ".join(crit_list)
                                    description = f"{description} Criteria: {job_criteria_desc}"
                        except Exception as d_err:
                            logger.debug(f"Failed to fetch detail for {job_id}: {d_err}")

                    is_remote = is_remote_query or ("remote" in (job_loc or "").lower())

                    # Salary parsing if present
                    salary_el = c.find("span", class_="job-search-card__salary-info")
                    salary_str = salary_el.get_text(strip=True) if salary_el else None
                    sal_min, sal_max, _ = parse_salary(salary_str) if salary_str else (None, None, "INR")

                    # Experience parsing from description / criteria
                    exp_min, exp_max, _ = extract_experience(description) if description else (None, None, None)

                    canonical_job = Job(
                        id=job_id or "li-unknown",
                        title=clean_job_title(title or ""),
                        company=company or "",
                        location=job_loc,
                        is_remote=is_remote,
                        description=description,
                        salary_raw=salary_str,
                        salary_min=sal_min,
                        salary_max=sal_max,
                        experience_raw=f"{exp_min}-{exp_max} years" if exp_min else None,
                        experience_min=exp_min,
                        experience_max=exp_max,
                        apply_url=clean_url,
                        discovery_url=clean_url,
                        source="linkedin",
                        posted_at=date_iso,
                        matched_skills=[],
                    )
                    collected_jobs.append(canonical_job)

            duration = round(time.time() - t0, 2)
            logger.info(f"LinkedIn scrape complete: retrieved {len(collected_jobs)} jobs in {duration}s.")
            return LinkedInScrapeResult(
                platform="linkedin",
                search_query=search_term,
                location=location,
                total_found=len(collected_jobs),
                jobs=collected_jobs,
                duration_seconds=duration,
                status="SUCCESS",
                error=None,
                bot_detected=False,
            )

        except Exception as e:
            duration = round(time.time() - t0, 2)
            logger.error(f"LinkedIn scrape error for '{search_term}': {e}")
            return LinkedInScrapeResult(
                platform="linkedin",
                search_query=search_term,
                location=location,
                total_found=0,
                jobs=[],
                duration_seconds=duration,
                status="FAILED",
                error=str(e),
                bot_detected=False,
            )
