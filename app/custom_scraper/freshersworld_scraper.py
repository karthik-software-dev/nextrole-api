"""Freshersworld Scraper Orchestrator.

In-house autonomous scraper for Freshersworld (freshersworld.com) extracting job postings
directly into canonical models.job.Job.
Strictly non-invasive: requires no login, no CAPTCHA bypass, no Playwright, no proxies,
and uses standard TLS verification.
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

logger = logging.getLogger("custom_scraper.freshersworld")


def _get_pipeline_reference_date() -> datetime:
    """Reuses the canonical reference datetime from run_pipeline to ensure unified freshness calculation."""
    try:
        from run_pipeline import CURRENT_DATE
        return CURRENT_DATE
    except Exception:
        try:
            from custom_scraper import CURRENT_DATE
            return CURRENT_DATE
        except Exception:
            return datetime(2026, 9, 28, tzinfo=timezone.utc)


DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.freshersworld.com/",
}


class FreshersworldScrapeResult:
    """Telemetry and job payload returned by FreshersworldScraper."""

    def __init__(
        self,
        platform: str = "freshersworld",
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


class FreshersworldScraper:
    """Autonomous scraper for Freshersworld (freshersworld.com) job listings."""

    BASE_URL = "https://www.freshersworld.com"

    def __init__(
        self,
        timeout: float = 4.0,
        request_delay: float = 0.3,
        reference_date: datetime | None = None,
    ):
        self.timeout = timeout
        self.request_delay = request_delay
        self.reference_date = reference_date if reference_date is not None else _get_pipeline_reference_date()
        self.circuit_broken: bool = False

    def _build_search_url(self, search_term: str, location: str, page: int = 1) -> tuple[str, bool]:
        """Constructs canonical search URL for Freshersworld based on location and page offset.
        
        Returns:
            tuple[url: str, is_wfh_category: bool]
        """
        loc_clean = (location or "").strip().lower()
        is_wfh_category = False

        if "bangalore" in loc_clean or "bengaluru" in loc_clean:
            base_path = "/python-developer-jobs-in-bangalore/15152353365"
        elif "chennai" in loc_clean:
            base_path = "/python-developer-jobs-in-chennai/151523533125"
        elif "remote" in loc_clean or "wfh" in loc_clean or "work from home" in loc_clean:
            base_path = "/jobs/category/work-from-home-job-vacancies"
            is_wfh_category = True
        else:
            base_path = "/python-developer-jobs/1515235"

        offset = max(0, (page - 1) * 20)
        if offset > 0:
            url = f"{self.BASE_URL}{base_path}?&limit=20&offset={offset}"
        else:
            url = f"{self.BASE_URL}{base_path}"

        return url, is_wfh_category

    def _fetch_detail_page(self, client: httpx.Client, detail_url: str) -> dict[str, Any] | None:
        """Fetches the job detail page and extracts the schema.org JobPosting JSON-LD block and metadata.
        
        Returns None if request fails or if no schema.org JobPosting JSON-LD block is present.
        """
        try:
            resp = client.get(detail_url, headers=DEFAULT_HEADERS, timeout=self.timeout)
            if resp.status_code != 200:
                return None

            soup = BeautifulSoup(resp.text, "html.parser")
            jp_data = None

            for script in soup.find_all("script", type="application/ld+json"):
                if not script.string:
                    continue
                try:
                    data = json.loads(script.string)
                    if isinstance(data, dict) and data.get("@type") == "JobPosting":
                        jp_data = data
                        break
                except Exception:
                    continue

            if not jp_data:
                # Mandatory JSON-LD invariant: Detail page without JobPosting JSON-LD is discarded
                return None

            # Check explicit work mode badges from detail page
            wfh_badge = ""
            for tag in soup.select(".is_wfh, .work-mode, .job-type, span.badge"):
                tag_txt = tag.get_text(strip=True).lower()
                if "work from home" in tag_txt or "wfh" in tag_txt or "remote" in tag_txt:
                    wfh_badge = tag.get_text(strip=True)
                    break

            return {
                "json_ld": jp_data,
                "wfh_badge": wfh_badge,
                "soup": soup,
            }
        except Exception as e:
            logger.debug(f"Failed to fetch Freshersworld detail page {detail_url}: {e}")
            return None

    def _parse_date(self, date_str: str | None, max_days: float = 7.0) -> tuple[str | None, bool]:
        """Parses timezone-aware ISO date string into UTC ISO string and checks freshness against self.reference_date.
        
        Returns:
            tuple[posted_at_iso: str | None, is_fresh: bool]
        """
        if not date_str or not isinstance(date_str, str):
            return None, False

        try:
            dt = datetime.fromisoformat(date_str)
            if dt.tzinfo is None:
                # Assume IST (+05:30) if timezone naive
                dt = dt.replace(tzinfo=timezone(timedelta(hours=5, minutes=30)))
            dt_utc = dt.astimezone(timezone.utc)
            
            age_days = (self.reference_date - dt_utc).total_seconds() / 86400.0
            
            # Allow small negative age due to timezone/clock skew
            if age_days < -0.5:
                return dt_utc.isoformat(), False
            
            is_fresh = age_days <= max_days
            return dt_utc.isoformat(), is_fresh
        except Exception:
            return None, False

    def _parse_salary(
        self,
        base_salary: dict[str, Any] | None,
        card_sal_text: str | None,
    ) -> tuple[float | None, float | None, str | None, str | None]:
        """Parses salary into annualized min/max float INR, raw string, and currency.
        
        Strict rule:
        - If salary is explicitly disclosed and source identifies INR -> currency = "INR".
        - If salary is missing/undisclosed -> all fields remain None.
        
        Returns:
            tuple[salary_min, salary_max, salary_raw, salary_currency]
        """
        # 1. Attempt from JSON-LD baseSalary
        if isinstance(base_salary, dict):
            currency = base_salary.get("currency")
            val_obj = base_salary.get("value")
            unit = base_salary.get("unitText") or ""
            
            if isinstance(val_obj, dict):
                min_v = val_obj.get("minValue")
                max_v = val_obj.get("maxValue") or val_obj.get("value")
                unit_t = (val_obj.get("unitText") or unit or "").lower()

                if min_v is not None or max_v is not None:
                    try:
                        s_min = float(min_v) if min_v is not None else float(max_v)
                        s_max = float(max_v) if max_v is not None else float(min_v)
                        # Annualize if monthly
                        if "month" in unit_t:
                            s_min *= 12.0
                            s_max *= 12.0
                        
                        raw_str = f"{min_v} - {max_v} {unit_t}".strip()
                        curr_code = "INR" if currency and "INR" in str(currency).upper() else ("INR" if currency == "₹" else currency)
                        return s_min, s_max, raw_str, curr_code
                    except (ValueError, TypeError):
                        pass

        # 2. Attempt from card text fallback e.g. "9000 - 12000 Monthly"
        if card_sal_text and isinstance(card_sal_text, str):
            s_min, s_max, curr = parse_salary(card_sal_text)
            if s_min is not None:
                return s_min, s_max, card_sal_text.strip(), curr

        return None, None, None, None

    def _parse_experience(
        self,
        exp_req: dict[str, Any] | None,
        card_exp_text: str | None,
    ) -> tuple[int | None, int | None, str | None]:
        """Parses experience into integer years without upward rounding distortion via processing.experience_parser.
        
        Returns:
            tuple[experience_min, experience_max, experience_raw]
        """
        # 1. From JSON-LD experienceRequirements.monthsOfExperience
        if isinstance(exp_req, dict) and "monthsOfExperience" in exp_req:
            try:
                months = int(exp_req["monthsOfExperience"])
                exp_min = months // 12
                return exp_min, None, f"{months} months"
            except (ValueError, TypeError):
                pass

        # 2. From card text fallback e.g. "0-2 Years", "1-3 Years", "0 Years"
        if card_exp_text and isinstance(card_exp_text, str):
            e_min, e_max, e_raw = extract_experience(card_exp_text)
            if e_min is not None:
                return e_min, e_max, card_exp_text.strip()
            if "fresher" in card_exp_text.lower():
                return 0, 0, card_exp_text.strip()

        return None, None, card_exp_text.strip() if card_exp_text else None

        return None, None, None

    def _detect_remote(
        self,
        is_wfh_category: bool,
        card_wfh_badge: str,
        detail_wfh_badge: str,
        loc_str: str,
    ) -> bool:
        """Determines is_remote strictly from explicit category, badge, or location evidence.
        
        Never marks remote based solely on title or description.
        """
        if is_wfh_category:
            return True

        if card_wfh_badge and any(w in card_wfh_badge.lower() for w in ["work from home", "wfh", "remote"]):
            return True

        if detail_wfh_badge and any(w in detail_wfh_badge.lower() for w in ["work from home", "wfh", "remote"]):
            return True

        if loc_str and any(w in loc_str.lower() for w in ["work from home", "wfh", "remote"]):
            return True

        return False

    def scrape(
        self,
        search_term: str = "Python Backend Developer",
        location: str = "Bangalore",
        results_wanted: int = 10,
        hours_old: int = 336,
        max_pages: int = 2,
    ) -> FreshersworldScrapeResult:
        """Scrapes Freshersworld job listings under a given query and location."""
        t_start = time.time()
        max_days = hours_old / 24.0
        collected_jobs: list[Job] = []
        seen_job_ids: set[str] = set()

        if self.circuit_broken:
            logger.warning("Freshersworld circuit breaker active. Skipping further requests.")
            return FreshersworldScrapeResult(
                platform="freshersworld",
                search_query=search_term,
                location=location,
                total_found=0,
                jobs=[],
                duration_seconds=0.0,
                status="BLOCKED",
                error="Circuit breaker active",
                bot_detected=True,
            )

        with httpx.Client(headers=DEFAULT_HEADERS, timeout=self.timeout, follow_redirects=True) as client:
            for page in range(1, max_pages + 1):
                if len(collected_jobs) >= results_wanted:
                    break

                search_url, is_wfh_category = self._build_search_url(search_term, location, page=page)
                logger.info(f"Fetching Freshersworld [Page {page}] {search_url}")

                try:
                    resp = client.get(search_url)
                except (httpx.TimeoutException, httpx.RequestError) as e:
                    self.circuit_broken = True
                    logger.warning(f"Freshersworld network error/timeout on page {page}: {e}. Circuit breaker tripped.")
                    dur = round(time.time() - t_start, 2)
                    return FreshersworldScrapeResult(
                        platform="freshersworld",
                        search_query=search_term,
                        location=location,
                        total_found=len(collected_jobs),
                        jobs=collected_jobs,
                        duration_seconds=dur,
                        status="ERROR",
                        error=str(e),
                        bot_detected=False,
                    )
                except Exception as e:
                    self.circuit_broken = True
                    logger.warning(f"Freshersworld unexpected error on page {page}: {e}. Circuit breaker tripped.")
                    dur = round(time.time() - t_start, 2)
                    return FreshersworldScrapeResult(
                        platform="freshersworld",
                        search_query=search_term,
                        location=location,
                        total_found=len(collected_jobs),
                        jobs=collected_jobs,
                        duration_seconds=dur,
                        status="ERROR",
                        error=str(e),
                        bot_detected=False,
                    )

                if resp.status_code != 200:
                    self.circuit_broken = True
                    is_block = resp.status_code in (403, 429) or "security check" in resp.text.lower()
                    status_val = "BLOCKED" if is_block else "FAILED"
                    logger.warning(f"Freshersworld HTTP {resp.status_code} on {search_url}. Circuit breaker tripped.")
                    dur = round(time.time() - t_start, 2)
                    return FreshersworldScrapeResult(
                        platform="freshersworld",
                        search_query=search_term,
                        location=location,
                        total_found=len(collected_jobs),
                        jobs=collected_jobs,
                        duration_seconds=dur,
                        status=status_val,
                        error=f"HTTP {resp.status_code}",
                        bot_detected=is_block,
                    )

                soup = BeautifulSoup(resp.text, "html.parser")
                cards = soup.select(".job-container[job_id]")

                if not cards:
                    logger.info(f"No job cards found on Freshersworld page {page}. Stopping pagination.")
                    break

                new_cards_on_page = 0

                for card in cards:
                    if len(collected_jobs) >= results_wanted:
                        break

                    job_id = card.get("job_id")
                    if not job_id:
                        m_id = re.search(r"-(\d+)$", card.get("job_display_url", ""))
                        job_id = m_id.group(1) if m_id else None

                    if not job_id or job_id in seen_job_ids:
                        continue

                    seen_job_ids.add(job_id)
                    new_cards_on_page += 1

                    # Card title
                    card_title_tag = card.select_one(".latest-jobs-title, .job-title, h3, a[job_display_url]")
                    card_title_raw = card_title_tag.get_text(strip=True) if card_title_tag else ""
                    title_clean = clean_job_title(card_title_raw)

                    # Card experience
                    exp_tag = card.select_one(".exp-span, span[title*='experience']")
                    card_exp_text = exp_tag.get_text(strip=True) if exp_tag else None
                    c_emin, _, _ = self._parse_experience(None, card_exp_text)

                    # Detail URL
                    detail_url = card.get("job_display_url")
                    if not detail_url:
                        a_link = card.select_one("a[href*='/jobs/']")
                        if a_link and a_link.get("href"):
                            href = a_link["href"]
                            detail_url = href if href.startswith("http") else f"{self.BASE_URL}{href}"

                    if not detail_url:
                        continue

                    # Card WFH badge
                    card_wfh_badge = ""
                    card_wfh_tag = card.select_one(".is_wfh, .work-mode")
                    if card_wfh_tag:
                        card_wfh_badge = card_wfh_tag.get_text(strip=True)

                    # Card salary text
                    sal_tag = card.select_one(".sal-span, span[title*='salary']")
                    card_sal_text = sal_tag.get_text(strip=True) if sal_tag else None

                    # Card location text
                    card_locs = [a.get_text(strip=True) for a in card.select("a[href*='jobs-in-']")]
                    card_loc_str = ", ".join(card_locs) if card_locs else None

                    # Mandatory Detail Page Fetch
                    time.sleep(self.request_delay)
                    detail_data = self._fetch_detail_page(client, detail_url)
                    if not detail_data:
                        # Missing detail page or missing JobPosting JSON-LD -> strictly discard
                        continue

                    jp_data = detail_data["json_ld"]
                    date_posted_str = jp_data.get("datePosted")
                    posted_at_iso, _ = self._parse_date(date_posted_str, max_days=max_days)

                    # Final Title & Company from JSON-LD
                    final_title = clean_job_title(jp_data.get("title") or title_clean)

                    comp_obj = jp_data.get("hiringOrganization")
                    company = comp_obj.get("name") if isinstance(comp_obj, dict) else "Confidential"

                    # Location extraction
                    loc_obj = jp_data.get("jobLocation")
                    location_str = card_loc_str or "India"
                    if isinstance(loc_obj, list) and loc_obj:
                        first_loc = loc_obj[0]
                        if isinstance(first_loc, dict):
                            addr = first_loc.get("address", {})
                            if isinstance(addr, dict):
                                location_str = addr.get("addressLocality") or addr.get("addressRegion") or location_str
                    elif isinstance(loc_obj, dict):
                        addr = loc_obj.get("address", {})
                        if isinstance(addr, dict):
                            location_str = addr.get("addressLocality") or addr.get("addressRegion") or location_str

                    # Remote Detection strictly from explicit evidence
                    detail_wfh_badge = detail_data.get("wfh_badge", "")
                    is_remote_job = self._detect_remote(
                        is_wfh_category=is_wfh_category,
                        card_wfh_badge=card_wfh_badge,
                        detail_wfh_badge=detail_wfh_badge,
                        loc_str=location_str,
                    )

                    # Salary parsing: no currency fabrication if undisclosed
                    s_min, s_max, s_raw, s_curr = self._parse_salary(
                        jp_data.get("baseSalary"),
                        card_sal_text,
                    )

                    # Experience parsing: floor division without upward rounding
                    e_min, e_max, e_raw = self._parse_experience(
                        jp_data.get("experienceRequirements"),
                        card_exp_text,
                    )

                    # Description
                    desc = jp_data.get("description") or ""

                    job = Job(
                        id=f"freshersworld_{job_id}",
                        title=final_title,
                        company=company,
                        source="freshersworld",
                        location=location_str,
                        is_remote=is_remote_job,
                        salary_raw=s_raw,
                        salary_min=s_min,
                        salary_max=s_max,
                        salary_currency=s_curr,
                        description=desc,
                        discovery_url=detail_url,
                        apply_url=detail_url,
                        posted_at=posted_at_iso,
                        apply_type="PLATFORM",
                        experience_min=e_min,
                        experience_max=e_max,
                        experience_raw=e_raw,
                        matched_skills=[],
                        raw_data={
                            "job_id": str(job_id),
                            "datePosted": date_posted_str,
                            "is_wfh_category": is_wfh_category,
                            "work_mode": detail_wfh_badge or card_wfh_badge,
                        },
                    )
                    collected_jobs.append(job)

                if new_cards_on_page == 0:
                    logger.info(f"Page {page} contained only duplicate cards. Stopping pagination.")
                    break

        duration = round(time.time() - t_start, 2)
        return FreshersworldScrapeResult(
            platform="freshersworld",
            search_query=search_term,
            location=location,
            total_found=len(collected_jobs),
            jobs=collected_jobs,
            duration_seconds=duration,
            status="SUCCESS",
        )


def scrape_freshersworld_jobs(
    results_wanted: int = 10,
    search_term: str = "Python Backend Developer",
) -> list[Job]:
    """Standardized entry point for Freshersworld scraper across multi-location rotation."""
    scraper = FreshersworldScraper()
    res = scraper.scrape(
        search_term=search_term,
        location="Bangalore",
        results_wanted=results_wanted,
        hours_old=336,
        max_pages=2,
    )
    return res.jobs
