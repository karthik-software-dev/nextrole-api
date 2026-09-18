import hashlib
import html
import re
from typing import Any

from models.job import Job
from models.normalizers.experience_parser import extract_experience


def _strip_html(text: str) -> str:
    """Removes HTML tags and cleans up whitespace."""
    if not text:
        return ""
    clean = re.sub(r"<[^>]+>", " ", text)
    clean = html.unescape(clean)
    return re.sub(r"\s+", " ", clean).strip()


def normalize_google_job(item: dict[str, Any]) -> Job:
    """Normalizes a raw Google Jobs scraper dictionary into a canonical Job model."""
    title = (item.get("job_title") or "Unknown Position").strip()
    company = (item.get("company_name") or "Unknown Company").strip()
    apply_link = (item.get("apply_link") or "").strip() or None

    # 1. Identifier
    key_str = f"{company}::{title}::{apply_link or ''}"
    job_id = f"google_{hashlib.md5(key_str.encode('utf-8')).hexdigest()[:12]}"

    # 2. Location & Remote
    location = str(item.get("location")).strip() if item.get("location") else None
    is_remote = False
    if location and "remote" in location.lower():
        is_remote = True
    elif "remote" in title.lower():
        is_remote = True

    # 3. Description (Combine description, qualifications, responsibilities)
    desc_parts = []
    if item.get("job_description"):
        desc_parts.append(str(item["job_description"]).strip())
    if item.get("qualifications"):
        desc_parts.append(f"Qualifications:\n{str(item['qualifications']).strip()}")
    if item.get("responsibilities"):
        desc_parts.append(f"Responsibilities:\n{str(item['responsibilities']).strip()}")

    combined_desc = "\n\n".join(desc_parts)
    description = _strip_html(combined_desc)

    min_exp, max_exp, raw_exp = extract_experience(f"{title} {description}")

    # 4. URLs
    discovery_url = apply_link
    apply_url = apply_link

    return Job(
        id=job_id,
        title=title,
        company=company,
        source="google_jobs",
        location=location,
        is_remote=is_remote,
        salary_raw=None,
        description=description,
        discovery_url=discovery_url,
        apply_url=apply_url,
        posted_at=None,
        relevance_score=0.0,
        experience_min=min_exp,
        experience_max=max_exp,
        experience_raw=raw_exp,
        raw_data=item,
    )


def normalize_google_jobs(items: list[dict[str, Any]]) -> list[Job]:
    """Normalizes a list of raw Google Jobs scraper items into Job models."""
    return [normalize_google_job(item) for item in items if isinstance(item, dict)]
