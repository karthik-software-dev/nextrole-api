import json
import logging
import re
import urllib.parse
import urllib.request
from dataclasses import asdict
from pathlib import Path
from typing import Any

from config.target_companies import TargetCompany, get_enabled_target_companies
from models.job import Job
from custom_scraper.ats_normalizer import normalize_ats_job

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


def is_non_technical_title(title: str | None) -> bool:
    """Pre-filters obvious non-engineering ATS roles to save bandwidth and memory."""
    if not title:
        return False
    t_lower = title.lower()
    from processing.relevance import HARD_EXCLUDE_TITLE_KEYWORDS, _has_keyword
    return any(_has_keyword(kw, t_lower) for kw in HARD_EXCLUDE_TITLE_KEYWORDS)


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


def fetch_lever_postings(company: TargetCompany) -> list[dict[str, Any]]:
    """Fetches job postings from Lever public REST API (zero cost, no auth required).

    Lever API: GET https://api.lever.co/v0/postings/<identifier>?mode=json
    Returns a flat list of posting objects.
    """
    url = f"https://api.lever.co/v0/postings/{company.identifier}?mode=json&limit=100"
    req = urllib.request.Request(url, headers=HTTP_HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            items = json.loads(resp.read().decode("utf-8"))
            # Lever returns a list directly (not wrapped in a key)
            if not isinstance(items, list):
                items = items.get("data", [])
            print(f"[ATS: Lever] Fetched {len(items)} postings for {company.name}")
            return items
    except Exception as e:
        print(f"[WARN] Failed to fetch Lever postings for {company.name}: {e}")
        return []


def fetch_ashby_postings(company: TargetCompany) -> list[dict[str, Any]]:
    """Fetches job postings from Ashby public REST API."""
    url = f"https://api.ashbyhq.com/posting-api/job-board/{company.identifier}"
    req = urllib.request.Request(url, headers=HTTP_HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            items = data.get("jobs", [])
            print(f"[ATS: Ashby] Fetched {len(items)} postings for {company.name}")
            return items
    except Exception as e:
        print(f"[WARN] Failed to fetch Ashby postings for {company.name}: {e}")
        return []


def _fetch_single_target_company(comp: TargetCompany) -> tuple[list[dict[str, Any]], list[Job]]:
    """Fetches and normalizes matching job postings for a single target company."""
    records: list[dict[str, Any]] = []
    comp_jobs: list[Job] = []
    try:
        if comp.ats_type == "smartrecruiters":
            raw_items = fetch_smartrecruiters_postings(comp)
        elif comp.ats_type == "greenhouse":
            raw_items = fetch_greenhouse_postings(comp)
        elif comp.ats_type == "lever":
            raw_items = fetch_lever_postings(comp)
        elif comp.ats_type == "ashby":
            raw_items = fetch_ashby_postings(comp)
        else:
            logger.debug(f"[WARN] Unsupported ATS type: {comp.ats_type} for {comp.name}")
            return [], []

        for item in raw_items:
            if comp.ats_type == "lever":
                categories = item.get("categories") or {}
                all_locs = categories.get("allLocations") or []
                all_locs_str = " ".join(all_locs) if isinstance(all_locs, list) else str(all_locs)
                loc_val = {
                    "name": categories.get("location"),
                    "country": item.get("country"),
                    "region": categories.get("team"),
                    "fullLocation": f"{all_locs_str} {categories.get('location', '')} {item.get('country', '')}"
                }
            elif comp.ats_type == "ashby":
                sec_locs = item.get("secondaryLocations") or []
                sec_strs = [s.get("location") if isinstance(s, dict) else str(s) for s in sec_locs if s]
                loc_val = {
                    "name": item.get("location"),
                    "fullLocation": f"{item.get('location', '')} {' '.join(sec_strs)} {'Remote' if item.get('isRemote') else ''}",
                }
            else:
                loc_val = item.get("location")

            if not is_location_match(loc_val, comp.location_filter):
                continue

            item_title = str(item.get("title") or item.get("name") or item.get("text") or "")
            if is_non_technical_title(item_title):
                continue

            records.append({
                "company_name": comp.name,
                "ats_type": comp.ats_type,
                "identifier": comp.identifier,
                "raw_item": item,
            })
            comp_jobs.append(normalize_ats_job(item, comp.name, comp.ats_type, comp.identifier))
    except Exception as e:
        logger.warning(f"Error fetching postings for {comp.name}: {e}")

    return records, comp_jobs


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

    # 2. Parallel live fetch from official ATS REST APIs
    print(f"[ATS] Querying official career portals for {len(target_list)} enabled companies in parallel...")
    collected_records: list[dict[str, Any]] = []
    jobs: list[Job] = []

    max_workers = min(15, len(target_list)) if target_list else 1
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_comp = {executor.submit(_fetch_single_target_company, comp): comp for comp in target_list}
        for future in as_completed(future_to_comp):
            comp = future_to_comp[future]
            try:
                rec_list, comp_jobs = future.result()
                collected_records.extend(rec_list)
                jobs.extend(comp_jobs)
                if comp_jobs:
                    print(f"  -> {comp.name}: {len(comp_jobs)} postings matched location ({comp.location_filter or 'All'})")
            except Exception as e:
                logger.warning(f"Failed processing {comp.name}: {e}")

    # 3. Save raw items to local cache
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        with open(target_cache, "w", encoding="utf-8") as f:
            json.dump(collected_records, f, indent=2, ensure_ascii=False)
        print(f"[CACHE] Saved {len(collected_records)} target career records to {target_cache.name}")
    except Exception as e:
        print(f"[WARN] Could not save ATS cache to {target_cache}: {e}")

    return jobs


def fetch_smartrecruiters_jobs(use_cache: bool = False, cache_file: Path | None = None) -> list[Job]:
    """Fetches jobs from SmartRecruiters ATS."""
    target_cache = cache_file or (CACHE_DIR / "smartrecruiters_raw_cache.json")
    if use_cache and target_cache.exists():
        try:
            with open(target_cache, "r", encoding="utf-8") as f:
                items = json.load(f)
            return [Job(**it) for it in items]
        except Exception:
            pass

    comps = [c for c in get_enabled_target_companies() if c.ats_type == "smartrecruiters"]
    jobs = []
    for comp in comps:
        raw_items = fetch_smartrecruiters_postings(comp)
        for it in raw_items:
            if is_non_technical_title(it.get("name")):
                continue
            if is_location_match(it.get("location"), comp.location_filter):
                j = normalize_ats_job(it, comp.name, comp.ats_type, comp.identifier)
                jobs.append(j)

    if jobs:
        try:
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            with open(target_cache, "w", encoding="utf-8") as f:
                json.dump([asdict(j) for j in jobs], f, indent=2, ensure_ascii=False)
        except Exception:
            pass
    return jobs


def fetch_greenhouse_jobs(use_cache: bool = False, cache_file: Path | None = None) -> list[Job]:
    """Fetches jobs from Greenhouse ATS."""
    target_cache = cache_file or (CACHE_DIR / "greenhouse_raw_cache.json")
    if use_cache and target_cache.exists():
        try:
            with open(target_cache, "r", encoding="utf-8") as f:
                items = json.load(f)
            return [Job(**it) for it in items]
        except Exception:
            pass

    comps = [c for c in get_enabled_target_companies() if c.ats_type == "greenhouse"]
    jobs = []
    for comp in comps:
        raw_items = fetch_greenhouse_postings(comp)
        for it in raw_items:
            if is_non_technical_title(it.get("title")):
                continue
            loc = it.get("location", {})
            loc_val = loc.get("name") if isinstance(loc, dict) else str(loc)
            if is_location_match(loc_val, comp.location_filter):
                j = normalize_ats_job(it, comp.name, comp.ats_type, comp.identifier)
                jobs.append(j)

    if jobs:
        try:
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            with open(target_cache, "w", encoding="utf-8") as f:
                json.dump([asdict(j) for j in jobs], f, indent=2, ensure_ascii=False)
        except Exception:
            pass
    return jobs


def fetch_lever_jobs(use_cache: bool = False, cache_file: Path | None = None) -> list[Job]:
    """Fetches jobs from Lever ATS."""
    target_cache = cache_file or (CACHE_DIR / "lever_raw_cache.json")
    if use_cache and target_cache.exists():
        try:
            with open(target_cache, "r", encoding="utf-8") as f:
                items = json.load(f)
            return [Job(**it) for it in items]
        except Exception:
            pass

    comps = [c for c in get_enabled_target_companies() if c.ats_type == "lever"]
    jobs = []
    for comp in comps:
        raw_items = fetch_lever_postings(comp)
        for it in raw_items:
            if is_non_technical_title(it.get("text")):
                continue
            categories = it.get("categories") or {}
            all_locs = categories.get("allLocations") or []
            all_locs_str = " ".join(all_locs) if isinstance(all_locs, list) else str(all_locs)
            loc_val = {
                "name": categories.get("location"),
                "country": it.get("country"),
                "region": categories.get("team"),
                "fullLocation": f"{all_locs_str} {categories.get('location', '')} {it.get('country', '')}"
            }
            if is_location_match(loc_val, comp.location_filter):
                j = normalize_ats_job(it, comp.name, comp.ats_type, comp.identifier)
                jobs.append(j)

    if jobs:
        try:
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            with open(target_cache, "w", encoding="utf-8") as f:
                json.dump([asdict(j) for j in jobs], f, indent=2, ensure_ascii=False)
        except Exception:
            pass
    return jobs


def fetch_workday_jobs(use_cache: bool = False, cache_file: Path | None = None) -> list[Job]:
    """Fetches jobs from Workday ATS."""
    target_cache = cache_file or (CACHE_DIR / "workday_raw_cache.json")
    if use_cache and target_cache.exists():
        try:
            with open(target_cache, "r", encoding="utf-8") as f:
                items = json.load(f)
            return [Job(**it) for it in items]
        except Exception:
            pass

    from custom_scraper.workday_scraper import WorkdayScraper
    scraper = WorkdayScraper()
    res = scraper.scrape("Python", "Bangalore", results_wanted=15)
    jobs = []
    for j in res.jobs:
        j.source = "ats"
        j.ats_provider = "Workday"
        jobs.append(j)

    if jobs:
        try:
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            with open(target_cache, "w", encoding="utf-8") as f:
                json.dump([asdict(j) for j in jobs], f, indent=2, ensure_ascii=False)
        except Exception:
            pass
    return jobs


def fetch_ashby_jobs(use_cache: bool = False, cache_file: Path | None = None) -> list[Job]:
    """Fetches jobs from Ashby ATS."""
    target_cache = cache_file or (CACHE_DIR / "ashby_raw_cache.json")
    if use_cache and target_cache.exists():
        try:
            with open(target_cache, "r", encoding="utf-8") as f:
                items = json.load(f)
            return [Job(**it) for it in items]
        except Exception:
            pass

    from custom_scraper.ashby_scraper import AshbyScraper
    scraper = AshbyScraper()
    res = scraper.scrape("Python", "Bangalore", results_wanted=15)
    jobs = []
    for j in res.jobs:
        j.source = "ats"
        j.ats_provider = "Ashby"
        jobs.append(j)

    if jobs:
        try:
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            with open(target_cache, "w", encoding="utf-8") as f:
                json.dump([asdict(j) for j in jobs], f, indent=2, ensure_ascii=False)
        except Exception:
            pass
    return jobs


def fetch_bamboohr_jobs(use_cache: bool = False, cache_file: Path | None = None) -> list[Job]:
    """Fetches jobs from BambooHR ATS."""
    target_cache = cache_file or (CACHE_DIR / "bamboohr_raw_cache.json")
    if use_cache and target_cache.exists():
        try:
            with open(target_cache, "r", encoding="utf-8") as f:
                items = json.load(f)
            return [Job(**it) for it in items]
        except Exception:
            pass

    from custom_scraper.bamboohr_scraper import BambooHRScraper
    scraper = BambooHRScraper()
    res = scraper.scrape("Python", "Bangalore", results_wanted=15)
    jobs = []
    for j in res.jobs:
        j.source = "ats"
        j.ats_provider = "BambooHR"
        jobs.append(j)

    if jobs:
        try:
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            with open(target_cache, "w", encoding="utf-8") as f:
                json.dump([asdict(j) for j in jobs], f, indent=2, ensure_ascii=False)
        except Exception:
            pass
    return jobs


def fetch_personio_jobs(use_cache: bool = False, cache_file: Path | None = None) -> list[Job]:
    """Fetches jobs from Personio ATS."""
    target_cache = cache_file or (CACHE_DIR / "personio_raw_cache.json")
    if use_cache and target_cache.exists():
        try:
            with open(target_cache, "r", encoding="utf-8") as f:
                items = json.load(f)
            return [Job(**it) for it in items]
        except Exception:
            pass

    from custom_scraper.personio_scraper import PersonioScraper
    scraper = PersonioScraper()
    res = scraper.scrape("Python", "Bangalore", results_wanted=15)
    jobs = []
    for j in res.jobs:
        j.source = "ats"
        j.ats_provider = "Personio"
        jobs.append(j)

    if jobs:
        try:
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            with open(target_cache, "w", encoding="utf-8") as f:
                json.dump([asdict(j) for j in jobs], f, indent=2, ensure_ascii=False)
        except Exception:
            pass
    return jobs


def fetch_recruitee_jobs(use_cache: bool = False, cache_file: Path | None = None) -> list[Job]:
    """Fetches jobs from Recruitee ATS."""
    target_cache = cache_file or (CACHE_DIR / "recruitee_raw_cache.json")
    if use_cache and target_cache.exists():
        try:
            with open(target_cache, "r", encoding="utf-8") as f:
                items = json.load(f)
            return [Job(**it) for it in items]
        except Exception:
            pass

    from custom_scraper.recruitee_scraper import RecruiteeScraper
    scraper = RecruiteeScraper()
    res = scraper.scrape("Python", "Bangalore", results_wanted=15)
    jobs = []
    for j in res.jobs:
        j.source = "ats"
        j.ats_provider = "Recruitee"
        jobs.append(j)

    if jobs:
        try:
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            with open(target_cache, "w", encoding="utf-8") as f:
                json.dump([asdict(j) for j in jobs], f, indent=2, ensure_ascii=False)
        except Exception:
            pass
    return jobs


def fetch_workable_jobs(use_cache: bool = False, cache_file: Path | None = None) -> list[Job]:
    """Fetches jobs from Workable ATS."""
    target_cache = cache_file or (CACHE_DIR / "workable_raw_cache.json")
    if use_cache and target_cache.exists():
        try:
            with open(target_cache, "r", encoding="utf-8") as f:
                items = json.load(f)
            return [Job(**it) for it in items]
        except Exception:
            pass

    from custom_scraper.workable_scraper import WorkableScraper
    scraper = WorkableScraper()
    res = scraper.scrape("Python", "Bangalore", results_wanted=15)
    jobs = []
    for j in res.jobs:
        j.source = "ats"
        j.ats_provider = "Workable"
        jobs.append(j)

    if jobs:
        try:
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            with open(target_cache, "w", encoding="utf-8") as f:
                json.dump([asdict(j) for j in jobs], f, indent=2, ensure_ascii=False)
        except Exception:
            pass
    return jobs


def fetch_teamtailor_jobs(use_cache: bool = False, cache_file: Path | None = None) -> list[Job]:
    """Fetches jobs from Teamtailor ATS."""
    target_cache = cache_file or (CACHE_DIR / "teamtailor_raw_cache.json")
    if use_cache and target_cache.exists():
        try:
            with open(target_cache, "r", encoding="utf-8") as f:
                items = json.load(f)
            return [Job(**it) for it in items]
        except Exception:
            pass

    from custom_scraper.teamtailor_scraper import TeamtailorScraper
    scraper = TeamtailorScraper()
    res = scraper.scrape("Python", "Bangalore", results_wanted=15)
    jobs = []
    for j in res.jobs:
        j.source = "ats"
        j.ats_provider = "Teamtailor"
        jobs.append(j)

    if jobs:
        try:
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            with open(target_cache, "w", encoding="utf-8") as f:
                json.dump([asdict(j) for j in jobs], f, indent=2, ensure_ascii=False)
        except Exception:
            pass
    return jobs


def fetch_breezy_jobs(use_cache: bool = False, cache_file: Path | None = None) -> list[Job]:
    """Fetches jobs from Breezy HR ATS."""
    target_cache = cache_file or (CACHE_DIR / "breezy_raw_cache.json")
    if use_cache and target_cache.exists():
        try:
            with open(target_cache, "r", encoding="utf-8") as f:
                items = json.load(f)
            return [Job(**it) for it in items]
        except Exception:
            pass

    from custom_scraper.breezy_scraper import BreezyScraper
    scraper = BreezyScraper()
    res = scraper.scrape("Python", "Bangalore", results_wanted=15)
    jobs = []
    for j in res.jobs:
        j.source = "ats"
        j.ats_provider = "Breezy HR"
        jobs.append(j)

    if jobs:
        try:
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            with open(target_cache, "w", encoding="utf-8") as f:
                json.dump([asdict(j) for j in jobs], f, indent=2, ensure_ascii=False)
        except Exception:
            pass
    return jobs

