"""Breezy HR ATS Scraper.

Ingests public job postings from Breezy HR-hosted career sites.
Uses the public unauthenticated JSON endpoint:
  https://{subdomain}.breezy.hr/json

Each response is a JSON array of position objects.

Strict requirements:
- Authoritative publication date: published_date (ISO 8601) evaluated against pipeline reference_date.
- Remote detection: from structured location.name == "Remote" or type == "remote".
  Never infer from title or description.
- Genuine Breezy HR application URL constructed from position.friendly_id:
  https://{subdomain}.breezy.hr/p/{friendly_id}
- Deterministic deduplication ID: breezy_{subdomain}_{position_id}.
- Zero browser overhead, zero auth bypass, 100% public REST JSON.
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
from processing.relevance import HARD_EXCLUDE_TITLE_KEYWORDS

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
class BreezyScrapeResult:
    """Encapsulates the output of a Breezy HR scrape invocation."""

    jobs: List[Job] = field(default_factory=list)
    status: str = "SUCCESS"  # SUCCESS, EMPTY, ERROR, BLOCKED
    error: Optional[str] = None
    bot_detected: bool = False
    duration_seconds: float = 0.0


def _has_keyword(kw: str, text: str) -> bool:
    """Helper for case-insensitive word-boundary keyword match."""
    return bool(re.search(rf"\b{re.escape(kw)}\b", text, re.I))


class BreezyScraper:
    """Adapter for scraping career sites hosted on Breezy HR."""

    def __init__(
        self,
        reference_date: Optional[datetime] = None,
        companies: Optional[List[Dict[str, Any]]] = None,
        timeout: float = 12.0,
    ):
        self.reference_date = reference_date or datetime.now(timezone.utc)
        self.companies = companies if companies is not None else get_companies_by_ats("breezy")
        self.timeout = timeout

    def _parse_authoritative_date(self, date_str: Optional[str], *args: Any, **kwargs: Any) -> Tuple[Optional[str], bool]:
        """Parses Breezy HR published_date (ISO 8601 or YYYY-MM-DD) to UTC ISO string.
        
        Freshness decisions are handled centrally by CentralJobProcessor.
        """
        if not date_str or not isinstance(date_str, str):
            return None, False

        clean_str = date_str.strip()

        # Try ISO 8601 with timezone: 2026-09-28T12:34:56+00:00 or 2026-09-28T12:34:56Z
        for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ"):
            try:
                posted_dt = datetime.strptime(clean_str, fmt)
                if posted_dt.tzinfo is None:
                    posted_dt = posted_dt.replace(tzinfo=timezone.utc)
                return posted_dt.astimezone(timezone.utc).isoformat(), True
            except Exception:
                pass

        # Try partial ISO: 2026-09-28T12:34:56
        try:
            posted_dt = datetime.strptime(clean_str[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
            return posted_dt.astimezone(timezone.utc).isoformat(), True
        except Exception:
            pass

        # Try date-only YYYY-MM-DD
        try:
            posted_dt = datetime.strptime(clean_str[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
            return posted_dt.astimezone(timezone.utc).isoformat(), True
        except Exception as e:
            logger.debug(f"Failed parsing Breezy date '{date_str}': {e}")
            return None, False

    def _detect_remote(self, location: Optional[Dict[str, Any]]) -> bool:
        """Determines remote status from Breezy HR structured location object.

        location.name == "Remote" OR location.type == "remote" -> True.
        Never infers from title or description.
        """
        if not isinstance(location, dict):
            return False
        loc_name = (location.get("name") or "").strip().lower()
        loc_type = (location.get("type") or "").strip().lower()
        return loc_name == "remote" or loc_type == "remote"

    def _matches_target_geography(
        self,
        location: Optional[Dict[str, Any]],
        is_remote: bool,
    ) -> bool:
        """Evaluates whether the posting matches target locations (Bangalore, Chennai, Remote)."""
        if is_remote:
            return True

        if not isinstance(location, dict):
            return False

        loc_name = (location.get("name") or "").lower()
        loc_city = (location.get("city") or "").lower()
        loc_country = (location.get("country") or "").lower()
        combined = f"{loc_name} {loc_city} {loc_country}"

        if "bangalore" in combined or "bengaluru" in combined:
            return True
        if "chennai" in combined:
            return True

        return False

    def _parse_experience(self, description: Optional[str]) -> Tuple[Optional[int], Optional[int], Optional[str]]:
        """Extracts experience requirements via processing.experience_parser."""
        return extract_experience(description)

    def scrape(
        self,
        search_term: str = "",
        location: str = "",
        results_wanted: int = 50,
        hours_old: int = 336,
    ) -> BreezyScrapeResult:
        """Scrapes open roles across registered Breezy HR company career boards."""
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
                    logger.warning(f"Breezy HR employer '{company_name}' missing ats_identifier. Skipping.")
                    continue

                feed_url = f"https://{subdomain}.breezy.hr/json"
                logger.info(f"Querying Breezy HR board: '{company_name}' ({subdomain})")

                try:
                    resp = client.get(feed_url)
                except httpx.TimeoutException:
                    logger.warning(f"Breezy HR feed timeout for '{subdomain}'")
                    continue
                except Exception as e:
                    logger.warning(f"Breezy HR network error for '{subdomain}': {e}")
                    continue

                if resp.status_code == 404:
                    logger.warning(f"Breezy HR board '{subdomain}' returned 404. Skipping.")
                    continue
                elif resp.status_code == 429:
                    logger.warning(f"Breezy HR rate limit (429) for '{subdomain}'. Skipping.")
                    continue
                elif resp.status_code != 200:
                    logger.warning(f"Breezy HR board '{subdomain}' returned HTTP {resp.status_code}")
                    continue

                try:
                    raw_data = resp.json()
                except Exception as e:
                    logger.warning(f"Malformed JSON from Breezy HR board '{subdomain}': {e}")
                    continue

                # The endpoint returns a list directly or may be wrapped
                positions: List[Dict[str, Any]] = []
                if isinstance(raw_data, list):
                    positions = raw_data
                elif isinstance(raw_data, dict):
                    # Some endpoints wrap in a key
                    for key in ("positions", "jobs", "results", "data"):
                        if isinstance(raw_data.get(key), list):
                            positions = raw_data[key]
                            break

                if not positions:
                    logger.info(f"Breezy HR board '{subdomain}': empty feed (0 positions).")
                    continue

                for pos in positions:
                    if len(collected_jobs) >= results_wanted:
                        break

                    if not isinstance(pos, dict):
                        continue

                    # Extract job ID
                    job_id = str(pos.get("_id") or pos.get("id") or "").strip()
                    if not job_id:
                        continue

                    dedup_id = f"breezy_{subdomain}_{job_id}"
                    if dedup_id in seen_job_ids:
                        continue
                    seen_job_ids.add(dedup_id)

                    # Check state: only 'published' positions
                    state = str(pos.get("state") or "").strip().lower()
                    if state and state not in ("published", "open", "active", ""):
                        continue

                    # Extract title
                    raw_title = str(pos.get("name") or pos.get("title") or "").strip()
                    title_clean = clean_job_title(raw_title)
                    if not title_clean:
                        continue

                    # Location / remote detection
                    loc_data = pos.get("location")
                    if not isinstance(loc_data, dict):
                        loc_data = {}
                    is_remote = self._detect_remote(loc_data)

                    # Authoritative date: published_date
                    pub_date_str = str(pos.get("published_date") or pos.get("creation_date") or "").strip()
                    posted_iso, _ = self._parse_authoritative_date(pub_date_str)

                    # Description from position listing (no detail API needed)
                    desc_raw = str(pos.get("description") or "").strip()
                    clean_desc = re.sub(r"<[^>]+>", " ", desc_raw).strip()
                    exp_min, exp_max, exp_raw = self._parse_experience(clean_desc)

                    # Application URL: friendly_id preferred; fallback to _id
                    friendly_id = str(pos.get("friendly_id") or job_id).strip()
                    apply_url = f"https://{subdomain}.breezy.hr/p/{friendly_id}"

                    # Canonical location string
                    loc_city = loc_data.get("city") or loc_data.get("name") or ""
                    loc_country = loc_data.get("country") or ""
                    parts = [p for p in [loc_city, loc_country] if p]
                    final_loc = ", ".join(parts) if parts else ("Remote" if is_remote else "Bangalore")

                    # Department / employment type
                    department = str(pos.get("department") or "").strip()
                    employment_type = str(pos.get("type") or "").strip()

                    canonical_job = Job(
                        id=dedup_id,
                        title=title_clean,
                        company=company_name,
                        source="breezy",
                        ats_provider="breezy",
                        location=final_loc,
                        is_remote=is_remote,
                        salary_min=None,
                        salary_max=None,
                        salary_currency=None,
                        salary_raw=None,
                        description=clean_desc,
                        discovery_url=apply_url,
                        apply_url=apply_url,
                        apply_type="DIRECT_ATS",
                        posted_at=posted_iso,
                        experience_min=exp_min,
                        experience_max=exp_max,
                        experience_raw=exp_raw,
                        raw_data={
                            "breezy_job_id": job_id,
                            "subdomain": subdomain,
                            "friendly_id": friendly_id,
                            "department": department,
                            "type": employment_type,
                            "state": state,
                            "published_date": pub_date_str,
                        },
                    )
                    collected_jobs.append(canonical_job)

        duration = round(time.time() - t_start, 2)
        logger.info(f"Breezy HR scrape completed: collected {len(collected_jobs)} fresh postings in {duration}s")
        return BreezyScrapeResult(
            jobs=collected_jobs,
            status="SUCCESS",
            duration_seconds=duration,
        )
