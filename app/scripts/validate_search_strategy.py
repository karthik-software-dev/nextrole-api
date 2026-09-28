import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Ensure project root is in sys.path
APP_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(APP_DIR))

from apify_client import ApifyClient
from config import extract_apify_dataset_id, get_apify_token
from models.job import Job
from models.normalizers.ats_normalizer import normalize_ats_job
from models.normalizers.google_jobs_normalizer import normalize_google_jobs
from models.normalizers.indeed_normalizer import normalize_indeed_jobs
from models.normalizers.linkedin_normalizer import normalize_linkedin_jobs
from models.normalizers.naukri_normalizer import normalize_naukri_jobs
from models.normalizers.wellfound_normalizer import normalize_wellfound_jobs
from processing.deduplication import deduplicate_jobs
from processing.prioritization import get_location_bucket, prioritize_jobs
from processing.relevance import calculate_relevance_score, filter_relevant_jobs
from processing.url_validator import validate_job_urls
from sources.ats_source import fetch_target_company_jobs

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger("validator")

DATA_DIR = APP_DIR / "data" / "validation"
DATA_DIR.mkdir(parents=True, exist_ok=True)


def run_apify_actor(
    client: ApifyClient,
    actor_id: str,
    run_input: dict[str, Any],
    label: str,
) -> dict[str, Any]:
    """Runs a single Apify actor, records timing, usage, and downloads dataset items."""
    start_t = time.time()
    result: dict[str, Any] = {
        "label": label,
        "actor_id": actor_id,
        "input": run_input,
        "status": "UNKNOWN",
        "items": [],
        "duration_sec": 0.0,
        "compute_units": 0.0,
        "cost_usd": 0.0,
        "error": None,
    }
    logger.info(f"==> Launching [{label}] ({actor_id})...")
    try:
        run = client.actor(actor_id).call(run_input=run_input)
        duration = time.time() - start_t
        result["duration_sec"] = round(duration, 2)
        result["status"] = run.get("status") if isinstance(run, dict) else getattr(run, "status", "UNKNOWN")
        
        usage = run.get("usage") if isinstance(run, dict) else getattr(run, "usage", {})
        if isinstance(usage, dict):
            result["compute_units"] = round(usage.get("ACTOR_COMPUTE_UNITS", 0.0), 6)
        result["cost_usd"] = round(run.get("usageTotalUsd", 0.0) if isinstance(run, dict) else getattr(run, "usageTotalUsd", 0.0), 4)

        dataset_id = extract_apify_dataset_id(run)
        if dataset_id:
            items = list(client.dataset(dataset_id).iterate_items())
            result["items"] = items
            logger.info(f"    [{label}] Finished: {result['status']} | {len(items)} items | {result['duration_sec']}s | {result['compute_units']} CUs")
        else:
            result["error"] = "Missing datasetId"
            logger.warning(f"    [{label}] No dataset ID returned")
    except Exception as e:
        result["duration_sec"] = round(time.time() - start_t, 2)
        result["status"] = "FAILED"
        result["error"] = str(e)
        logger.error(f"    [{label}] Run failed: {e}")

    return result


def analyze_dataset(
    raw_connector_jobs: dict[str, list[Job]],
    run_records: list[dict[str, Any]],
    ats_duration: float = 0.0,
) -> dict[str, Any]:
    """Runs the full processing pipeline and extracts rich evaluation metrics."""
    all_jobs: list[Job] = []
    jobs_by_connector: dict[str, int] = {}
    
    for conn, job_list in raw_connector_jobs.items():
        jobs_by_connector[conn] = len(job_list)
        all_jobs.extend(job_list)

    total_raw = len(all_jobs)
    
    # Normalization count is len(all_jobs) as each is a normalized Job object
    normalized_jobs = all_jobs

    # Calculate relevance scores for all normalized jobs
    scores = []
    for j in normalized_jobs:
        sc, rz = calculate_relevance_score(j)
        j.relevance_score = sc
        scores.append(sc)

    avg_relevance_score = round(sum(scores) / len(scores), 2) if scores else 0.0
    relevant_jobs = [j for j in normalized_jobs if j.relevance_score >= 8.0]
    rejected_jobs = [j for j in normalized_jobs if j.relevance_score < 8.0]

    # Deduplication
    unique_jobs = deduplicate_jobs(relevant_jobs)
    duplicate_count = len(relevant_jobs) - len(unique_jobs)
    duplicate_pct = round((duplicate_count / len(relevant_jobs) * 100), 2) if relevant_jobs else 0.0

    # URL Validation & Prioritization
    validated_jobs = validate_job_urls(unique_jobs)
    prioritized_jobs = prioritize_jobs(validated_jobs)

    # Breakdown by location
    blr_count = sum(1 for j in prioritized_jobs if get_location_bucket(j) == "BANGALORE")
    maa_count = sum(1 for j in prioritized_jobs if get_location_bucket(j) == "CHENNAI")
    other_remote_count = sum(1 for j in prioritized_jobs if get_location_bucket(j) == "OTHER")

    # Breakdown by technology categories across unique relevant jobs
    def match_terms(job: Job, terms: list[str]) -> bool:
        haystack = f"{job.title or ''} {job.description or ''} {' '.join(job.matched_skills or [])}".lower()
        return any(t.lower() in haystack for t in terms)

    ai_llm_jobs = [j for j in unique_jobs if match_terms(j, ["ai", "llm", "rag", "genai", "generative ai", "langchain", "vector", "openai"])]
    full_stack_jobs = [j for j in unique_jobs if match_terms(j, ["full stack", "fullstack", "react"])]
    fastapi_jobs = [j for j in unique_jobs if match_terms(j, ["fastapi"])]
    flask_jobs = [j for j in unique_jobs if match_terms(j, ["flask"])]
    microservices_jobs = [j for j in unique_jobs if match_terms(j, ["microservice", "microservices"])]

    # Cost and compute totals
    total_duration = sum(r.get("duration_sec", 0.0) for r in run_records) + ats_duration
    total_cus = round(sum(r.get("compute_units", 0.0) for r in run_records), 6)
    total_cost = round(sum(r.get("cost_usd", 0.0) for r in run_records), 4)

    return {
        "raw_jobs_total": total_raw,
        "normalized_jobs": len(normalized_jobs),
        "relevant_jobs": len(relevant_jobs),
        "unique_jobs": len(unique_jobs),
        "prioritized_jobs": len(prioritized_jobs),
        "rejected_jobs": len(rejected_jobs),
        "duplicate_count": duplicate_count,
        "duplicate_pct": duplicate_pct,
        "avg_relevance_score": avg_relevance_score,
        "bengaluru_jobs": blr_count,
        "chennai_jobs": maa_count,
        "other_remote_jobs": other_remote_count,
        "ai_llm_jobs": len(ai_llm_jobs),
        "full_stack_jobs": len(full_stack_jobs),
        "fastapi_jobs": len(fastapi_jobs),
        "flask_jobs": len(flask_jobs),
        "microservices_jobs": len(microservices_jobs),
        "apify_calls": len(run_records),
        "execution_time_sec": round(total_duration, 2),
        "compute_units": total_cus,
        "cost_usd": total_cost,
        "jobs_by_connector": jobs_by_connector,
        "runs": [
            {
                "label": r["label"],
                "actor_id": r["actor_id"],
                "status": r["status"],
                "items_count": len(r["items"]),
                "duration_sec": r["duration_sec"],
                "compute_units": r["compute_units"],
                "cost_usd": r["cost_usd"],
                "error": r.get("error"),
                "relevant_count": sum(1 for j in r.get("normalized_jobs", []) if j.relevance_score >= 8.0),
                "rejected_count": sum(1 for j in r.get("normalized_jobs", []) if j.relevance_score < 8.0),
                "sample_relevant_titles": [j.title for j in r.get("normalized_jobs", []) if j.relevance_score >= 8.0][:4],
                "sample_rejected_titles": [j.title for j in r.get("normalized_jobs", []) if j.relevance_score < 8.0][:4],
            }
            for r in run_records
        ],
    }


def run_baseline(client: ApifyClient) -> dict[str, Any]:
    """Executes the exact current production search queries across connectors."""
    logger.info("==================================================")
    logger.info("STARTING BASELINE RUN (CURRENT PRODUCTION SEARCH)")
    logger.info("==================================================")
    
    run_records: list[dict[str, Any]] = []
    connector_jobs: dict[str, list[Job]] = {
        "indeed": [],
        "linkedin": [],
        "naukri": [],
        "wellfound": [],
        "google_jobs": [],
        "ats": [],
    }

    # 1. Indeed Baseline (2 calls)
    indeed_configs = [
        ("Indeed Core BLR", {
            "position": "Python Backend Engineer",
            "location": "Bengaluru",
            "maxItemsPerSearch": 25,
            "country": "IN",
            "parseCompanyDetails": True,
            "saveOnlyUniqueItems": True,
        }),
        ("Indeed Core MAA", {
            "position": "Python Backend Developer",
            "location": "Chennai",
            "maxItemsPerSearch": 25,
            "country": "IN",
            "parseCompanyDetails": True,
            "saveOnlyUniqueItems": True,
        }),
    ]
    for label, inp in indeed_configs:
        rec = run_apify_actor(client, "misceres/indeed-scraper", inp, label)
        norm = normalize_indeed_jobs(rec["items"]) if rec["items"] else []
        rec["normalized_jobs"] = norm
        connector_jobs["indeed"].extend(norm)
        run_records.append(rec)

    # 2. LinkedIn Baseline (2 calls)
    linkedin_configs = [
        ("LinkedIn Core BLR", {
            "keyword": "Python Backend Engineer",
            "location": "Bengaluru, India",
            "results_wanted": 50,
            "posted_date": "7d",
            "collectDetails": True,
        }),
        ("LinkedIn Core MAA", {
            "keyword": "Python Backend Engineer",
            "location": "Chennai, India",
            "results_wanted": 50,
            "posted_date": "7d",
            "collectDetails": True,
        }),
    ]
    for label, inp in linkedin_configs:
        rec = run_apify_actor(client, "shahidirfan/Fast-LinkedIn-job-Scraper", inp, label)
        norm = normalize_linkedin_jobs(rec["items"]) if rec["items"] else []
        rec["normalized_jobs"] = norm
        connector_jobs["linkedin"].extend(norm)
        run_records.append(rec)

    # 3. Naukri Baseline (2 calls)
    naukri_configs = [
        ("Naukri Core BLR", {
            "searchUrl": "https://www.naukri.com/python-backend-engineer-jobs-in-bengaluru",
            "maxJobs": 50,
            "fetchDetails": True,
            "sortBy": "date",
            "freshness": "7",
        }),
        ("Naukri Core MAA", {
            "searchUrl": "https://www.naukri.com/python-backend-developer-jobs-in-chennai",
            "maxJobs": 50,
            "fetchDetails": True,
            "sortBy": "date",
            "freshness": "7",
        }),
    ]
    for label, inp in naukri_configs:
        rec = run_apify_actor(client, "muhammetakkurtt/naukri-job-scraper", inp, label)
        norm = normalize_naukri_jobs(rec["items"]) if rec["items"] else []
        rec["normalized_jobs"] = norm
        connector_jobs["naukri"].extend(norm)
        run_records.append(rec)

    # 4. Wellfound Baseline (1 call)
    wellfound_inp = {
        "role": "backend-engineer",
        "location": "bangalore",
        "maxItems": 15,
    }
    rec_wf = run_apify_actor(client, "chimerical_quicklime/wellfound-startup-jobs-scraper", wellfound_inp, "Wellfound Backend BLR")
    norm_wf = normalize_wellfound_jobs(rec_wf["items"]) if rec_wf["items"] else []
    rec_wf["normalized_jobs"] = norm_wf
    connector_jobs["wellfound"].extend(norm_wf)
    run_records.append(rec_wf)

    # 5. Google Jobs Baseline (1 call)
    google_inp = {
        "job_title": "Python Backend Engineer",
        "location": "Bengaluru, India",
        "no_of_jobs": 15,
    }
    rec_gj = run_apify_actor(client, "nuclear_quietude/google-jobs-scraper-api", google_inp, "Google Corporate BLR")
    norm_gj = normalize_google_jobs(rec_gj["items"]) if rec_gj["items"] else []
    rec_gj["normalized_jobs"] = norm_gj
    connector_jobs["google_jobs"].extend(norm_gj)
    run_records.append(rec_gj)

    # 6. Target ATS Baseline (Live direct API fetch)
    logger.info("==> Running Target ATS Direct Portals (Baseline)...")
    ats_start = time.time()
    try:
        ats_jobs = fetch_target_company_jobs(use_cache=False)
        connector_jobs["ats"].extend(ats_jobs)
        ats_dur = round(time.time() - ats_start, 2)
        logger.info(f"    [ATS Portals] Finished in {ats_dur}s with {len(ats_jobs)} normalized jobs.")
    except Exception as e:
        ats_dur = round(time.time() - ats_start, 2)
        logger.warning(f"    [ATS Portals] Failed: {e}")

    summary = analyze_dataset(connector_jobs, run_records, ats_duration=ats_dur)
    
    with open(DATA_DIR / "baseline_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    return summary


def run_proposed(client: ApifyClient) -> dict[str, Any]:
    """Executes the proposed optimized search strategy with query grouping, freshness, and low latency."""
    logger.info("==================================================")
    logger.info("STARTING PROPOSED EXPERIMENTAL RUN (OPTIMIZED)")
    logger.info("==================================================")
    
    run_records: list[dict[str, Any]] = []
    connector_jobs: dict[str, list[Job]] = {
        "indeed": [],
        "linkedin": [],
        "naukri": [],
        "wellfound": [],
        "google_jobs": [],
        "ats": [],
    }

    # 1. Indeed Proposed (4 calls: parseCompanyDetails=False, Boolean grouping, 7d/15d)
    indeed_configs = [
        ("Indeed Core BLR (7d)", {
            "position": '"Python Backend" OR "FastAPI" OR "Python API"',
            "location": "Bengaluru",
            "maxItemsPerSearch": 35,
            "country": "IN",
            "fromDays": 7,
            "parseCompanyDetails": False,
            "saveOnlyUniqueItems": True,
        }),
        ("Indeed Core MAA (7d)", {
            "position": '"Python Backend" OR "FastAPI" OR "Python Flask"',
            "location": "Chennai",
            "maxItemsPerSearch": 25,
            "country": "IN",
            "fromDays": 7,
            "parseCompanyDetails": False,
            "saveOnlyUniqueItems": True,
        }),
        ("Indeed FullStack/Arch BLR (15d)", {
            "position": '"Python Full Stack" OR "Python React" OR "Python Microservices"',
            "location": "Bengaluru",
            "maxItemsPerSearch": 25,
            "country": "IN",
            "fromDays": 15,
            "parseCompanyDetails": False,
            "saveOnlyUniqueItems": True,
        }),
        ("Indeed AI/LLM/RAG BLR (15d)", {
            "position": '"Python AI Engineer" OR "Python LLM" OR "Python RAG"',
            "location": "Bengaluru",
            "maxItemsPerSearch": 25,
            "country": "IN",
            "fromDays": 15,
            "parseCompanyDetails": False,
            "saveOnlyUniqueItems": True,
        }),
    ]
    for label, inp in indeed_configs:
        rec = run_apify_actor(client, "misceres/indeed-scraper", inp, label)
        norm = normalize_indeed_jobs(rec["items"]) if rec["items"] else []
        rec["normalized_jobs"] = norm
        connector_jobs["indeed"].extend(norm)
        run_records.append(rec)

    # 2. LinkedIn Proposed (4 calls: Boolean grouping, collectDetails=True, 7d/14d)
    linkedin_configs = [
        ("LinkedIn Core BLR (7d)", {
            "keyword": '("Python Backend" OR "Python API" OR "FastAPI" OR "Python Flask")',
            "location": "Bengaluru, India",
            "results_wanted": 40,
            "posted_date": "7d",
            "collectDetails": True,
        }),
        ("LinkedIn Core MAA (7d)", {
            "keyword": '("Python Backend" OR "Python API" OR "FastAPI" OR "Python Flask")',
            "location": "Chennai, India",
            "results_wanted": 30,
            "posted_date": "7d",
            "collectDetails": True,
        }),
        ("LinkedIn FullStack BLR (15d)", {
            "keyword": '("Python Full Stack" OR "Python React" OR "React FastAPI" OR "Python Microservices")',
            "location": "Bengaluru, India",
            "results_wanted": 30,
            "posted_date": "30d",
            "collectDetails": True,
        }),
        ("LinkedIn AI/LLM BLR (15d)", {
            "keyword": '("Python AI Engineer" OR "Python LLM" OR "Python RAG" OR "GenAI Python" OR "AI Backend Python")',
            "location": "Bengaluru, India",
            "results_wanted": 30,
            "posted_date": "30d",
            "collectDetails": True,
        }),
    ]
    for label, inp in linkedin_configs:
        rec = run_apify_actor(client, "shahidirfan/Fast-LinkedIn-job-Scraper", inp, label)
        norm = normalize_linkedin_jobs(rec["items"]) if rec["items"] else []
        rec["normalized_jobs"] = norm
        connector_jobs["linkedin"].extend(norm)
        run_records.append(rec)

    # 3. Naukri Proposed (4 calls: Validated slugs, maxJobs >= 50)
    naukri_configs = [
        ("Naukri Core BLR (7d)", {
            "searchUrl": "https://www.naukri.com/python-backend-engineer-jobs-in-bengaluru",
            "maxJobs": 50,
            "fetchDetails": True,
            "sortBy": "date",
            "freshness": "7",
        }),
        ("Naukri Core MAA (7d)", {
            "searchUrl": "https://www.naukri.com/python-backend-developer-jobs-in-chennai",
            "maxJobs": 50,
            "fetchDetails": True,
            "sortBy": "date",
            "freshness": "7",
        }),
        ("Naukri FastAPI BLR (7d)", {
            "searchUrl": "https://www.naukri.com/fastapi-developer-jobs-in-bengaluru",
            "maxJobs": 50,
            "fetchDetails": True,
            "sortBy": "date",
            "freshness": "7",
        }),
        ("Naukri FullStack BLR (15d)", {
            "searchUrl": "https://www.naukri.com/python-full-stack-developer-jobs-in-bengaluru",
            "maxJobs": 50,
            "fetchDetails": True,
            "sortBy": "date",
            "freshness": "15",
        }),
    ]
    for label, inp in naukri_configs:
        rec = run_apify_actor(client, "muhammetakkurtt/naukri-job-scraper", inp, label)
        norm = normalize_naukri_jobs(rec["items"]) if rec["items"] else []
        rec["normalized_jobs"] = norm
        connector_jobs["naukri"].extend(norm)
        run_records.append(rec)

    # 4. Wellfound Proposed (2 calls: Backend + Full Stack)
    wellfound_configs = [
        ("Wellfound Backend BLR", {
            "role": "backend-engineer",
            "location": "bangalore",
            "maxItems": 25,
        }),
        ("Wellfound FullStack BLR", {
            "role": "full-stack-engineer",
            "location": "bangalore",
            "maxItems": 20,
        }),
    ]
    for label, inp in wellfound_configs:
        rec = run_apify_actor(client, "chimerical_quicklime/wellfound-startup-jobs-scraper", inp, label)
        norm = normalize_wellfound_jobs(rec["items"]) if rec["items"] else []
        rec["normalized_jobs"] = norm
        connector_jobs["wellfound"].extend(norm)
        run_records.append(rec)

    # 5. Google Jobs Proposed (1 call: Verified Google corporate backend)
    google_inp = {
        "job_title": "Software Engineer Backend",
        "location": "Bengaluru, India",
        "no_of_jobs": 20,
    }
    rec_gj = run_apify_actor(client, "nuclear_quietude/google-jobs-scraper-api", google_inp, "Google Corporate Backend BLR")
    norm_gj = normalize_google_jobs(rec_gj["items"]) if rec_gj["items"] else []
    rec_gj["normalized_jobs"] = norm_gj
    connector_jobs["google_jobs"].extend(norm_gj)
    run_records.append(rec_gj)

    # 6. Target ATS Proposed (Enhanced with Profile Keyword Filtering before hydration)
    logger.info("==> Running Target ATS Direct Portals (Enhanced Ingestion Filter)...")
    ats_start = time.time()
    try:
        raw_ats_jobs = fetch_target_company_jobs(use_cache=False)
        target_kw = ["python", "backend", "fastapi", "flask", "full stack", "fullstack", "react", "microservice", "ai", "llm", "rag", "genai", "engineer", "developer"]
        filtered_ats = [
            j for j in raw_ats_jobs
            if any(k in (j.title or "").lower() for k in target_kw)
        ]
        connector_jobs["ats"].extend(filtered_ats)
        ats_dur = round(time.time() - ats_start, 2)
        logger.info(f"    [ATS Portals Enhanced] Finished in {ats_dur}s. Yielded {len(filtered_ats)} tech-relevant jobs (from {len(raw_ats_jobs)} raw).")
    except Exception as e:
        ats_dur = round(time.time() - ats_start, 2)
        logger.warning(f"    [ATS Portals Enhanced] Failed: {e}")

    summary = analyze_dataset(connector_jobs, run_records, ats_duration=ats_dur)
    
    with open(DATA_DIR / "proposed_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    return summary


def main():
    token = get_apify_token()
    if not token:
        logger.error("APIFY_API_TOKEN is missing. Aborting validation.")
        sys.exit(1)

    client = ApifyClient(token)

    mode = sys.argv[1] if len(sys.argv) > 1 else "--both"

    if mode in ("--baseline", "--both"):
        run_baseline(client)

    if mode in ("--proposed", "--both"):
        run_proposed(client)

    logger.info("Validation run completed successfully. Summaries written to data/validation/")


if __name__ == "__main__":
    main()

