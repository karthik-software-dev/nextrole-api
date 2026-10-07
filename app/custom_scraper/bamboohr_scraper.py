"""BambooHR ATS Scraper.

Ingests public job postings from BambooHR-hosted career sites.
Uses public unauthenticated endpoints:
- Catalog: https://{subdomain}.bamboohr.com/careers/list
- Detail:  https://{subdomain}.bamboohr.com/careers/{id}/detail

Strict requirements:
- Authoritative publication date: datePosted (YYYY-MM-DD) evaluated against pipeline reference_date.
- Structured locationType: 1 = Remote, 2 = Hybrid, 0 = Onsite. Never infer from text.
- Genuine jobOpeningShareUrl as application URL.
- Structured salary extraction from compensation if available.
- Deterministic deduplication ID: bamboohr_{subdomain}_{job_id}.
- Zero browser overhead, zero auth bypass, 100% public REST API.
"""

import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import httpx

from custom_scraper.company_registry import get_companies_by_ats
from models.job import Job
from processing.deduplication import clean_job_title
from processing.experience_parser import extract_experience
from processing.salary_parser import parse_salary

logger = logging.getLogger(__name__)

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/130.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
}


@dataclass
class BambooHRScrapeResult:
    """Encapsulates the output of a BambooHR scrape invocation."""

    jobs: List[Job] = field(default_factory=list)
    status: str = "SUCCESS"  # SUCCESS, EMPTY, ERROR, BLOCKED
    error: Optional[str] = None
    bot_detected: bool = False
    duration_seconds: float = 0.0


def _has_keyword(kw: str, text: str) -> bool:
    """Helper for case-insensitive exact keyword match."""
    return bool(re.search(rf"\b{re.escape(kw)}\b", text, re.I))


class BambooHRScraper:
    """Adapter for scraping career sites hosted on BambooHR."""

    def __init__(
        self,
        reference_date: Optional[datetime] = None,
        companies: Optional[List[Dict[str, Any]]] = None,
        timeout: float = 12.0,
    ):
        self.reference_date = reference_date or datetime.now(timezone.utc)
        self.companies = companies if companies is not None else get_companies_by_ats("bamboohr")
        self.timeout = timeout

    def _parse_authoritative_date(self, date_str: Optional[str], *args: Any, **kwargs: Any) -> Tuple[Optional[str], bool]:
        """Parses BambooHR datePosted (YYYY-MM-DD) to UTC ISO string.
        
        Freshness decisions are handled centrally by CentralJobProcessor.
        """
        if not date_str or not isinstance(date_str, str):
            return None, False

        clean_str = date_str.strip()[:10]
        try:
            posted_dt = datetime.strptime(clean_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            return posted_dt.isoformat(), True
        except Exception as e:
            logger.debug(f"Failed parsing BambooHR date '{date_str}': {e}")
            return None, False

    def _detect_remote(self, location_type: Any) -> bool:
        """Determines remote status strictly from BambooHR locationType:

        1 = Remote
        2 = Hybrid -> False (not full remote)
        0 = Onsite -> False
        """
        try:
            val = int(location_type)
            return val == 1
        except (ValueError, TypeError):
            return False

    def _matches_target_geography(
        self,
        location_dict: Optional[Dict[str, Any]],
        ats_location_dict: Optional[Dict[str, Any]],
        is_remote: bool,
        target_loc: Optional[str] = None,
    ) -> Tuple[bool, bool]:
        """Evaluates whether the posting matches target locations (Bangalore, Chennai, Remote)."""
        loc_str = ""
        country_str = ""
        if isinstance(location_dict, dict):
            loc_str += f" {location_dict.get('city') or ''} {location_dict.get('state') or ''}"
            country_str += f" {location_dict.get('addressCountry') or ''}"
        if isinstance(ats_location_dict, dict):
            loc_str += f" {ats_location_dict.get('city') or ''} {ats_location_dict.get('state') or ''}"
            country_str += f" {ats_location_dict.get('country') or ''}"

        combined_loc = loc_str.lower()
        combined_country = country_str.lower()

        is_blr = "bangalore" in combined_loc or "bengaluru" in combined_loc
        is_maa = "chennai" in combined_loc
        is_in = "india" in combined_country or "in" in combined_country or is_blr or is_maa

        if is_remote:
            if target_loc:
                t_clean = target_loc.strip().lower()
                if "remote" in t_clean:
                    return True, True
                elif "bangalore" in t_clean or "bengaluru" in t_clean:
                    return is_blr or is_in or True, True
                elif "chennai" in t_clean:
                    return is_maa or is_in or True, True
            return True, True

        matches_city = is_blr or is_maa
        if target_loc:
            t_clean = target_loc.strip().lower()
            if "bangalore" in t_clean or "bengaluru" in t_clean:
                matches_city = is_blr
            elif "chennai" in t_clean:
                matches_city = is_maa
            elif "remote" in t_clean:
                matches_city = False

        return matches_city, False

    def _parse_experience(self, text: Optional[str]) -> Tuple[Optional[int], Optional[int], Optional[str]]:
        """Extracts experience requirements via processing.experience_parser."""
        return extract_experience(text)

    def _parse_compensation(self, comp_data: Any) -> Tuple[Optional[float], Optional[float], Optional[str], Optional[str]]:
        """Parses structured compensation via processing.salary_parser."""
        if not comp_data:
            return None, None, None, None

        raw_str = str(comp_data).strip()
        s_min, s_max, curr = parse_salary(raw_str)
        return s_min, s_max, curr, raw_str if s_min is not None else None

    def scrape(
        self,
        search_term: str = "",
        location: str = "",
        results_wanted: int = 50,
        hours_old: int = 336,
    ) -> BambooHRScrapeResult:
        """Scrapes open roles across registered BambooHR company career boards."""
        t_start = time.time()
        max_days = hours_old / 24.0
        collected_jobs: List[Job] = []
        seen_job_ids: set[str] = set()

        with httpx.Client(headers=DEFAULT_HEADERS, timeout=self.timeout, follow_redirects=True) as client:
            for comp in self.companies:
                if len(collected_jobs) >= results_wanted:
                    break

                company_name = comp.get("company", "Unknown")
                subdomain = comp.get("ats_identifier", "")
                if not subdomain:
                    logger.warning(f"BambooHR employer '{company_name}' missing ats_identifier. Skipping.")
                    continue

                catalog_url = f"https://{subdomain}.bamboohr.com/careers/list"
                logger.info(f"Querying BambooHR board: '{company_name}' ({subdomain})")

                try:
                    resp = client.get(catalog_url)
                except httpx.TimeoutException:
                    logger.warning(f"BambooHR catalog timeout for '{subdomain}'")
                    continue
                except Exception as e:
                    logger.warning(f"BambooHR network error for '{subdomain}': {e}")
                    continue

                if resp.status_code == 404:
                    logger.warning(f"BambooHR board '{subdomain}' returned 404. Skipping.")
                    continue
                elif resp.status_code == 429:
                    logger.warning(f"BambooHR rate limit (429) for '{subdomain}'. Skipping.")
                    continue
                elif resp.status_code != 200:
                    logger.warning(f"BambooHR board '{subdomain}' returned HTTP {resp.status_code}")
                    continue

                try:
                    data = resp.json()
                except Exception as e:
                    logger.warning(f"Malformed JSON from BambooHR catalog '{subdomain}': {e}")
                    continue

                raw_list = data.get("result", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
                if not isinstance(raw_list, list):
                    continue

                for item in raw_list:
                    if len(collected_jobs) >= results_wanted:
                        break

                    job_id = str(item.get("id") or "").strip()
                    if not job_id:
                        continue

                    dedup_id = f"bamboohr_{subdomain}_{job_id}"
                    if dedup_id in seen_job_ids:
                        continue
                    seen_job_ids.add(dedup_id)

                    raw_title = item.get("jobOpeningName", "")
                    title_clean = clean_job_title(raw_title)
                    if not title_clean:
                        continue

                    loc_dict = item.get("location") if isinstance(item.get("location"), dict) else {}
                    ats_loc_dict = item.get("atsLocation") if isinstance(item.get("atsLocation"), dict) else {}
                    is_remote = self._detect_remote(item.get("locationType"))

                    # Phase 2: Fetch detail endpoint for authoritative datePosted, description, salary
                    detail_url = f"https://{subdomain}.bamboohr.com/careers/{job_id}/detail"
                    try:
                        d_resp = client.get(detail_url)
                    except Exception as e:
                        logger.warning(f"BambooHR detail request failed for {job_id}: {e}")
                        continue

                    if d_resp.status_code != 200:
                        continue

                    try:
                        d_json = d_resp.json()
                        job_opening = d_json.get("result", {}).get("jobOpening", {})
                    except Exception as e:
                        logger.warning(f"Malformed JSON from BambooHR detail {job_id}: {e}")
                        continue

                    # Check status
                    status_str = str(job_opening.get("jobOpeningStatus") or "Open").strip().lower()
                    if status_str != "open":
                        continue

                    # Authoritative timestamp extraction
                    raw_date = job_opening.get("datePosted")
                    posted_iso, _ = self._parse_authoritative_date(raw_date)

                    # Description & Experience
                    desc_html = job_opening.get("description") or ""
                    clean_desc = re.sub(r"<[^>]+>", " ", desc_html).strip()
                    exp_min, exp_max, exp_raw = self._parse_experience(clean_desc)

                    # Compensation
                    sal_min, sal_max, sal_curr, sal_raw = self._parse_compensation(job_opening.get("compensation"))

                    # Application URL
                    share_url = job_opening.get("jobOpeningShareUrl") or f"https://{subdomain}.bamboohr.com/careers/{job_id}"

                    # Canonical location string
                    loc_city = loc_dict.get("city") or ats_loc_dict.get("city") or ""
                    loc_state = loc_dict.get("state") or ats_loc_dict.get("state") or ""
                    loc_country = loc_dict.get("addressCountry") or ats_loc_dict.get("country") or ""
                    parts = [p for p in [loc_city, loc_state, loc_country] if p]
                    final_loc = ", ".join(parts) if parts else ("Remote" if is_remote else "Bangalore")

                    canonical_job = Job(
                        id=dedup_id,
                        title=title_clean,
                        company=company_name,
                        source="bamboohr",
                        ats_provider="bamboohr",
                        location=final_loc,
                        is_remote=is_remote,
                        salary_min=sal_min,
                        salary_max=sal_max,
                        salary_currency=sal_curr,
                        salary_raw=sal_raw,
                        description=clean_desc,
                        discovery_url=share_url,
                        apply_url=share_url,
                        apply_type="DIRECT_ATS",
                        posted_at=posted_iso,
                        experience_min=exp_min,
                        experience_max=exp_max,
                        experience_raw=exp_raw,
                        raw_data={
                            "bamboohr_job_id": job_id,
                            "subdomain": subdomain,
                            "department": job_opening.get("departmentLabel"),
                            "employmentType": job_opening.get("employmentStatusLabel"),
                            "locationType": job_opening.get("locationType"),
                            "datePosted": raw_date,
                        },
                    )
                    collected_jobs.append(canonical_job)

        duration = round(time.time() - t_start, 2)
        logger.info(f"BambooHR scrape completed: collected {len(collected_jobs)} fresh postings in {duration}s")
        return BambooHRScrapeResult(
            jobs=collected_jobs,
            status="SUCCESS",
            duration_seconds=duration,
        )
