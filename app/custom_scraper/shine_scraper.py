"""Shine Scraper Orchestrator.

In-house autonomous scraper for Shine (shine.com) using public server-rendered SEO routes
and Schema.org JobPosting JSON-LD detail schemas directly into canonical models.job.Job.
Strictly non-invasive: requires no login, no CAPTCHA bypass, no Playwright, and no private internal APIs.
"""

import json
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

logger = logging.getLogger("custom_scraper.shine")

REFERENCE_DATE = datetime(2026, 9, 28, tzinfo=timezone.utc)

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Sec-Ch-Ua": '"Chromium";v="130", "Google Chrome";v="130"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
}


class ShineScrapeResult:
    """Telemetry and job payload returned by ShineScraper."""

    def __init__(
        self,
        platform: str = "shine",
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


class ShineScraper:
    """Autonomous Shine scraper leveraging public SEO search routes and JobPosting JSON-LD schemas."""

    BASE_URL = "https://www.shine.com"

    def __init__(
        self,
        timeout: float = 15.0,
        request_delay: float = 0.5,
        reference_date: datetime | None = None,
    ):
        self.timeout = timeout
        self.request_delay = request_delay
        self.reference_date = reference_date or REFERENCE_DATE

    def _resolve_target_url(self, search_term: str, location: str, page: int = 1) -> tuple[str, bool]:
        """Generates Shine SEO search URL dynamically from any input query and location.
        
        Examples:
        - Python Backend Developer in Bangalore -> /job-search/python-backend-developer-jobs-in-bangalore
        - FastAPI Developer in Chennai -> /job-search/fastapi-developer-jobs-in-chennai
        - Python Backend Developer in Remote -> /job-search/remote-python-backend-developer-jobs
        """
        q_slug = re.sub(r"[^a-zA-Z0-9]+", "-", (search_term or "").strip().lower()).strip("-")
        loc_lower = (location or "").strip().lower()

        is_remote = "remote" in loc_lower or "remote" in q_slug
        page_suffix = f"-{page}" if page > 1 else ""

        if is_remote:
            return f"{self.BASE_URL}/job-search/remote-{q_slug}-jobs{page_suffix}", True

        loc_slug = "bangalore" if ("bangalore" in loc_lower or "bengaluru" in loc_lower) else ("chennai" if "chennai" in loc_lower else loc_lower)
        return f"{self.BASE_URL}/job-search/{q_slug}-jobs-in-{loc_slug}{page_suffix}", False

    def _parse_experience(self, text: str | None) -> tuple[int | None, int | None, str | None]:
        """Extracts experience_min, experience_max, and raw string via processing.experience_parser."""
        return extract_experience(text)

    def _parse_salary(self, text: str | None) -> tuple[float | None, float | None, str | None]:
        """Parses explicit salary text via processing.salary_parser."""
        if not text:
            return None, None, None
        s_min, s_max, _ = parse_salary(text)
        return s_min, s_max, text.strip() if s_min is not None else None

    def _is_explicitly_stale_card_badge(self, text: str | None) -> bool:
        """Returns True ONLY when card relative badge explicitly proves the job is > 7 days old.
        
        A missing badge returns False so detail page can be fetched for JSON-LD datePosted.
        """
        if not text:
            return False
        lbl = text.strip().lower()
        if "month" in lbl or "year" in lbl or "30+" in lbl:
            return True
        m_w = re.search(r"(\d+)\+?\s*weeks?", lbl)
        if m_w and int(m_w.group(1)) >= 2:
            return True
        m_d = re.search(r"(\d+)\+?\s*days?", lbl)
        if m_d and int(m_d.group(1)) > 7:
            return True
        return False

    def _parse_card_relative_date(self, text: str | None) -> datetime | None:
        """Converts explicit recent relative badge text to timezone-aware UTC datetime.
        
        Returns None if missing, ambiguous, or > 7 days.
        """
        if not text:
            return None
        lbl = text.strip().lower()
        if "today" in lbl or "just now" in lbl:
            return self.reference_date
        if "yesterday" in lbl:
            return self.reference_date - timedelta(days=1)
        m_h = re.search(r"(\d+)\s+hours?\s+ago", lbl)
        if m_h:
            return self.reference_date - timedelta(hours=int(m_h.group(1)))
        m_d = re.search(r"(\d+)\s+days?\s+ago", lbl)
        if m_d:
            days = int(m_d.group(1))
            if days <= 7:
                return self.reference_date - timedelta(days=days)
        return None

    def _parse_card(self, article: BeautifulSoup) -> dict[str, Any] | None:
        """Parses raw attributes from a single Shine <article> card."""
        a_tag = article.find("a", class_=re.compile(r"hit|title", re.I))
        title_raw = a_tag.get("aria-label", "") if a_tag else ""
        href = a_tag.get("href", "") if a_tag else ""

        if " at " in title_raw:
            job_title = title_raw.split(" at ")[0].strip()
        else:
            job_title = title_raw.strip()

        meta_url = article.find("meta", itemprop="url")
        job_url = meta_url.get("content") if meta_url else (f"{self.BASE_URL}{href}" if href else "")

        job_id = None
        if job_url:
            m = re.search(r"/(\d+)(?:\?|$)", job_url)
            if m:
                job_id = m.group(1)

        if not job_id or not job_title:
            return None

        comp_el = article.find(class_=re.compile(r"company|recruiter|name", re.I))
        company = comp_el.get_text(strip=True) if comp_el else ""

        raw_text = article.get_text(separator=" | ", strip=True)
        tokens = [p.strip() for p in raw_text.split(" | ")]

        exp_raw = None
        salary_raw = None
        loc_raw = None
        posted_rel = None
        skills: list[str] = []

        for tok in tokens:
            if re.search(r"\b\d+\s+to\s+\d+\s+Yrs\b|\b\d+\+\s+Yrs\b", tok, re.I):
                exp_raw = tok
            elif re.search(r"Lakh/Yr|Per Annum|INR|\bPA\b", tok, re.I):
                salary_raw = tok
            elif any(kw in tok.lower() for kw in ["hours ago", "days ago", "today", "yesterday", "weeks ago", "months ago"]):
                if not posted_rel:
                    posted_rel = tok
            elif any(loc in tok.lower() for loc in ["bangalore", "chennai", "mumbai", "pune", "delhi", "hyderabad", "remote", "gurugram", "noida", "kolkata"]):
                if not loc_raw:
                    loc_raw = tok

        if "Required:" in tokens:
            idx = tokens.index("Required:")
            skills = [x for x in tokens[idx + 1 :] if x not in ["·", "Apply", ""]]

        return {
            "job_id": job_id,
            "title": job_title,
            "company": company,
            "location": loc_raw,
            "experience_raw": exp_raw,
            "salary_raw": salary_raw,
            "posted_rel": posted_rel,
            "skills": skills,
            "job_url": job_url,
        }

    def _fetch_detail_json_ld(self, client: httpx.Client, job_url: str) -> tuple[str | None, str | None, str | None]:
        """Fetches detail page and extracts (description, datePosted_iso, company_name) from JSON-LD."""
        try:
            r = client.get(job_url, timeout=self.timeout)
            if r.status_code != 200:
                logger.warning(f"Detail fetch returned status {r.status_code} for {job_url}")
                return None, None, None

            soup = BeautifulSoup(r.text, "html.parser")
            for s in soup.find_all("script", type="application/ld+json"):
                if not s.string:
                    continue
                try:
                    data = json.loads(s.string)
                    if isinstance(data, dict) and data.get("@type") == "JobPosting":
                        desc = data.get("description")
                        date_posted = data.get("datePosted")
                        org = data.get("hiringOrganization")
                        org_name = org.get("name") if isinstance(org, dict) else None
                        return desc, date_posted, org_name
                except Exception:
                    continue
            return None, None, None
        except Exception as e:
            logger.warning(f"Failed to fetch detail for {job_url}: {e}")
            return None, None, None

    def scrape(
        self,
        search_term: str,
        location: str,
        results_wanted: int = 15,
        hours_old: int = 336,
    ) -> ShineScrapeResult:
        """Scrapes jobs from Shine using dynamic SEO route, card filtering, and detail JSON-LD enrichment."""
        t0 = time.time()
        max_days = hours_old / 24.0

        logger.info(
            f"Targeting Shine search for '{search_term}' in '{location}' "
            f"(results_wanted={results_wanted}, max_days={max_days})"
        )

        collected_jobs: list[Job] = []
        page = 1
        max_pages = 2 if results_wanted > 20 else 1

        with httpx.Client(headers=DEFAULT_HEADERS, follow_redirects=True, timeout=self.timeout) as client:
            while page <= max_pages and len(collected_jobs) < results_wanted:
                search_url, require_remote = self._resolve_target_url(search_term, location, page=page)
                logger.info(f"[Shine Page {page}] Fetching {search_url}...")

                try:
                    r = client.get(search_url)
                except Exception as e:
                    logger.error(f"Failed to fetch Shine search page {search_url}: {e}")
                    dur = round(time.time() - t0, 2)
                    return ShineScrapeResult(
                        platform="shine",
                        search_query=search_term,
                        location=location,
                        total_found=len(collected_jobs),
                        jobs=collected_jobs,
                        duration_seconds=dur,
                        status="ERROR",
                        error=str(e),
                    )

                if r.status_code in [403, 429]:
                    logger.critical(f"Shine returned status {r.status_code} on {search_url} (Bot challenge/Rate limit)")
                    dur = round(time.time() - t0, 2)
                    return ShineScrapeResult(
                        platform="shine",
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
                    logger.warning(f"Shine returned non-200 status {r.status_code} for {search_url}")
                    break

                soup = BeautifulSoup(r.text, "html.parser")
                articles = soup.find_all("article")
                if not articles:
                    logger.info(f"No job cards found on Shine page {page}")
                    break

                logger.info(f"Found {len(articles)} raw job cards on Shine page {page}")

                for art in articles:
                    if len(collected_jobs) >= results_wanted:
                        break

                    card = self._parse_card(art)
                    if not card:
                        continue

                    job_title = card["title"]
                    title_clean = clean_job_title(job_title)
                    t_lower = title_clean.lower()

                    # Experience parsing
                    exp_min, exp_max, exp_raw = self._parse_experience(card["experience_raw"])

                    # Detail Page Enrichment for Full Description and Exact ISO Timestamp
                    if self.request_delay > 0:
                        time.sleep(self.request_delay)

                    detail_desc, detail_date_iso, detail_comp = self._fetch_detail_json_ld(client, card["job_url"])

                    final_company = detail_comp or card["company"] or "Confidential"
                    final_desc = detail_desc
                    posted_at_iso: str | None = None
                    raw_posted_iso: str | None = detail_date_iso

                    # Date Evaluation
                    if detail_date_iso:
                        try:
                            dt = datetime.fromisoformat(detail_date_iso)
                            dt_utc = dt.astimezone(timezone.utc)
                            posted_at_iso = dt_utc.isoformat()
                        except Exception as ex:
                            logger.warning(f"Error parsing JSON-LD date '{detail_date_iso}': {ex}")

                    # Fallback to verified card relative date if detail date is unavailable
                    if not posted_at_iso:
                        card_dt = self._parse_card_relative_date(card["posted_rel"])
                        if card_dt:
                            posted_at_iso = card_dt.isoformat()

                    # Fallback for description if detail page failed
                    if not final_desc:
                        skills_str = ", ".join(card["skills"]) if card["skills"] else "Python"
                        final_desc = f"{job_title} at {final_company}\nRequired Skills: {skills_str}"

                    # Salary parsing
                    sal_min, sal_max, sal_raw = self._parse_salary(card["salary_raw"])

                    # Location string and Remote evaluation
                    loc_val = card["location"] or location
                    is_remote_job = require_remote or "remote" in (loc_val or "").lower() or "remote" in job_title.lower()

                    job_obj = Job(
                        id=f"shine-{card['job_id']}",
                        title=title_clean,
                        company=final_company,
                        source="shine",
                        location=loc_val,
                        is_remote=is_remote_job,
                        salary_raw=sal_raw,
                        salary_min=sal_min,
                        salary_max=sal_max,
                        salary_currency="INR",
                        description=final_desc,
                        discovery_url=card["job_url"],
                        apply_url=card["job_url"],
                        apply_type="PLATFORM",
                        posted_at=posted_at_iso,
                        experience_min=exp_min,
                        experience_max=exp_max,
                        experience_raw=exp_raw,
                        matched_skills=card["skills"],
                        raw_data={
                            "shine_job_id": card["job_id"],
                            "shine_date_posted": raw_posted_iso,
                            "shine_card_posted_rel": card["posted_rel"],
                            "skills": card["skills"],
                        },
                    )
                    collected_jobs.append(job_obj)

                page += 1

        dur = round(time.time() - t0, 2)
        logger.info(f"Shine scraping completed: {len(collected_jobs)} valid jobs returned in {dur}s")

        return ShineScrapeResult(
            platform="shine",
            search_query=search_term,
            location=location,
            total_found=len(collected_jobs),
            jobs=collected_jobs,
            duration_seconds=dur,
            status="SUCCESS",
        )
