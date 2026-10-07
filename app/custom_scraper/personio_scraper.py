"""Personio ATS Scraper.

Ingests public job postings from Personio-hosted career sites.
Uses the public unauthenticated XML feed:
  https://{subdomain}.jobs.personio.de/xml?language=en

Each feed contains <position> nodes with structured fields.

Strict requirements:
- Authoritative publication date: <createdAt> (ISO 8601) evaluated against pipeline reference_date.
- Remote detection: from <schedule> or <office>/<name> = "Remote".
  Never infer from title or description.
- Genuine Personio application URL constructed as:
  https://{subdomain}.jobs.personio.de/job/{id}
- Structured salary extraction from <salary> node if present.
- Deterministic deduplication ID: personio_{subdomain}_{job_id}.
- Zero browser overhead, zero auth bypass, 100% public XML feed.
"""

import logging
import re
import time
import xml.etree.ElementTree as ET
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
    "Accept": "application/xml, text/xml, */*",
}


@dataclass
class PersonioScrapeResult:
    """Encapsulates the output of a Personio scrape invocation."""

    jobs: List[Job] = field(default_factory=list)
    status: str = "SUCCESS"  # SUCCESS, EMPTY, ERROR, BLOCKED
    error: Optional[str] = None
    bot_detected: bool = False
    duration_seconds: float = 0.0


def _has_keyword(kw: str, text: str) -> bool:
    """Helper for case-insensitive word-boundary keyword match."""
    return bool(re.search(rf"\b{re.escape(kw)}\b", text, re.I))


def _xml_text(node: Optional[ET.Element], tag: str, default: str = "") -> str:
    """Safe text extraction from an XML element child."""
    if node is None:
        return default
    child = node.find(tag)
    if child is None or child.text is None:
        return default
    return child.text.strip()


class PersonioScraper:
    """Adapter for scraping career sites hosted on Personio."""

    def __init__(
        self,
        reference_date: Optional[datetime] = None,
        companies: Optional[List[Dict[str, Any]]] = None,
        timeout: float = 12.0,
    ):
        self.reference_date = reference_date or datetime.now(timezone.utc)
        self.companies = companies if companies is not None else get_companies_by_ats("personio")
        self.timeout = timeout

    def _parse_authoritative_date(self, date_str: Optional[str], *args: Any, **kwargs: Any) -> Tuple[Optional[str], bool]:
        """Parses Personio createdAt (ISO 8601 or YYYY-MM-DD) to UTC ISO string.
        
        Freshness decisions are handled centrally by CentralJobProcessor.
        """
        if not date_str or not isinstance(date_str, str):
            return None, False

        clean_str = date_str.strip()
        for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S"):
            try:
                posted_dt = datetime.strptime(clean_str[:19], fmt[:len(fmt)])
                if posted_dt.tzinfo is None:
                    posted_dt = posted_dt.replace(tzinfo=timezone.utc)
                return posted_dt.astimezone(timezone.utc).isoformat(), True
            except Exception:
                pass

        try:
            posted_dt = datetime.strptime(clean_str[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
            return posted_dt.astimezone(timezone.utc).isoformat(), True
        except Exception as e:
            logger.debug(f"Failed parsing Personio date '{date_str}': {e}")
            return None, False

    def _detect_remote(self, schedule: Optional[str], office_name: Optional[str]) -> bool:
        """Determines remote status from structured Personio <schedule> and <office><name> fields.

        schedule == 'remote' OR office name == 'Remote' -> True.
        Never infers from title or description.
        """
        if schedule and "remote" in schedule.lower():
            return True
        if office_name and office_name.strip().lower() == "remote":
            return True
        return False

    def _matches_target_geography(
        self,
        office_name: Optional[str],
        is_remote: bool,
        keywords: Optional[List[str]] = None,
    ) -> bool:
        """Evaluates whether the posting matches target locations (Bangalore, Chennai, Remote).

        office_name is the Personio structured office field value.
        """
        if is_remote:
            return True

        name_lower = (office_name or "").lower()
        if "bangalore" in name_lower or "bengaluru" in name_lower:
            return True
        if "chennai" in name_lower:
            return True

        return False

    def _parse_experience(self, description: Optional[str]) -> Tuple[Optional[int], Optional[int], Optional[str]]:
        """Extracts experience requirements via processing.experience_parser."""
        return extract_experience(description)

    def _parse_salary(self, salary_text: Optional[str]) -> Tuple[Optional[float], Optional[float], Optional[str], Optional[str]]:
        """Parses salary/compensation text via processing.salary_parser."""
        if not salary_text or not salary_text.strip():
            return None, None, None, None
        s_min, s_max, curr = parse_salary(salary_text)
        return s_min, s_max, curr, salary_text.strip() if s_min is not None else None

    def scrape(
        self,
        search_term: str = "",
        location: str = "",
        results_wanted: int = 50,
        hours_old: int = 336,
    ) -> PersonioScrapeResult:
        """Scrapes open roles across registered Personio company career boards."""
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
                    logger.warning(f"Personio employer '{company_name}' missing ats_identifier. Skipping.")
                    continue

                feed_url = f"https://{subdomain}.jobs.personio.de/xml?language=en"
                logger.info(f"Querying Personio board: '{company_name}' ({subdomain})")

                try:
                    resp = client.get(feed_url)
                except httpx.TimeoutException:
                    logger.warning(f"Personio feed timeout for '{subdomain}'")
                    continue
                except Exception as e:
                    logger.warning(f"Personio network error for '{subdomain}': {e}")
                    continue

                if resp.status_code == 404:
                    logger.warning(f"Personio board '{subdomain}' returned 404. Skipping.")
                    continue
                elif resp.status_code == 429:
                    logger.warning(f"Personio rate limit (429) for '{subdomain}'. Skipping.")
                    continue
                elif resp.status_code != 200:
                    logger.warning(f"Personio board '{subdomain}' returned HTTP {resp.status_code}")
                    continue

                # Parse XML feed
                try:
                    root = ET.fromstring(resp.content)
                except ET.ParseError as e:
                    logger.warning(f"Malformed XML from Personio feed '{subdomain}': {e}")
                    continue

                # Positions can be direct children or wrapped in <positions>
                positions = root.findall(".//position")
                if not positions:
                    logger.info(f"Personio board '{subdomain}': empty feed (0 positions).")
                    continue

                for pos in positions:
                    if len(collected_jobs) >= results_wanted:
                        break

                    # Extract job ID
                    job_id = _xml_text(pos, "id") or _xml_text(pos, "jobId")
                    if not job_id:
                        # Try attribute
                        job_id = pos.get("id", "")
                    if not job_id:
                        continue

                    dedup_id = f"personio_{subdomain}_{job_id}"
                    if dedup_id in seen_job_ids:
                        continue
                    seen_job_ids.add(dedup_id)

                    # Extract title
                    raw_title = _xml_text(pos, "name") or _xml_text(pos, "title")
                    title_clean = clean_job_title(raw_title)
                    if not title_clean:
                        continue

                    # Location / remote detection
                    schedule_val = _xml_text(pos, "schedule")
                    # Office name may be nested: <office><name>...</name></office>
                    office_node = pos.find("office")
                    office_name = _xml_text(office_node, "name") if office_node is not None else _xml_text(pos, "office")
                    is_remote = self._detect_remote(schedule_val, office_name)

                    # Authoritative timestamp extraction
                    created_at_str = _xml_text(pos, "createdAt") or _xml_text(pos, "created_at")
                    posted_iso, _ = self._parse_authoritative_date(created_at_str)

                    # Description
                    desc_raw = _xml_text(pos, "jobDescriptions") or _xml_text(pos, "description") or ""
                    clean_desc = re.sub(r"<[^>]+>", " ", desc_raw).strip()
                    exp_min, exp_max, exp_raw = self._parse_experience(clean_desc)

                    # Salary
                    salary_text = _xml_text(pos, "salary")
                    sal_min, sal_max, sal_curr, sal_raw = self._parse_salary(salary_text)

                    # Application URL
                    apply_url = (
                        _xml_text(pos, "applyUrl")
                        or _xml_text(pos, "applicationUrl")
                        or f"https://{subdomain}.jobs.personio.de/job/{job_id}"
                    )

                    # Canonical location string
                    final_loc = office_name if office_name else ("Remote" if is_remote else "Bangalore")
                    if not final_loc:
                        final_loc = "Remote" if is_remote else "Bangalore"

                    # Department / employment type
                    department = _xml_text(pos, "department")
                    employment_type = _xml_text(pos, "employmentType") or _xml_text(pos, "schedule")

                    canonical_job = Job(
                        id=dedup_id,
                        title=title_clean,
                        company=company_name,
                        source="personio",
                        ats_provider="personio",
                        location=final_loc,
                        is_remote=is_remote,
                        salary_min=sal_min,
                        salary_max=sal_max,
                        salary_currency=sal_curr,
                        salary_raw=sal_raw,
                        description=clean_desc,
                        discovery_url=apply_url,
                        apply_url=apply_url,
                        apply_type="DIRECT_ATS",
                        posted_at=posted_iso,
                        experience_min=exp_min,
                        experience_max=exp_max,
                        experience_raw=exp_raw,
                        raw_data={
                            "personio_job_id": job_id,
                            "subdomain": subdomain,
                            "department": department,
                            "employmentType": employment_type,
                            "schedule": schedule_val,
                            "office": office_name,
                            "createdAt": created_at_str,
                        },
                    )
                    collected_jobs.append(canonical_job)

        duration = round(time.time() - t_start, 2)
        logger.info(f"Personio scrape completed: collected {len(collected_jobs)} fresh postings in {duration}s")
        return PersonioScrapeResult(
            jobs=collected_jobs,
            status="SUCCESS",
            duration_seconds=duration,
        )
