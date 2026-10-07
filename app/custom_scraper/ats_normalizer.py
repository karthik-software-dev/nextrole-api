import hashlib
import html
import re
from typing import Any

from models.job import Job
from processing.experience_parser import extract_experience


def _strip_html(text: str) -> str:
    """Removes HTML tags and cleans up whitespace."""
    if not text:
        return ""
    clean = re.sub(r"<[^>]+>", " ", text)
    clean = html.unescape(clean)
    return re.sub(r"\s+", " ", clean).strip()


def normalize_smartrecruiters_job(item: dict[str, Any], company_name: str, company_identifier: str) -> Job:
    """Normalizes a SmartRecruiters API job record into a canonical Job model."""
    raw_id = str(item.get("id") or "").strip()
    title = (item.get("name") or "Unknown Position").strip()

    job_id = f"ats_{company_identifier.lower()}_{raw_id}" if raw_id else f"ats_{company_identifier.lower()}_{hashlib.md5(title.encode()).hexdigest()[:8]}"

    # Location
    loc_obj = item.get("location") or {}
    city = loc_obj.get("city")
    region = loc_obj.get("region")
    country = loc_obj.get("country")
    loc_parts = [p for p in [city, region, country] if p]
    location = ", ".join(loc_parts) if loc_parts else None

    is_remote = False
    if loc_obj.get("remote") is True:
        is_remote = True
    elif location and "remote" in location.lower():
        is_remote = True
    elif "remote" in title.lower():
        is_remote = True

    # Application URLs
    direct_apply_url = f"https://jobs.smartrecruiters.com/{company_identifier}/{raw_id}" if raw_id else None
    discovery_url = direct_apply_url

    # Description (Check for full jobAd sections or brief text)
    desc_parts = []
    job_ad = item.get("jobAd") or {}
    sections = job_ad.get("sections") or {}
    for sec_name in ("companyDescription", "jobDescription", "qualifications", "additionalInformation"):
        sec_val = sections.get(sec_name, {})
        if isinstance(sec_val, dict) and sec_val.get("text"):
            desc_parts.append(sec_val["text"])

    if not desc_parts and item.get("description"):
        desc_parts.append(str(item["description"]))

    raw_description = "\n\n".join(desc_parts) if desc_parts else title
    description = _strip_html(raw_description)

    min_exp, max_exp, raw_exp = extract_experience(f"{title} {description}")

    posted_at = item.get("releasedDate") or item.get("createdOn")

    return Job(
        id=job_id,
        title=title,
        company=company_name,
        source="ats",
        location=location,
        is_remote=is_remote,
        salary_raw=None,
        description=description,
        discovery_url=discovery_url,
        apply_url=direct_apply_url,
        ats_provider="SmartRecruiters",
        apply_type="DIRECT_ATS",
        posted_at=posted_at,
        relevance_score=0.0,
        experience_min=min_exp,
        experience_max=max_exp,
        experience_raw=raw_exp,
        raw_data=item,
    )


def normalize_greenhouse_job(item: dict[str, Any], company_name: str, board_token: str) -> Job:
    """Normalizes a Greenhouse API job record into a canonical Job model."""
    raw_id = str(item.get("id") or "").strip()
    title = (item.get("title") or "Unknown Position").strip()

    job_id = f"ats_{board_token.lower()}_{raw_id}" if raw_id else f"ats_{board_token.lower()}_{hashlib.md5(title.encode()).hexdigest()[:8]}"

    # Location
    loc_obj = item.get("location")
    if isinstance(loc_obj, dict):
        location = loc_obj.get("name")
    elif loc_obj:
        location = str(loc_obj).strip()
    else:
        location = None

    is_remote = False
    if location and "remote" in location.lower():
        is_remote = True
    elif "remote" in title.lower():
        is_remote = True

    direct_apply_url = item.get("absolute_url") or f"https://job-boards.greenhouse.io/{board_token}/jobs/{raw_id}"
    discovery_url = direct_apply_url

    raw_description = item.get("content") or ""
    description = _strip_html(raw_description) or title

    min_exp, max_exp, raw_exp = extract_experience(f"{title} {description}")

    posted_at = item.get("updated_at")

    return Job(
        id=job_id,
        title=title,
        company=company_name,
        source="ats",
        location=location,
        is_remote=is_remote,
        salary_raw=None,
        description=description,
        discovery_url=discovery_url,
        apply_url=direct_apply_url,
        ats_provider="Greenhouse",
        apply_type="DIRECT_ATS",
        posted_at=posted_at,
        relevance_score=0.0,
        experience_min=min_exp,
        experience_max=max_exp,
        experience_raw=raw_exp,
        raw_data=item,
    )


def normalize_lever_job(item: dict[str, Any], company_name: str, board_token: str) -> Job:
    """Normalizes a Lever API job posting into a canonical Job model.

    Lever posting structure:
      id, text (title), hostedUrl (apply link),
      categories.location, descriptionPlain / description,
      createdAt (Unix ms timestamp)
    """
    raw_id = str(item.get("id") or "").strip()
    title = (item.get("text") or "Unknown Position").strip()

    job_id = f"ats_lever_{board_token.lower()}_{raw_id}" if raw_id else f"ats_lever_{board_token.lower()}_{hashlib.md5(title.encode()).hexdigest()[:8]}"

    # Location lives inside categories
    categories = item.get("categories") or {}
    location = categories.get("location") or categories.get("team") or None

    is_remote = False
    if location and "remote" in location.lower():
        is_remote = True
    elif "remote" in title.lower():
        is_remote = True

    # Lever gives a hosted apply page URL
    direct_apply_url = item.get("hostedUrl") or item.get("applyUrl")
    discovery_url = direct_apply_url

    # Prefer plain text description over HTML
    raw_description = item.get("descriptionPlain") or item.get("description") or ""
    description = _strip_html(raw_description) or title

    min_exp, max_exp, raw_exp = extract_experience(f"{title} {description}")

    # Lever timestamps are Unix ms
    created_at_ms = item.get("createdAt")
    posted_at = None
    if created_at_ms:
        try:
            from datetime import datetime, timezone
            posted_at = datetime.fromtimestamp(int(created_at_ms) / 1000, tz=timezone.utc).isoformat()
        except Exception:
            posted_at = str(created_at_ms)

    return Job(
        id=job_id,
        title=title,
        company=company_name,
        source="ats",
        location=location,
        is_remote=is_remote,
        salary_raw=None,
        description=description,
        discovery_url=discovery_url,
        apply_url=direct_apply_url,
        ats_provider="Lever",
        apply_type="DIRECT_ATS",
        posted_at=posted_at,
        relevance_score=0.0,
        experience_min=min_exp,
        experience_max=max_exp,
        experience_raw=raw_exp,
        raw_data=item,
    )


def normalize_ashby_job(item: dict[str, Any], company_name: str, identifier: str) -> Job:
    """Normalizes an Ashby public REST API job record into a canonical Job model."""
    raw_id = str(item.get("id") or "").strip()
    title = (item.get("title") or "Unknown Position").strip()

    job_id = f"ats_ashby_{identifier.lower()}_{raw_id}" if raw_id else f"ats_ashby_{identifier.lower()}_{hashlib.md5(title.encode()).hexdigest()[:8]}"

    # Location & Secondary Locations
    primary_loc = item.get("location") or ""
    sec_locs = item.get("secondaryLocations") or []
    sec_loc_strs = [s.get("location") if isinstance(s, dict) else str(s) for s in sec_locs if s]
    all_locs = [primary_loc] + [s for s in sec_loc_strs if s and s != primary_loc]
    location = " / ".join(all_locs) if all_locs else None

    # Remote detection
    is_remote = False
    if item.get("isRemote") is True or str(item.get("workplaceType", "")).lower() == "remote":
        is_remote = True
    elif location and "remote" in location.lower():
        is_remote = True
    elif "remote" in title.lower():
        is_remote = True

    # Application URLs
    direct_apply_url = item.get("jobUrl") or item.get("applyUrl") or f"https://jobs.ashbyhq.com/{identifier}/{raw_id}"
    discovery_url = direct_apply_url

    # Description
    raw_description = item.get("descriptionPlain") or item.get("descriptionHtml") or ""
    description = _strip_html(raw_description) or title

    min_exp, max_exp, raw_exp = extract_experience(f"{title} {description}")
    published_at = item.get("publishedAt")

    return Job(
        id=job_id,
        title=title,
        company=company_name,
        source="ats",
        location=location,
        is_remote=is_remote,
        salary_raw=None,
        description=description,
        discovery_url=discovery_url,
        apply_url=direct_apply_url,
        ats_provider="Ashby",
        apply_type="DIRECT_ATS",
        posted_at=published_at,
        relevance_score=0.0,
        experience_min=min_exp,
        experience_max=max_exp,
        experience_raw=raw_exp,
        raw_data=item,
    )


def normalize_ats_job(item: dict[str, Any], company_name: str, ats_type: str, identifier: str) -> Job:
    """Dispatches normalization based on ATS provider type."""
    if ats_type == "smartrecruiters":
        return normalize_smartrecruiters_job(item, company_name, identifier)
    elif ats_type == "greenhouse":
        return normalize_greenhouse_job(item, company_name, identifier)
    elif ats_type == "lever":
        return normalize_lever_job(item, company_name, identifier)
    elif ats_type == "ashby":
        return normalize_ashby_job(item, company_name, identifier)
    else:
        # Generic fallback for Workday, BambooHR, Personio, Recruitee, Workable, Teamtailor, Breezy
        raw_id = str(item.get("id") or "").strip()
        title = str(item.get("title") or item.get("name") or "Unknown Position").strip()
        job_id = f"ats_{identifier.lower()}_{raw_id or hashlib.md5(title.encode()).hexdigest()[:8]}"
        apply_url = item.get("apply_url") or item.get("url") or item.get("canonical_apply_url") or item.get("discovery_url")
        ats_provider_map = {
            "workday": "Workday",
            "ashby": "Ashby",
            "bamboohr": "BambooHR",
            "personio": "Personio",
            "recruitee": "Recruitee",
            "workable": "Workable",
            "teamtailor": "Teamtailor",
            "breezy": "Breezy HR",
        }
        prov = ats_provider_map.get(ats_type.lower(), "Company Careers")
        return Job(
            id=job_id,
            title=title,
            company=company_name,
            source="ats",
            location=str(item.get("location") or ""),
            is_remote=bool(item.get("is_remote")),
            salary_raw=item.get("salary_raw"),
            description=_strip_html(str(item.get("description") or "")),
            discovery_url=apply_url,
            apply_url=apply_url,
            ats_provider=prov,
            apply_type="DIRECT_ATS",
            posted_at=item.get("posted_at"),
            relevance_score=0.0,
            raw_data=item,
        )


def normalize_ats_jobs(records: list[tuple[dict[str, Any], str, str, str]]) -> list[Job]:
    """Normalizes a list of (raw_item, company_name, ats_type, identifier) tuples."""
    return [normalize_ats_job(item, comp, ats, ident) for item, comp, ats, ident in records]
