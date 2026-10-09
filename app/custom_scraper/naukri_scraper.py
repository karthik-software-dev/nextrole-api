"""Naukri Scraper Orchestrator.

In-house autonomous scraper for Naukri using Playwright with real browser telemetry.
Maps scraped job tuples directly into canonical models.job.Job.
"""

import logging
import re
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from playwright.sync_api import sync_playwright

from models.job import Job
from processing.experience_parser import extract_experience
from processing.salary_parser import parse_salary
from processing.deduplication import clean_job_title

logger = logging.getLogger("custom_scraper.naukri")

REFERENCE_DATE = datetime(2026, 9, 28, tzinfo=timezone.utc)


def parse_date_label(label: str | None, ref_date: datetime = REFERENCE_DATE) -> datetime | None:
    """Parses relative Naukri date strings ('2 days ago', 'few hours ago', '1 week ago') to datetime."""
    if not label:
        return None
    lbl = label.strip().lower()
    if "today" in lbl or "just now" in lbl or "few hours" in lbl:
        return ref_date
    elif "day" in lbl:
        m = re.search(r"(\d+)\+?\s*days?", lbl)
        days = int(m.group(1)) if m else 1
        return ref_date - timedelta(days=days)
    elif "week" in lbl:
        m = re.search(r"(\d+)\+?\s*weeks?", lbl)
        weeks = int(m.group(1)) if m else 1
        return ref_date - timedelta(days=weeks * 7)
    elif "month" in lbl or "30+" in lbl:
        m = re.search(r"(\d+)\+?\s*months?", lbl)
        months = int(m.group(1)) if m else 1
        return ref_date - timedelta(days=months * 30)
    return None


def parse_naukri_creation_date(text: str | None, max_ref_date: datetime = REFERENCE_DATE) -> datetime | None:
    """Extracts original job creation date from Naukri 12-digit job ID (DDMMYY format).

    Example:
        'nk-300826005162' -> 2026-08-30 (Day: 30, Month: 08, Year: 26)
    """
    if not text:
        return None
    m = re.search(r"(\d{2})(\d{2})(\d{2})\d{6}", text)
    if not m:
        return None
    day_str, month_str, year_str = m.group(1), m.group(2), m.group(3)
    try:
        day = int(day_str)
        month = int(month_str)
        year = 2000 + int(year_str)
        if 1 <= day <= 31 and 1 <= month <= 12 and 2020 <= year <= 2030:
            dt = datetime(year, month, day, tzinfo=timezone.utc)
            if dt <= max_ref_date + timedelta(days=2):
                return dt
    except Exception:
        pass
    return None



class NaukriScrapeResult:
    """Telemetry and job payload returned by NaukriScraper."""

    def __init__(
        self,
        platform: str = "naukri",
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


class NaukriScraper:
    """Autonomous Naukri scraper executing client-side telemetry via Playwright Chrome."""

    def __init__(self, headless: bool = True, timeout_ms: int = 20000):
        self.headless = headless
        self.timeout_ms = timeout_ms

    def scrape(
        self,
        search_term: str,
        location: str = "Bangalore",
        results_wanted: int = 25,
        hours_old: Optional[int] = 336,
    ) -> NaukriScrapeResult:
        """Fetches jobs for a query and location from Naukri.
        
        Maps each job tuple into the canonical models.job.Job representation.
        """
        t0 = time.time()
        query_slug = search_term.lower().replace(" ", "-").replace("+", "")
        loc_slug = location.lower().replace(" ", "-")

        if "remote" in loc_slug:
            url = f"https://www.naukri.com/{query_slug}-jobs?remote=true"
        else:
            url = f"https://www.naukri.com/{query_slug}-jobs-in-{loc_slug}"

        collected_jobs: list[Job] = []
        bot_detected = False
        error_msg: str | None = None
        status = "SUCCESS"

        try:
            with sync_playwright() as p:
                launch_args = [
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-infobars",
                    "--disable-dev-shm-usage",
                ]
                browser = None
                try:
                    browser = p.chromium.launch(headless=self.headless, args=launch_args)
                except Exception:
                    try:
                        browser = p.chromium.launch(channel="chrome", headless=self.headless, args=launch_args)
                    except Exception as b_err:
                        logger.warning(f"[Naukri] Browser launch unavailable on this environment: {b_err}")
                        return NaukriScrapeResult(search_query=search_term, location=location, jobs=[], total_found=0, bot_detected=False, error=str(b_err), status="UNAVAILABLE")
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
                    viewport={"width": 1280, "height": 800},
                    locale="en-US",
                )
                page = context.new_page()

                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=self.timeout_ms)
                    page.wait_for_selector(".srp-jobtuple-wrapper", timeout=10000)
                    time.sleep(1.0)
                except Exception as e:
                    logger.warning(f"Naukri wait selector timeout for '{search_term}': {e}")
                    error_msg = str(e)

                content = page.content()
                if "recaptcha" in content.lower() and "puzzle" in content.lower():
                    bot_detected = True
                    status = "BLOCKED"
                    error_msg = "Interactive CAPTCHA / bot challenge encountered"

                if not bot_detected:
                    cards = page.query_selector_all(".srp-jobtuple-wrapper")
                    for c in cards[:results_wanted]:
                        title_el = c.query_selector("a.title")
                        comp_el = c.query_selector("a.comp-name, .comp-name")
                        exp_el = c.query_selector(".exp-wrap, .expwdth")
                        sal_el = c.query_selector(".sal-wrap, .sal")
                        loc_el = c.query_selector(".loc-wrap, .loc")
                        url_el = c.query_selector("a.title")
                        tags_els = c.query_selector_all(".tags-gt li, .tag-li, .dot-gt")
                        date_el = c.query_selector(".job-post-day, .date")

                        title = title_el.inner_text().strip() if title_el else None
                        company = comp_el.inner_text().strip() if comp_el else None
                        job_url = url_el.get_attribute("href") if url_el else None

                        job_id = None
                        if job_url:
                            m_id = re.search(r"(\d{12})(?:\?|$)", job_url)
                            if m_id:
                                job_id = f"nk-{m_id.group(1)}"
                        if not job_id and job_url:
                            job_id = f"nk-{abs(hash(job_url))}"

                        experience = exp_el.inner_text().strip() if exp_el else None
                        salary = sal_el.inner_text().strip() if sal_el else None
                        loc_str = loc_el.inner_text().strip() if loc_el else None
                        skills = [t.inner_text().strip() for t in tags_els if t.inner_text().strip()]
                        date_label = date_el.inner_text().strip() if date_el else None

                        is_remote = False
                        if loc_str and ("remote" in loc_str.lower() or "hybrid" in loc_str.lower()):
                            is_remote = "remote" in loc_str.lower()
                        elif "remote" in loc_slug:
                            is_remote = True

                        sal_min, sal_max, _ = parse_salary(salary) if salary and salary.lower() != "not disclosed" else (None, None, "INR")
                        exp_min, exp_max, _ = extract_experience(experience) if experience else (None, None, None)
                        created_dt = parse_naukri_creation_date(job_id or job_url)
                        dt_parsed = parse_date_label(date_label)
                        # True creation date prevents recruiter re-promotions from masquerading as fresh
                        effective_dt = created_dt if created_dt else dt_parsed
                        posted_at_iso = effective_dt.strftime("%Y-%m-%d") if effective_dt else None

                        job = Job(
                            id=job_id or "nk-unknown",
                            title=clean_job_title(title or ""),
                            company=company or "",
                            location=loc_str or location,
                            is_remote=is_remote,
                            description=f"{title} at {company} in {loc_str}. Required Skills: {', '.join(skills)}.",
                            salary_raw=salary if salary and salary.lower() != "not disclosed" else None,
                            salary_min=sal_min,
                            salary_max=sal_max,
                            experience_raw=experience,
                            experience_min=exp_min,
                            experience_max=exp_max,
                            apply_url=job_url,
                            discovery_url=job_url,
                            source="naukri",
                            posted_at=posted_at_iso,
                            matched_skills=skills,
                            raw_data={
                                "date_label": date_label,
                                "original_creation_date": created_dt.strftime("%Y-%m-%d") if created_dt else None,
                                "is_repromoted": bool(created_dt and dt_parsed and (dt_parsed - created_dt).days > 7),
                            },
                        )
                        collected_jobs.append(job)

                browser.close()

            duration = round(time.time() - t0, 2)
            if not collected_jobs and error_msg and not bot_detected:
                status = "TIMEOUT"

            return NaukriScrapeResult(
                platform="naukri",
                search_query=search_term,
                location=location,
                total_found=len(collected_jobs),
                jobs=collected_jobs,
                duration_seconds=duration,
                status=status,
                error=error_msg,
                bot_detected=bot_detected,
            )

        except Exception as e:
            duration = round(time.time() - t0, 2)
            logger.error(f"Naukri scrape failed for query '{search_term}': {e}")
            return NaukriScrapeResult(
                platform="naukri",
                search_query=search_term,
                location=location,
                total_found=0,
                jobs=[],
                duration_seconds=duration,
                status="FAILED",
                error=str(e),
                bot_detected=False,
            )
