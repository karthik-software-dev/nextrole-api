import json
import logging
import re
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from config.target_companies import TargetCompany, get_enabled_target_companies
from models.job import Job
from models.normalizers.ats_normalizer import normalize_ats_job

logger = logging.getLogger(__name__)

CACHE_DIR = Path(__file__).resolve().parent.parent / "data"
DEFAULT_CACHE_FILE = CACHE_DIR / "ats_raw_cache.json"
HTTP_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


INDIA_LOCATION_KEYWORDS = {
    "india", "in", "bengaluru", "bangalore", "hyderabad", "pune", "mumbai",
    "gurgaon", "gurugram", "delhi", "noida", "chennai", "kolkata", "ahmedabad", "remote"
}


def is_location_match(item_loc: Any, target_filter: str | None) -> bool:
    """Checks if a job posting's location matches the configured location filter."""
    if not target_filter:
        return True

    loc_str = ""
    if isinstance(item_loc, dict):
        parts = [
            item_loc.get("name"),
            item_loc.get("city"),
            item_loc.get("region"),
            item_loc.get("country"),
            item_loc.get("fullLocation"),
        ]
        loc_str = " ".join(str(p) for p in parts if p).lower()
    else:
        loc_str = str(item_loc or "").lower()

    filter_lower = target_filter.lower()
    if filter_lower in loc_str:
        return True

    if filter_lower in ("in", "india"):
        tokens = set(re.findall(r"\b[a-zA-Z]+\b", loc_str))
        if tokens & INDIA_LOCATION_KEYWORDS:
            return True

    return False


from concurrent.futures import ThreadPoolExecutor, as_completed


def _fetch_single_smartrecruiters_detail(company_identifier: str, item: dict[str, Any]) -> dict[str, Any]:
    """Fetches full posting detail including jobAd sections for a single SmartRecruiters job."""
    job_id = item.get("id")
    if not job_id:
        return item
    url = f"https://api.smartrecruiters.com/v1/companies/{company_identifier}/postings/{job_id}"
    req = urllib.request.Request(url, headers=HTTP_HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            detail = json.loads(resp.read().decode("utf-8"))
            # Preserve top-level list metadata if missing in detail
            for k, v in item.items():
                if k not in detail:
                    detail[k] = v
            return detail
    except Exception as e:
        logger.debug("Failed to fetch posting detail for %s: %s", job_id, e)
        return item


def fetch_smartrecruiters_postings(company: TargetCompany) -> list[dict[str, Any]]:
    """Fetches job postings and full descriptions from SmartRecruiters public REST API."""
    url = f"https://api.smartrecruiters.com/v1/companies/{company.identifier}/postings?limit=100"
    req = urllib.request.Request(url, headers=HTTP_HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            raw_items = data.get("content", [])
            print(f"[ATS: SmartRecruiters] Fetched {len(raw_items)} postings for {company.name}")
    except Exception as e:
        print(f"[WARN] Failed to fetch SmartRecruiters postings for {company.name}: {e}")
        return []

    # Pre-filter by location before fetching full jobAd details to minimize network calls
    candidate_items = [
        item for item in raw_items
        if is_location_match(item.get("location"), company.location_filter)
    ]

    if not candidate_items:
        return []

    # Hydrate full descriptions in parallel
    hydrated_items: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=8) as executor:
        future_map = {
            executor.submit(_fetch_single_smartrecruiters_detail, company.identifier, it): it
            for it in candidate_items
        }
        for future in as_completed(future_map):
            try:
                hydrated_items.append(future.result())
            except Exception:
                hydrated_items.append(future_map[future])

    return hydrated_items


def fetch_greenhouse_postings(company: TargetCompany) -> list[dict[str, Any]]:
    """Fetches job postings from Greenhouse public REST API."""
    url = f"https://boards-api.greenhouse.io/v1/boards/{company.identifier}/jobs?content=true"
    req = urllib.request.Request(url, headers=HTTP_HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            items = data.get("jobs", [])
            print(f"[ATS: Greenhouse] Fetched {len(items)} postings for {company.name}")
            return items
    except Exception as e:
        print(f"[WARN] Failed to fetch Greenhouse postings for {company.name}: {e}")
        return []


def fetch_target_company_jobs(
    use_cache: bool = False,
    cache_file: Path | None = None,
    companies: list[TargetCompany] | None = None
) -> list[Job]:
    """Discovers live job postings directly from target companies' official career/ATS portals.

    Returns normalized Job objects.
    """
    target_cache = cache_file or DEFAULT_CACHE_FILE
    target_list = companies or get_enabled_target_companies()

    # 1. Check local cache first
    if use_cache and target_cache.exists():
        try:
            with open(target_cache, "r", encoding="utf-8") as f:
                cached_payload = json.load(f)
            jobs: list[Job] = []
            for record in cached_payload:
                raw_item = record.get("raw_item", {})
                comp_name = record.get("company_name", "Unknown")
                ats_type = record.get("ats_type", "generic")
                ident = record.get("identifier", "unknown")
                jobs.append(normalize_ats_job(raw_item, comp_name, ats_type, ident))
            print(f"[CACHE] Loaded {len(jobs)} target career jobs from {target_cache.name}")
            return jobs
        except Exception as e:
            print(f"[WARN] Failed to read ATS cache ({e}), falling back to live fetch...")

    # 2. Live fetch from official ATS REST APIs
    print(f"[ATS] Querying official career portals for {len(target_list)} enabled companies...")
    collected_records: list[dict[str, Any]] = []
    jobs: list[Job] = []

    for comp in target_list:
        if comp.ats_type == "smartrecruiters":
            raw_items = fetch_smartrecruiters_postings(comp)
        elif comp.ats_type == "greenhouse":
            raw_items = fetch_greenhouse_postings(comp)
        else:
            print(f"[WARN] Unsupported ATS type: {comp.ats_type} for {comp.name}")
            continue

        matched_for_comp = 0
        for item in raw_items:
            loc_val = item.get("location")
            if not is_location_match(loc_val, comp.location_filter):
                continue

            matched_for_comp += 1
            collected_records.append({
                "company_name": comp.name,
                "ats_type": comp.ats_type,
                "identifier": comp.identifier,
                "raw_item": item,
            })
            jobs.append(normalize_ats_job(item, comp.name, comp.ats_type, comp.identifier))

        print(f"  -> {comp.name}: {matched_for_comp} postings matched location ({comp.location_filter or 'All'})")

    # 3. Save raw items to local cache
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        with open(target_cache, "w", encoding="utf-8") as f:
            json.dump(collected_records, f, indent=2, ensure_ascii=False)
        print(f"[CACHE] Saved {len(collected_records)} target career records to {target_cache.name}")
    except Exception as e:
        print(f"[WARN] Could not save ATS cache to {target_cache}: {e}")

    return jobs
