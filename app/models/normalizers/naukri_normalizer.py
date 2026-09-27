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


def normalize_naukri_job(item: dict[str, Any]) -> Job:
    """Normalizes a raw Naukri scraper dictionary into a canonical Job model."""
    jd = item.get("jobDetails") or item

    # 1. Identifier
    raw_job_id = jd.get("jobId")
    if raw_job_id:
        job_id = f"naukri_{raw_job_id}"
    else:
        # Fallback hash
        key_str = f"{jd.get('companyDetail', {}).get('name', '')}::{jd.get('title', '')}"
        job_id = f"naukri_{hashlib.md5(key_str.encode('utf-8')).hexdigest()[:12]}"

    # 2. Title & Company
    title = clean_job_title((jd.get("title") or "Unknown Position").strip())
    company_detail = jd.get("companyDetail")
    if isinstance(company_detail, dict) and company_detail.get("name"):
        company = company_detail["name"].strip()
    else:
        company = (jd.get("staticCompanyName") or "Unknown Company").strip()

    # 3. Location & Remote
    locations_list = jd.get("locations", [])
    if isinstance(locations_list, list) and locations_list:
        loc_labels = [
            loc.get("label", "").strip()
            for loc in locations_list
            if isinstance(loc, dict) and loc.get("label")
        ]
        location = ", ".join(loc_labels) if loc_labels else None
    else:
        location = str(jd.get("location")).strip() if jd.get("location") else None

    is_remote = False
    if location and "remote" in location.lower():
        is_remote = True
    elif "remote" in title.lower():
        is_remote = True
    elif jd.get("wfhType"):
        is_remote = True

    # 4. Salary
    salary_detail = jd.get("salaryDetail")
    salary_raw = None
    if isinstance(salary_detail, dict):
        sal_text = salary_detail.get("salaryText") or salary_detail.get("label")
        if sal_text and sal_text.lower() != "not disclosed":
            salary_raw = sal_text.strip()
    elif isinstance(salary_detail, str) and salary_detail.lower() != "not disclosed":
        salary_raw = salary_detail.strip()

    salary_min, salary_max, salary_currency = parse_salary(salary_raw)

    # 5. Description
    raw_desc = jd.get("description") or jd.get("shortDescription") or ""
    description = _strip_html(raw_desc)

    # 6. Experience
    min_exp = jd.get("minimumExperience")
    max_exp = jd.get("maximumExperience")
    raw_exp = jd.get("experienceText")

    if min_exp is not None:
        try:
            min_exp = int(min_exp)
        except (ValueError, TypeError):
            min_exp = None

    if max_exp is not None:
        try:
            max_exp = int(max_exp)
        except (ValueError, TypeError):
            max_exp = None

    if min_exp is None and max_exp is None:
        min_exp, max_exp, parsed_raw = extract_experience(f"{title} {description}")
        if not raw_exp:
            raw_exp = parsed_raw

    # 7. URLs (Discovery vs Apply)
    discovery_url = jd.get("staticUrl") or None
    apply_url = jd.get("applyRedirectUrl") or jd.get("staticUrl") or discovery_url

    # 8. Posted At
    posted_at = jd.get("createdDate")
    if posted_at and not isinstance(posted_at, str):
        posted_at = str(posted_at)

    return Job(
        id=job_id,
        title=title,
        company=company,
        source="naukri",
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


def normalize_naukri_jobs(items: list[dict[str, Any]]) -> list[Job]:
    """Normalizes a list of raw Naukri scraper items into Job models."""
    return [normalize_naukri_job(item) for item in items if isinstance(item, dict)]
