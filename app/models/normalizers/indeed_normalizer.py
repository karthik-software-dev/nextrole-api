import hashlib
import re
from typing import Any

from models.job import Job
from models.normalizers.experience_parser import extract_experience
from models.normalizers.salary_parser import parse_salary
from processing.deduplication import clean_job_title


def _extract_job_id(item: dict[str, Any], url: str | None) -> str:
    """Extract source ID with simple fallbacks."""
    # 1. Direct ID fields from Apify Indeed scraper
    raw_id = item.get("id") or item.get("jobKey") or item.get("jk")
    if raw_id:
        return str(raw_id).strip()

    # 2. Extract jk parameter from url if present
    if url:
        match = re.search(r"[?&]jk=([a-zA-Z0-9]+)", url)
        if match:
            return match.group(1)

    # 3. Deterministic hash fallback from company + title
    company = item.get("company") or ""
    title = item.get("positionName") or item.get("title") or ""
    key_str = f"{company.strip().lower()}::{title.strip().lower()}"
    return hashlib.md5(key_str.encode("utf-8")).hexdigest()[:16]


def normalize_indeed_job(item: dict[str, Any]) -> Job:
    """Normalizes a raw Indeed scraper dictionary into a canonical Job model."""
    title = clean_job_title((item.get("positionName") or item.get("title") or "Unknown Position").strip())
    company = (item.get("company") or "Unknown Company").strip()
    location = (item.get("location") or "").strip() or None
    discovery_url = item.get("url") or None
    apply_url = item.get("externalApplyLink") or item.get("url") or discovery_url

    job_id = _extract_job_id(item, discovery_url)

    # Detect remote indicator
    is_remote = False
    if location and "remote" in location.lower():
        is_remote = True
    elif "remote" in title.lower():
        is_remote = True
    elif item.get("isRemote") is True or item.get("remoteLocation") is True:
        is_remote = True

    # Normalize salary
    salary_raw = item.get("salary")
    if salary_raw and isinstance(salary_raw, str):
        salary_raw = salary_raw.strip()
    elif salary_raw and not isinstance(salary_raw, str):
        salary_raw = str(salary_raw)

    salary_min, salary_max, salary_currency = parse_salary(salary_raw)

    description = item.get("description") or item.get("descriptionText") or ""
    if isinstance(description, str):
        description = description.strip()

    min_exp, max_exp, raw_exp = extract_experience(f"{title} {description}")

    posted_at = item.get("postedAt") or item.get("postedAtParsed") or None
    if posted_at and not isinstance(posted_at, str):
        posted_at = str(posted_at)

    return Job(
        id=job_id,
        title=title,
        company=company,
        source="indeed",
        location=location,
        is_remote=is_remote,
        salary_raw=salary_raw,
        salary_min=salary_min,
        salary_max=salary_max,
        salary_currency=salary_currency,
        description=description,
        discovery_url=discovery_url,
        apply_url=apply_url,
        posted_at=posted_at,
        relevance_score=0.0,
        experience_min=min_exp,
        experience_max=max_exp,
        experience_raw=raw_exp,
        raw_data=item,
    )


def normalize_indeed_jobs(items: list[dict[str, Any]]) -> list[Job]:
    """Normalizes a list of raw Indeed scraper items into Job models."""
    return [normalize_indeed_job(item) for item in items if isinstance(item, dict)]
