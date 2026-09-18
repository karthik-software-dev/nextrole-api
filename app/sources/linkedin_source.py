import json
import logging
from pathlib import Path
from typing import Any

from apify_client import ApifyClient

from config import APIFY_API_TOKEN
from models.job import Job
from models.normalizers.linkedin_normalizer import normalize_linkedin_jobs

logger = logging.getLogger(__name__)

ACTOR_ID = "shahidirfan/Fast-LinkedIn-job-Scraper"
CACHE_DIR = Path(__file__).resolve().parent.parent / "data"
DEFAULT_CACHE_FILE = CACHE_DIR / "linkedin_raw_cache.json"


def fetch_linkedin_jobs(use_cache: bool = False, cache_file: Path | None = None) -> list[Job]:
    """Fetches jobs from LinkedIn via Apify or reads from local cache if enabled.

    Returns normalized Job objects.
    """
    target_cache = cache_file or DEFAULT_CACHE_FILE

    # 1. Check local cache first if requested
    if use_cache and target_cache.exists():
        try:
            with open(target_cache, "r", encoding="utf-8") as f:
                raw_items = json.load(f)
            print(f"[CACHE] Loaded {len(raw_items)} raw items from {target_cache.name}")
            return normalize_linkedin_jobs(raw_items)
        except Exception as e:
            print(f"[WARN] Failed to read LinkedIn cache ({e}), falling back to live Apify fetch...")

    # 2. Live fetch via Apify Client
    print("[APIFY] Connecting to Apify to scrape LinkedIn jobs...")
    client = ApifyClient(APIFY_API_TOKEN)

    run_input = {
        "keyword": "Python Backend Engineer",
        "location": "Bengaluru, India",
        "results_wanted": 25,
        "collectDetails": True,
    }

    try:
        run = client.actor(ACTOR_ID).call(run_input=run_input)
        dataset_id = run.get("defaultDatasetId")
        if not dataset_id:
            raise RuntimeError(f"LinkedIn run finished without a defaultDatasetId: {run}")

        raw_items: list[dict[str, Any]] = list(
            client.dataset(dataset_id).iterate_items()
        )
    except Exception as e:
        print(f"[ERROR] Failed to fetch from LinkedIn via Apify: {e}")
        if target_cache.exists():
            print(f"[FALLBACK] Using existing cache {target_cache.name} due to fetch error.")
            with open(target_cache, "r", encoding="utf-8") as f:
                raw_items = json.load(f)
            return normalize_linkedin_jobs(raw_items)
        raise

    # 3. Save raw items to local cache
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        with open(target_cache, "w", encoding="utf-8") as f:
            json.dump(raw_items, f, indent=2, ensure_ascii=False)
        print(f"[CACHE] Saved {len(raw_items)} raw items to {target_cache.name}")
    except Exception as e:
        print(f"[WARN] Could not save LinkedIn cache to {target_cache}: {e}")

    # 4. Normalize into common Job models
    return normalize_linkedin_jobs(raw_items)
