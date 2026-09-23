import sys
from pathlib import Path

# Ensure UTF-8 output encoding for symbols like Indian Rupee (₹) on Windows terminals
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from processing.deduplication import deduplicate_jobs
from processing.prioritization import prioritize_jobs, get_location_bucket, select_by_location_quota
from processing.relevance import filter_relevant_jobs
from processing.url_validator import validate_job_urls
from sources.ats_source import fetch_target_company_jobs
from sources.google_jobs_source import fetch_google_jobs
from sources.indeed_source import fetch_indeed_jobs
from sources.linkedin_source import fetch_linkedin_jobs
from sources.naukri_source import fetch_naukri_jobs
from sources.wellfound_source import fetch_wellfound_jobs
from storage.database import get_db, init_db
from storage.repositories.job_repository import JobRepository


def main():
    print("=" * 60)
    print("JOB DISCOVERY ENGINE - MULTI-SOURCE & TARGET CAREERS (V6)")
    print("=" * 60)

    # Database Dashboard / CLI inspect commands
    if "--db-stats" in sys.argv:
        if init_db():
            with get_db() as session:
                stats = JobRepository.get_database_stats(session)
                print("\n" + "=" * 60)
                print("POSTGRESQL DATABASE DASHBOARD SUMMARY ('job_agent')")
                print("=" * 60)
                print(f"Total Canonical Jobs   : {stats['total_jobs']}")
                print(f"Active Opportunities   : {stats['active_jobs']}")
                print(f"Inactive / Soft-Deleted: {stats['inactive_jobs']}")
                print(f"Tier 1 (High Priority) : {stats['tier1_jobs']}")
                print(f"Tier 2 (Solid Match)   : {stats['tier2_jobs']}")
                print(f"Tracked Companies      : {stats['total_companies']}")
                print(f"Total Source Postings  : {stats['total_sources']}")
                print(f"Bengaluru Opportunities: {stats['bangalore_jobs']}")
                print(f"Chennai Opportunities  : {stats['chennai_jobs']}")
                print(f"Other / Remote Jobs    : {stats['other_jobs']}")
                print("=" * 60 + "\n")
        return

    deact_arg = next((arg.split("=")[1] for arg in sys.argv if arg.startswith("--deactivate=")), None)
    if deact_arg:
        if init_db():
            with get_db() as session:
                try:
                    job_id = int(deact_arg)
                    success = JobRepository.deactivate_job(session, job_id)
                    if success:
                        print(f"\n[DATABASE] Job #{job_id} successfully marked as inactive (soft-deleted).\n")
                    else:
                        print(f"\n[WARN] Job #{job_id} not found in database.\n")
                except ValueError:
                    print("\n[ERROR] Invalid job ID for --deactivate. Must be an integer.\n")
        return

    # Check CLI arguments
    force_live = "--live" in sys.argv
    use_cache = not force_live


    # Determine which sources to scrape
    source_arg = next((arg.split("=")[1].lower() for arg in sys.argv if arg.startswith("--source=")), "all")
    location_arg = next((arg.split("=")[1].lower() for arg in sys.argv if arg.startswith("--location=")), "all")

    print(f"\n[CONFIG] Source: {source_arg.upper()} | Location: {location_arg.upper()} | Cache Mode: {'ENABLED' if use_cache else 'LIVE FETCH'}")
    print("\nFetching & normalizing jobs across active sources...\n")

    jobs = []
    source_counts = {}

    source_definitions = [
        ("Indeed", ("indeed", "all"), fetch_indeed_jobs),
        ("Naukri", ("naukri", "all"), fetch_naukri_jobs),
        ("LinkedIn", ("linkedin", "all"), fetch_linkedin_jobs),
        ("Wellfound", ("wellfound", "all"), fetch_wellfound_jobs),
        ("Google Jobs", ("google_jobs", "google", "all"), fetch_google_jobs),
        ("Target Careers", ("ats", "careers", "target_companies", "all"), fetch_target_company_jobs),
    ]

    for label, triggers, fetcher in source_definitions:
        if source_arg in triggers:
            try:
                fetched_jobs = fetcher(use_cache=use_cache)
                source_counts[label] = len(fetched_jobs)
                jobs.extend(fetched_jobs)
            except Exception as src_err:
                print(f"[WARN] Failed to fetch from {label}: {src_err}")
                source_counts[label] = 0

    sources_summary = ", ".join(f"{k}: {v}" for k, v in source_counts.items())
    print(f"\nTotal jobs collected & normalized: {len(jobs)} ({sources_summary})")

    relevant_jobs = filter_relevant_jobs(jobs)
    unique_jobs = deduplicate_jobs(relevant_jobs)
    validated_jobs = validate_job_urls(unique_jobs)
    prioritized_jobs = prioritize_jobs(validated_jobs)

    # Apply location filtering or 80/15/5 quota selection
    if location_arg in ("bangalore", "bengaluru", "blr"):
        prioritized_jobs = [j for j in prioritized_jobs if any(k in (j.location or "").lower() for k in ["bengaluru", "bangalore", "karnataka"])]
    elif location_arg in ("chennai", "maa"):
        prioritized_jobs = [j for j in prioritized_jobs if any(k in (j.location or "").lower() for k in ["chennai", "tamil nadu"])]
    elif location_arg in ("other", "remote", "hyd", "hyderabad", "pune"):
        prioritized_jobs = [j for j in prioritized_jobs if not any(k in (j.location or "").lower() for k in ["bengaluru", "bangalore", "karnataka", "chennai"])]
    else:
        # Default 'all': apply 80% Bangalore / 15% Chennai / 5% Other quota
        prioritized_jobs = select_by_location_quota(prioritized_jobs, target_total=100)

    duplicates_count = len(relevant_jobs) - len(prioritized_jobs)
    direct_ats_count = sum(1 for j in prioritized_jobs if j.apply_type in ("DIRECT_ATS", "COMPANY_CAREERS"))
    tier1_count = sum(1 for j in prioritized_jobs if "TIER 1" in j.priority_tier)
    tier2_count = sum(1 for j in prioritized_jobs if "TIER 2" in j.priority_tier)
    tier3_count = sum(1 for j in prioritized_jobs if "TIER 3" in j.priority_tier)

    blr_count = sum(1 for j in prioritized_jobs if any(k in (j.location or "").lower() for k in ["bengaluru", "bangalore", "karnataka"]))
    maa_count = sum(1 for j in prioritized_jobs if any(k in (j.location or "").lower() for k in ["chennai", "tamil nadu"]))
    other_count = sum(1 for j in prioritized_jobs if not any(k in (j.location or "").lower() for k in ["bengaluru", "bangalore", "karnataka", "chennai", "tamil nadu"]))

    print(f"Relevant opportunities found : {len(relevant_jobs)}")
    print(f"Duplicates merged            : {duplicates_count}")
    print(f"Actionable unique jobs       : {len(prioritized_jobs)}")
    print(f"Direct ATS / Career links    : {direct_ats_count}/{len(prioritized_jobs)}")
    print(f"Priority breakdown           : {tier1_count} High Priority | {tier2_count} Solid | {tier3_count} Standard")
    print(f"Location breakdown           : {blr_count} Bengaluru | {maa_count} Chennai | {other_count} Other/Remote\n")

    print("=" * 60)
    print("ACTIONABLE OPPORTUNITIES (Prioritized)")
    print("=" * 60)

    for index, job in enumerate(prioritized_jobs, start=1):
        location_display = job.location or "Not specified"
        if job.is_remote and "remote" not in location_display.lower():
            location_display += " (Remote)"
        if len(location_display) > 65:
            cities = [c.strip() for c in location_display.split(",")]
            if len(cities) > 3:
                suffix = " (Remote)" if "remote" in location_display.lower() else ""
                location_display = f"{', '.join(cities[:3])}, +{len(cities)-3} cities{suffix}"

        salary_display = (job.salary_raw or "Not disclosed").replace("₹", "INR ").replace("–", "-").replace("•", "|")
        
        if job.apply_url and job.ats_provider:
            direct_apply = f"[{job.ats_provider}] {job.apply_url}"
        elif job.apply_url:
            direct_apply = job.apply_url
        else:
            direct_apply = "Not available (Use Discovery link)"

        skills_display = ", ".join(job.matched_skills) if job.matched_skills else "General match"

        exp_display = job.experience_raw or "Not specified"
        if job.experience_min is not None and job.experience_min <= 3 and (job.experience_max is None or job.experience_max <= 5):
            exp_display += " (Sweet-Spot 1-5 Yrs)"

        loc_lower = (job.location or "").lower()
        has_blr = any(k in loc_lower for k in ["bengaluru", "bangalore", "karnataka"])
        has_maa = any(k in loc_lower for k in ["chennai", "tamil nadu"])

        if location_arg in ("chennai", "maa"):
            loc_badge = "📍 CHENNAI"
        elif location_arg in ("bangalore", "bengaluru", "blr"):
            loc_badge = "📍 BENGALURU"
        elif has_blr and has_maa:
            loc_badge = "📍 BLR / CHENNAI"
        elif has_blr:
            loc_badge = "📍 BENGALURU"
        elif has_maa:
            loc_badge = "📍 CHENNAI"
        else:
            loc_badge = "📍 OTHER / REMOTE"

        print(f"\n#{index}  {job.priority_tier} [{loc_badge}]", flush=True)
        print(f"ID           : {job.id}", flush=True)
        print(f"Source       : {job.source.upper()}", flush=True)
        print(f"Title        : {job.title}", flush=True)
        print(f"Company      : {job.company}", flush=True)
        print(f"Experience   : {exp_display}", flush=True)
        print(f"Location     : {location_display}", flush=True)
        print(f"Salary       : {salary_display}", flush=True)
        print(f"Priority     : {job.priority_score} (Relevance Score: {job.relevance_score})", flush=True)
        print(f"Skills       : {skills_display}", flush=True)
        if job.duplicate_count > 1:
            print(f"Duplicates   : {job.duplicate_count} listings merged", flush=True)
        print(f"Direct Apply : {direct_apply}", flush=True)
        print(f"Discovery    : {job.discovery_url}", flush=True)

    # Persist and Sync Opportunities to PostgreSQL Database ('job_agent')
    try:
        if init_db():
            with get_db() as session:
                synced_count = 0
                for job in prioritized_jobs:
                    try:
                        with session.begin_nested():
                            JobRepository.upsert_job(session, job)
                        synced_count += 1
                    except Exception as job_err:
                        print(f"[WARN] Failed to sync job '{job.title}': {job_err}")
                print(f"\n[DATABASE] Successfully synced {synced_count} opportunities to PostgreSQL ('job_agent')")
    except Exception as e:
        print(f"\n[WARN] Database sync skipped ({e})")

    print("\n" + "=" * 60)
    print("DONE")
    print("=" * 60)


if __name__ == "__main__":
    main()