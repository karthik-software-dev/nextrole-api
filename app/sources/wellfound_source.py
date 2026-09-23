import json
import logging
from pathlib import Path
from typing import Any

from apify_client import ApifyClient

from config import APIFY_API_TOKEN
from models.job import Job
from models.normalizers.wellfound_normalizer import normalize_wellfound_jobs

logger = logging.getLogger(__name__)

ACTOR_ID = "chimerical_quicklime/wellfound-startup-jobs-scraper"
CACHE_DIR = Path(__file__).resolve().parent.parent / "data"
DEFAULT_CACHE_FILE = CACHE_DIR / "wellfound_raw_cache.json"


def fetch_wellfound_jobs(use_cache: bool = False, cache_file: Path | None = None) -> list[Job]:
    """Fetches jobs from Wellfound via Apify or reads from local cache if enabled.

    Returns normalized Job models.
    """
    target_cache = cache_file or DEFAULT_CACHE_FILE

    # 1. Check local cache first if requested
    if use_cache and target_cache.exists():
        try:
            with open(target_cache, "r", encoding="utf-8") as f:
                raw_items = json.load(f)
            print(f"[CACHE] Loaded {len(raw_items)} raw items from {target_cache.name}")
            return normalize_wellfound_jobs(raw_items)
        except Exception as e:
            print(f"[WARN] Failed to read Wellfound cache ({e}), falling back to live Apify fetch...")

    # 2. Check Apify Token
    if not APIFY_API_TOKEN:
        print("[WARN] APIFY_API_TOKEN not configured in environment.")
        if target_cache.exists():
            print(f"[FALLBACK] Using existing cache {target_cache.name}.")
            with open(target_cache, "r", encoding="utf-8") as f:
                raw_items = json.load(f)
            return normalize_wellfound_jobs(raw_items)
        return []

    # 3. Live fetch via Apify Client
    print("[APIFY] Connecting to Apify to scrape Wellfound startup jobs...")
    client = ApifyClient(APIFY_API_TOKEN)

    run_input = {
        "role": "backend-engineer",
        "location": "bangalore",
        "maxItems": 15,
    }

    try:
        run = client.actor(ACTOR_ID).call(run_input=run_input)
        dataset_id = run.get("defaultDatasetId")
        if not dataset_id:
            raise RuntimeError(f"Wellfound run finished without a defaultDatasetId: {run}")

        raw_items: list[dict[str, Any]] = list(
            client.dataset(dataset_id).iterate_items()
        )
    except Exception as e:
        print(f"[ERROR] Failed to fetch from Wellfound via Apify: {e}")
        if target_cache.exists():
            print(f"[FALLBACK] Using existing cache {target_cache.name} due to fetch error.")
            with open(target_cache, "r", encoding="utf-8") as f:
                raw_items = json.load(f)
            return normalize_wellfound_jobs(raw_items)
        return []

    # 3. Save raw items to local cache
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        with open(target_cache, "w", encoding="utf-8") as f:
            json.dump(raw_items, f, indent=2, ensure_ascii=False)
        print(f"[CACHE] Saved {len(raw_items)} raw items to {target_cache.name}")
    except Exception as e:
        print(f"[WARN] Could not save Wellfound cache to {target_cache}: {e}")

    # 4. Normalize into common Job models
    return normalize_wellfound_jobs(raw_items)
