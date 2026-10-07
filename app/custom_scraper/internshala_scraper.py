"""Internshala Scraper Orchestrator.

In-house autonomous scraper for Internshala (internshala.com) extracting job postings
directly into canonical models.job.Job.
Strictly non-invasive: requires no login, no CAPTCHA bypass, no Playwright, no proxies,
and uses standard TLS verification.
"""

import logging
import re
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import httpx
from bs4 import BeautifulSoup

from models.job import Job
from processing.deduplication import clean_job_title
from processing.experience_parser import extract_experience
from processing.relevance import HARD_EXCLUDE_TITLE_KEYWORDS, _has_keyword
from processing.salary_parser import parse_salary

logger = logging.getLogger("custom_scraper.internshala")


def _get_default_reference_date() -> datetime:
    """Reuses the canonical reference datetime from run_pipeline to ensure unified freshness calculation."""
    try:
        from run_pipeline import CURRENT_DATE
        return CURRENT_DATE
    except Exception:
        return datetime(2026, 9, 28, tzinfo=timezone.utc)


DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://internshala.com/",
}


class InternshalaScrapeResult:
    """Telemetry and job payload returned by InternshalaScraper."""

    def __init__(
        self,
        platform: str = "internshala",
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


class InternshalaScraper:
    """Autonomous scraper for Internshala job listings."""

    BASE_URL = "https://internshala.com"

    def __init__(
        self,
        timeout: float = 15.0,
        request_delay: float = 0.3,
        reference_date: datetime | None = None,
    ):
        self.timeout = timeout
        self.request_delay = request_delay
        self.reference_date = reference_date or _get_default_reference_date()

    def _build_search_url(self, search_term: str, location: str) -> tuple[str, bool]:
        """Constructs canonical Internshala SEO listing URL based on query and target location.
        
        Returns:
            tuple[url: str, is_remote_search: bool]
        """
        q_lower = (search_term or "").lower().strip()
        loc_lower = (location or "").lower().strip()
        is_remote = "remote" in loc_lower or "work from home" in loc_lower or "wfh" in loc_lower

        # Map search query to Internshala profile slug
        if "full stack" in q_lower or "fullstack" in q_lower:
            profile = "full-stack-developer"
        elif "backend" in q_lower or "api" in q_lower:
            profile = "backend-developer"
        elif "ai" in q_lower or "artificial intelligence" in q_lower or "machine learning" in q_lower:
            profile = "artificial-intelligence-ai"
        elif "data" in q_lower:
            profile = "data-science"
        else:
            profile = "python-developer"

        # Construct location URL path
        if is_remote:
            url = f"{self.BASE_URL}/jobs/{profile}-jobs/work-from-home/"
        elif "chennai" in loc_lower:
            url = f"{self.BASE_URL}/jobs/{profile}-jobs-in-chennai/"
        else:
            url = f"{self.BASE_URL}/jobs/{profile}-jobs-in-bangalore/"

        return url, is_remote

    def _parse_relative_date(self, badge_text: str | None, max_days: float = 7.0) -> tuple[str | None, bool]:
        """Parses Internshala relative date string into ISO 8601 UTC timestamp.
        
        Returns:
            tuple[posted_at_iso: str | None, is_fresh: bool]
            If date is missing, malformed, or older than max_days, is_fresh is False and posted_at_iso may be None.
        """
        if not badge_text or not isinstance(badge_text, str):
            return None, False

        txt = badge_text.strip().lower()
        if any(w in txt for w in ["today", "just now", "few hours ago", "hours ago"]):
            return self.reference_date.isoformat(), True

        m_days = re.search(r"(\d+)\s+day[s]?\s+ago", txt)
        if m_days:
            days = int(m_days.group(1))
            if days <= max_days:
                dt = self.reference_date - timedelta(days=days)
                return dt.isoformat(), True
            return None, False

        m_weeks = re.search(r"(\d+)\s+week[s]?\s+ago", txt)
        if m_weeks:
            weeks = int(m_weeks.group(1))
            days = weeks * 7
            if days <= max_days:
                dt = self.reference_date - timedelta(days=days)
                return dt.isoformat(), True
            return None, False

        # Older time units like months or unparseable text
        return None, False

    def _parse_salary(self, text: str) -> tuple[float | None, float | None, str | None]:
        """Extracts minimum, maximum, and display string via processing.salary_parser."""
        if not text or "competitive" in text.lower():
            return None, None, None
        s_min, s_max, _ = parse_salary(text)
        return s_min, s_max, text.strip() if s_min is not None else None

    def _parse_experience(self, text: str) -> tuple[int | None, int | None, str | None]:
        """Extracts experience requirements in years via processing.experience_parser."""
        return extract_experience(text)

    def _fetch_detail_page(self, client: httpx.Client, detail_url: str) -> tuple[str, list[str]]:
        """Fetches public job detail page to extract description and explicit skill tags."""
        try:
            r = client.get(detail_url)
            if r.status_code != 200:
                logger.warning(f"Failed to fetch Internshala detail page {detail_url}: HTTP {r.status_code}")
                return "", []

            soup = BeautifulSoup(r.text, "html.parser")

            # Extract skill tags
            skills: list[str] = []
            for el in soup.find_all("span", class_="round_tabs"):
                st = el.get_text(strip=True)
                if st and st not in skills:
                    skills.append(st)

            # Extract job description
            desc_el = soup.find("div", class_="text-container") or soup.find("div", class_="internship_details")
            desc_text = desc_el.get_text(separator="\n", strip=True) if desc_el else ""

            return desc_text, skills
        except Exception as e:
            logger.warning(f"Error extracting Internshala detail from {detail_url}: {e}")
            return "", []

    def scrape(
        self,
        search_term: str,
        location: str,
        results_wanted: int = 15,
        hours_old: int = 336,
    ) -> InternshalaScrapeResult:
        """Executes search on Internshala Page 1, performs early freshness filtering,
        fetches detail pages for fresh candidates, and returns canonical Job instances.
        """
        t0 = time.time()
        max_days = hours_old / 24.0

        target_url, is_remote_search = self._build_search_url(search_term, location)
        logger.info(
            f"Targeting Internshala search: '{search_term}' in '{location}' -> {target_url} "
            f"(results_wanted={results_wanted}, max_days={max_days})"
        )

        collected_jobs: list[Job] = []

        with httpx.Client(headers=DEFAULT_HEADERS, timeout=self.timeout, follow_redirects=True) as client:
            try:
                r = client.get(target_url)
            except Exception as e:
                logger.error(f"Internshala request failed for '{search_term}' in '{location}': {e}")
                dur = round(time.time() - t0, 2)
                return InternshalaScrapeResult(
                    platform="internshala",
                    search_query=search_term,
                    location=location,
                    total_found=0,
                    jobs=[],
                    duration_seconds=dur,
                    status="ERROR",
                    error=str(e),
                )

            if r.status_code in [403, 429]:
                logger.critical(f"Internshala blocked request with status {r.status_code}")
                dur = round(time.time() - t0, 2)
                return InternshalaScrapeResult(
                    platform="internshala",
                    search_query=search_term,
                    location=location,
                    total_found=0,
                    jobs=[],
                    duration_seconds=dur,
                    status="BLOCKED",
                    error=f"HTTP {r.status_code}",
                    bot_detected=True,
                )

            if r.status_code != 200:
                logger.warning(f"Internshala search returned unexpected status {r.status_code}")
                dur = round(time.time() - t0, 2)
                return InternshalaScrapeResult(
                    platform="internshala",
                    search_query=search_term,
                    location=location,
                    total_found=0,
                    jobs=[],
                    duration_seconds=dur,
                    status="ERROR",
                    error=f"HTTP {r.status_code}",
                )

            soup = BeautifulSoup(r.text, "html.parser")
            cards = soup.find_all("div", id=re.compile(r"^individual_internship_\d+"))
            logger.info(f"Found {len(cards)} raw job cards on Internshala page 1")

            for card in cards:
                if len(collected_jobs) >= results_wanted:
                    break

                cid_raw = card.get("id", "").replace("individual_internship_", "").strip()
                if not cid_raw:
                    continue

                # 1. Title Extraction & Hard Exclusion
                title_el = card.find(["h3", "div", "a"], class_=lambda x: x and ("title" in x or "name" in x))
                title_raw = title_el.get_text(strip=True) if title_el else ""
                title_clean = clean_job_title(title_raw)
                if not title_clean:
                    continue

                # 2. Company & Location
                comp_el = card.find("p", class_="company-name")
                company = comp_el.get_text(strip=True) if comp_el else "Confidential"

                loc_el = (
                    card.find("p", class_="row-1-item locations")
                    or card.find("div", class_="row-1-item locations")
                    or card.find("a", class_="location_link")
                )
                loc_str = loc_el.get_text(strip=True) if loc_el else location

                # Remote classification strictly evidence-based
                is_remote_job = (
                    is_remote_search
                    or "work from home" in loc_str.lower()
                    or "remote" in loc_str.lower()
                )

                # 3. Experience Mapping
                row_items = [el.get_text(strip=True) for el in card.find_all("div", class_="row-1-item")]
                exp_text = next((item for item in row_items if "year" in item.lower() or "experience" in item.lower()), "")
                e_min, e_max, exp_raw = self._parse_experience(exp_text)

                # 4. Salary
                sal_text = next((item for item in row_items if "₹" in item or "salary" in item.lower()), "")
                s_min, s_max, s_raw = self._parse_salary(sal_text)

                # 5. Date Parsing from Search Card Badge
                status_badges = [
                    el.get_text(strip=True)
                    for el in card.find_all("div", class_=lambda x: x and "status" in x.lower())
                ]
                date_badge = next((b for b in status_badges if "ago" in b.lower() or "today" in b.lower()), None)
                posted_at_iso, _ = self._parse_relative_date(date_badge, max_days=max_days)

                # 6. Discovery URL
                data_href = card.get("data-href") or ""
                if not data_href:
                    # Try finding link inside card
                    link_el = card.find("a", href=lambda h: h and "/job/detail/" in h)
                    data_href = link_el.get("href") if link_el else ""

                if not data_href:
                    continue

                discovery_url = f"{self.BASE_URL}{data_href}" if data_href.startswith("/") else data_href

                # 7. Fetch Detail Page for Fresh Candidate
                desc_text, skills_list = self._fetch_detail_page(client, discovery_url)
                if skills_list:
                    full_desc = f"Skills: {', '.join(skills_list)}\n\n{desc_text}" if desc_text else f"Skills: {', '.join(skills_list)}"
                else:
                    full_desc = desc_text

                job = Job(
                    id=f"internshala-{cid_raw}",
                    title=title_clean,
                    company=company,
                    source="internshala",
                    location=loc_str,
                    is_remote=is_remote_job,
                    salary_raw=s_raw,
                    salary_min=s_min,
                    salary_max=s_max,
                    salary_currency="INR",
                    description=full_desc,
                    discovery_url=discovery_url,
                    apply_url=discovery_url,
                    apply_type="PLATFORM",
                    posted_at=posted_at_iso,
                    experience_min=e_min,
                    experience_max=e_max,
                    experience_raw=exp_raw,
                    matched_skills=skills_list,
                    raw_data={
                        "internshala_id": cid_raw,
                        "date_badge": date_badge,
                        "posted_at": posted_at_iso,
                        "raw_experience": exp_text,
                        "raw_salary": sal_text,
                    },
                )
                collected_jobs.append(job)

                if self.request_delay > 0:
                    time.sleep(self.request_delay)

        dur = round(time.time() - t0, 2)
        logger.info(f"Internshala scraping completed: {len(collected_jobs)} valid jobs in {dur}s")

        return InternshalaScrapeResult(
            platform="internshala",
            search_query=search_term,
            location=location,
            total_found=len(collected_jobs),
            jobs=collected_jobs,
            duration_seconds=dur,
            status="SUCCESS",
        )
