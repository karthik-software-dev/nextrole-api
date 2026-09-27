import hashlib
import html
import re
from typing import Any

from models.job import Job
from models.normalizers.experience_parser import extract_experience
from models.normalizers.salary_parser import parse_salary
from processing.deduplication import clean_job_title


def _strip_html(text: str) -> str:
    """Removes HTML tags and cleans up whitespace and entities."""
    if not text:
        return ""
    clean = re.sub(r"<[^>]+>", " ", text)
    clean = html.unescape(clean)
    return re.sub(r"\s+", " ", clean).strip()


def normalize_linkedin_job(item: dict[str, Any]) -> Job:
    """Normalizes a raw Fast-LinkedIn-job-Scraper dictionary into a canonical Job model."""
    # 1. Identifier
    raw_job_id = item.get("jobId")
    if raw_job_id:
        job_id = f"linkedin_{raw_job_id}"
    else:
        key_str = f"{item.get('company', '')}::{item.get('title', '')}"
        job_id = f"linkedin_{hashlib.md5(key_str.encode('utf-8')).hexdigest()[:12]}"

    # 2. Title & Company
    title = clean_job_title((item.get("title") or "Unknown Position").strip())
    company = (item.get("company") or "Unknown Company").strip()

    # 3. Location & Remote
    location = str(item.get("location")).strip() if item.get("location") else None
    work_type = str(item.get("workType") or "").lower()

    is_remote = False
    if location and "remote" in location.lower():
        is_remote = True
    elif "remote" in title.lower():
        is_remote = True
    elif "remote" in work_type:
        is_remote = True

    # 4. Salary
    salary_raw = None
    salary_val = item.get("salary")
    if salary_val and str(salary_val).strip():
        salary_raw = str(salary_val).strip()

    salary_min, salary_max, salary_currency = parse_salary(salary_raw)

    # 5. Description
    raw_desc = item.get("descriptionText") or item.get("descriptionHtml") or ""
    description = _strip_html(raw_desc)

    min_exp, max_exp, raw_exp = extract_experience(f"{title} {description}")

    # 6. URLs (Discovery vs Apply)
    if raw_job_id:
        discovery_url = f"https://www.linkedin.com/jobs/view/{raw_job_id}"
    else:
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
        source="linkedin",
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


def normalize_linkedin_jobs(items: list[dict[str, Any]]) -> list[Job]:
    """Normalizes a list of raw LinkedIn scraper items into Job models."""
    return [normalize_linkedin_job(item) for item in items if isinstance(item, dict)]
