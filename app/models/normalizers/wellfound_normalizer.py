import hashlib
import html
import re
from typing import Any

from models.job import Job
from models.normalizers.experience_parser import extract_experience
from models.normalizers.salary_parser import parse_salary
from processing.deduplication import clean_job_title


def _strip_html(text: str) -> str:
    """Removes HTML tags, markdown artifacts, and cleans up whitespace."""
    if not text:
        return ""
    clean = re.sub(r"<[^>]+>", " ", text)
    clean = html.unescape(clean)
    return re.sub(r"\s+", " ", clean).strip()


def normalize_wellfound_job(item: dict[str, Any]) -> Job:
    """Normalizes a raw Wellfound scraper dictionary into a canonical Job model."""
    # 1. Identifier
    raw_job_id = item.get("jobId")
    if raw_job_id:
        job_id = f"wellfound_{raw_job_id}"
    else:
        key_str = f"{item.get('companyName', '')}::{item.get('title', '')}"
        job_id = f"wellfound_{hashlib.md5(key_str.encode('utf-8')).hexdigest()[:12]}"

    # 2. Title & Company
    title = clean_job_title((item.get("title") or "Unknown Position").strip())
    company = (item.get("companyName") or "Unknown Company").strip()

    # 3. Location & Remote
    locations_val = item.get("locations")
    if isinstance(locations_val, list):
        location = ", ".join(str(l).strip() for l in locations_val if str(l).strip()) or None
    elif locations_val:
        location = str(locations_val).strip()
    else:
        location = None

    is_remote = bool(item.get("remote"))
    if not is_remote and location and "remote" in location.lower():
        is_remote = True
    if not is_remote and "remote" in title.lower():
        is_remote = True

    # 4. Salary & Compensation
    salary_raw = None
    comp = item.get("compensation")
    if comp and str(comp).strip():
        salary_raw = str(comp).strip()

    salary_min, salary_max, salary_currency = parse_salary(salary_raw)

    # 5. Description
    raw_desc = item.get("description") or ""
    description = _strip_html(raw_desc)

    min_exp, max_exp, raw_exp = extract_experience(f"{title} {description}")

    # 6. URLs (Discovery vs Apply)
    discovery_url = item.get("jobUrl") or None
    apply_url = item.get("applyUrl") or item.get("jobUrl") or discovery_url

    # 7. Posted At
    posted_at = item.get("postedAt")
    if posted_at and not isinstance(posted_at, str):
        posted_at = str(posted_at)

    return Job(
        id=job_id,
        title=title,
        company=company,
        source="wellfound",
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


def normalize_wellfound_jobs(items: list[dict[str, Any]]) -> list[Job]:
    """Normalizes a list of raw Wellfound scraper items into Job models."""
    return [normalize_wellfound_job(item) for item in items if isinstance(item, dict)]
