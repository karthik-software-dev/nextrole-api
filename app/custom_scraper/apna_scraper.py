"""Apna Scraper Orchestrator.

In-house autonomous scraper for Apna (apna.co) extracting tech job postings
directly into canonical models.job.Job.
Strictly non-invasive: requires no login, no CAPTCHA bypass, no Playwright, no proxies,
and uses standard TLS verification.
"""

import json
import logging
import re
import time
from datetime import datetime, timezone
from typing import Any, Optional

import httpx
from bs4 import BeautifulSoup

from models.job import Job
from processing.deduplication import clean_job_title
from processing.experience_parser import extract_experience
from processing.relevance import HARD_EXCLUDE_TITLE_KEYWORDS, _has_keyword
from processing.salary_parser import parse_salary

logger = logging.getLogger("custom_scraper.apna")


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
    "Referer": "https://apna.co/",
}


class ApnaScrapeResult:
    """Telemetry and job payload returned by ApnaScraper."""

    def __init__(
        self,
        platform: str = "apna",
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


class ApnaScraper:
    """Autonomous scraper for Apna (apna.co) job listings."""

    BASE_URL = "https://apna.co"

    def __init__(
        self,
        timeout: float = 15.0,
        request_delay: float = 0.3,
        reference_date: datetime | None = None,
    ):
        self.timeout = timeout
        self.request_delay = request_delay
        self.reference_date = reference_date or _get_default_reference_date()

    def _build_search_url(self, search_term: str, location: str, page: int = 1) -> tuple[str, bool]:
        """Constructs canonical search URL for Apna based on query, location, and page number.
        
        Returns:
            tuple[url: str, is_remote_search: bool]
        """
        q_clean = re.sub(r"\s+", "+", (search_term or "").strip())
        loc_lower = (location or "").lower().strip()
        is_remote = "remote" in loc_lower or "work from home" in loc_lower or "wfh" in loc_lower

        if is_remote:
            url = f"{self.BASE_URL}/jobs?text={q_clean}+remote&page={page}"
        elif "chennai" in loc_lower:
            url = f"{self.BASE_URL}/jobs/jobs-in-chennai?text={q_clean}&page={page}"
        else:
            url = f"{self.BASE_URL}/jobs/jobs-in-bengaluru-bangalore?text={q_clean}&page={page}"

        return url, is_remote

    def _parse_experience(self, text: str | None) -> tuple[int | None, int | None, str | None]:
        """Extracts experience requirements in years via processing.experience_parser."""
        return extract_experience(text)

    def _parse_salary(self, text: str | None) -> tuple[float | None, float | None, str | None]:
        """Extracts salary range via processing.salary_parser."""
        if not text or "not disclosed" in text.lower() or "competitive" in text.lower():
            return None, None, None
        s_min, s_max, _ = parse_salary(text)
        return s_min, s_max, text.strip() if s_min is not None else None

    def _parse_date(self, date_str: str | None, max_days: float = 7.0) -> tuple[str | None, bool]:
        """Parses exact ISO 8601 UTC datePosted string from Schema.org JSON-LD.
        
        Enforces conservative freshness:
        - Must be valid ISO 8601
        - Must be within [0, max_days] relative to self.reference_date
        - If missing or stale or unparseable, returns (None, False)
        """
        if not date_str or not isinstance(date_str, str):
            return None, False

        try:
            # Handle ISO with or without milliseconds and Z timezone
            clean_str = date_str.replace("Z", "+00:00")
            dt = datetime.fromisoformat(clean_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            else:
                dt = dt.astimezone(timezone.utc)
        except Exception:
            return None, False

        diff_days = (self.reference_date - dt).total_seconds() / 86400.0
        if 0.0 <= diff_days <= max_days:
            return dt.isoformat(), True

        return None, False

    def _fetch_detail_page(self, client: httpx.Client, detail_url: str) -> dict[str, Any] | None:
        """Fetches public job detail page and extracts Schema.org JSON-LD and Next.js RSC data."""
        try:
            r = client.get(detail_url)
            if r.status_code != 200:
                logger.warning(f"Failed to fetch Apna detail page {detail_url}: HTTP {r.status_code}")
                return None

            soup = BeautifulSoup(r.text, "html.parser")

            # 1. Schema.org JobPosting JSON-LD
            jp_data: dict[str, Any] | None = None
            for s in soup.find_all("script", type="application/ld+json"):
                if s.string:
                    try:
                        data = json.loads(s.string)
                        if isinstance(data, dict) and data.get("@type") == "JobPosting":
                            jp_data = data
                            break
                    except Exception:
                        pass

            if not jp_data:
                return None

            # 2. Extract external apply URL from Next.js RSC chunk
            external_job_url: str | None = None
            is_external_job = False

            m_apply = re.search(r'\\?"external_job_url\\?"\s*:\s*\\?"([^"\\]+)\\?"', r.text)
            if m_apply:
                external_job_url = m_apply.group(1).replace("\\/", "/")

            m_is_ext = re.search(r'\\?"is_external_job\\?"\s*:\s*(true|false)', r.text)
            if m_is_ext and m_is_ext.group(1).lower() == "true":
                is_external_job = True

            # 3. Work mode extraction from detail HTML
            work_mode = ""
            if "work from home" in r.text.lower():
                work_mode = "Work from Home"
            elif "work from office" in r.text.lower():
                work_mode = "Work from Office"

            return {
                "json_ld": jp_data,
                "external_job_url": external_job_url,
                "is_external_job": is_external_job,
                "work_mode": work_mode,
            }
        except Exception as e:
            logger.warning(f"Error fetching detail {detail_url}: {e}")
            return None

    def scrape(
        self,
        search_term: str,
        location: str,
        results_wanted: int = 15,
        hours_old: int = 336,
    ) -> ApnaScrapeResult:
        """Executes search on Apna across up to max_pages=2, deduplicates by job ID,
        extracts detail page JSON-LD, verifies strict freshness, and returns canonical Job instances.
        """
        t0 = time.time()
        max_days = hours_old / 24.0

        logger.info(
            f"Targeting Apna search: '{search_term}' in '{location}' "
            f"(results_wanted={results_wanted}, max_days={max_days})"
        )

        collected_jobs: list[Job] = []
        seen_job_ids: set[str] = set()
        page = 1
        max_pages = 2

        with httpx.Client(headers=DEFAULT_HEADERS, timeout=self.timeout, follow_redirects=True) as client:
            while page <= max_pages and len(collected_jobs) < results_wanted:
                target_url, is_remote_search = self._build_search_url(search_term, location, page=page)
                logger.info(f"[Apna Page {page}] Fetching {target_url}...")

                try:
                    r = client.get(target_url)
                except Exception as e:
                    logger.error(f"Apna request failed on page {page}: {e}")
                    dur = round(time.time() - t0, 2)
                    return ApnaScrapeResult(
                        platform="apna",
                        search_query=search_term,
                        location=location,
                        total_found=len(collected_jobs),
                        jobs=collected_jobs,
                        duration_seconds=dur,
                        status="ERROR",
                        error=str(e),
                    )

                if r.status_code in [403, 429]:
                    logger.critical(f"Apna blocked request with HTTP {r.status_code}")
                    dur = round(time.time() - t0, 2)
                    return ApnaScrapeResult(
                        platform="apna",
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
                    logger.warning(f"Apna search page returned status {r.status_code}")
                    break

                soup = BeautifulSoup(r.text, "html.parser")
                card_links = [
                    a for a in soup.find_all("a", href=True)
                    if "/job/" in a.get("href")
                ]

                if not card_links:
                    logger.info(f"Apna returned 0 job links on page {page}")
                    break

                new_jobs_on_page = 0

                for card in card_links:
                    if len(collected_jobs) >= results_wanted:
                        break

                    href = card.get("href", "").strip()
                    m_id = re.search(r"-(\d+)$", href)
                    if not m_id:
                        continue
                    job_id = m_id.group(1)

                    if job_id in seen_job_ids:
                        # Skip already seen job ID, but continue processing the page
                        continue

                    seen_job_ids.add(job_id)
                    new_jobs_on_page += 1

                    # Preliminary title & card text check
                    card_text = card.get_text(separator=" | ", strip=True)
                    card_parts = [p.strip() for p in card_text.split("|") if p.strip()]
                    title_raw = card_parts[0] if card_parts else ""
                    title_clean = clean_job_title(title_raw)

                    if not title_clean:
                        continue

                    # Extract card experience
                    card_exp = next((p for p in card_parts if "year" in p.lower() or "fresher" in p.lower()), "")
                    e_min, e_max, exp_raw = self._parse_experience(card_exp)

                    discovery_url = f"{self.BASE_URL}{href}" if href.startswith("/") else href

                    # Fetch detail page to obtain authoritative datePosted and external apply URL
                    detail_res = self._fetch_detail_page(client, discovery_url)
                    if not detail_res:
                        continue

                    jp_data = detail_res["json_ld"]
                    date_posted_str = jp_data.get("datePosted")
                    posted_at_iso, _ = self._parse_date(date_posted_str, max_days=max_days)

                    # Final job title & company from JSON-LD
                    final_title = clean_job_title(jp_data.get("title") or title_clean)

                    comp_obj = jp_data.get("hiringOrganization")
                    company = comp_obj.get("name") if isinstance(comp_obj, dict) else "Confidential"

                    # Location & Remote status from evidence only
                    loc_obj = jp_data.get("jobLocation")
                    loc_str = "India"
                    if isinstance(loc_obj, dict):
                        addr = loc_obj.get("address", {})
                        if isinstance(addr, dict):
                            loc_str = addr.get("addressLocality") or addr.get("addressRegion") or "India"

                    work_mode = detail_res["work_mode"] or (
                        "Work from Home" if "work from home" in card_text.lower() else ""
                    )
                    is_remote_job = (
                        "work from home" in work_mode.lower()
                        or "remote" in loc_str.lower()
                    )

                    # Salary from JSON-LD or card text
                    card_sal = next((p for p in card_parts if "₹" in p or "not disclosed" in p.lower()), "")
                    s_min, s_max, s_raw = self._parse_salary(card_sal)

                    # Description
                    desc = jp_data.get("description") or ""

                    # Application URL & Type: Genuine external ATS URL or None (PLATFORM)
                    ext_url = detail_res["external_job_url"]
                    is_ext = detail_res["is_external_job"]
                    if is_ext and ext_url:
                        apply_url = ext_url
                        apply_type = "DIRECT"
                    else:
                        apply_url = discovery_url
                        apply_type = "PLATFORM"

                    job = Job(
                        id=f"apna-{job_id}",
                        title=final_title,
                        company=company,
                        source="apna",
                        location=loc_str,
                        is_remote=is_remote_job,
                        salary_raw=s_raw,
                        salary_min=s_min,
                        salary_max=s_max,
                        salary_currency="INR" if s_raw else None,
                        description=desc,
                        discovery_url=discovery_url,
                        apply_url=apply_url,
                        apply_type=apply_type,
                        posted_at=posted_at_iso,
                        experience_min=e_min,
                        experience_max=e_max,
                        experience_raw=exp_raw,
                        raw_data={
                            "apna_id": str(job_id),
                            "datePosted": date_posted_str,
                            "is_external": is_ext,
                            "external_job_url": ext_url,
                            "work_mode": work_mode,
                        },
                    )
                    collected_jobs.append(job)

                    if self.request_delay > 0:
                        time.sleep(self.request_delay)

                if new_jobs_on_page == 0:
                    logger.info(f"Page {page} contained no new unique jobs. Stopping pagination.")
                    break

                page += 1
                if self.request_delay > 0:
                    time.sleep(self.request_delay)

        dur = round(time.time() - t0, 2)
        logger.info(f"Apna scraping completed: {len(collected_jobs)} valid jobs in {dur}s")

        return ApnaScrapeResult(
            platform="apna",
            search_query=search_term,
            location=location,
            total_found=len(collected_jobs),
            jobs=collected_jobs,
            duration_seconds=dur,
            status="SUCCESS",
        )
