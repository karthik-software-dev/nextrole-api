"""One-time idempotent database maintenance script to synchronize relevance scores
and is_active status across all jobs in PostgreSQL according to the frozen relevance engine.
"""

import os
import sys

# Ensure app package is on path
APP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from datetime import datetime, timezone
from sqlalchemy import func, select
from storage.database import get_db
from storage.models.job import Job
from storage.models.company import Company
from models.job import Job as JobDataclass
from processing.relevance import calculate_relevance_score

MIN_RELEVANCE_THRESHOLD = 8.0


def sync_database_relevance(dry_run: bool = False) -> dict:
    """Recalculates relevance scores and synchronizes is_active for all jobs in PostgreSQL.

    Args:
        dry_run: If True, calculates and reports changes without committing to DB.

    Returns:
        dict: Summary statistics of the operation.
    """
    stats = {
        "total_jobs": 0,
        "before_active": 0,
        "before_inactive": 0,
        "after_active": 0,
        "after_inactive": 0,
        "deactivated_count": 0,
        "reactivated_count": 0,
        "benchmark_84": {
            "total": 0,
            "relevant_active": 0,
            "not_relevant_inactive": 0,
        },
    }

    with get_db() as session:
        # Load all canonical jobs with company joined
        jobs = session.scalars(select(Job).order_by(Job.id)).all()
        stats["total_jobs"] = len(jobs)

        for job in jobs:
            if job.is_active:
                stats["before_active"] += 1
            else:
                stats["before_inactive"] += 1

            # Convert DB model to JobDataclass for relevance scoring
            company_name = job.company.name if job.company else "Unknown"
            desc = job.description
            if not desc or len(desc.strip()) == 0:
                skills_str = ", ".join(job.matched_skills or [])
                desc = f"Job Title: {job.title} at {company_name}. Required skills mentioned: {skills_str}."

            job_dc = JobDataclass(
                id=str(job.id),
                title=job.title,
                company=company_name,
                description=desc,
                location=job.location,
                is_remote=job.is_remote,
                experience_min=job.experience_min,
                experience_max=job.experience_max,
                experience_raw=job.experience_raw,
                salary_min=float(job.salary_min) if job.salary_min is not None else None,
                salary_max=float(job.salary_max) if job.salary_max is not None else None,
                salary_raw=job.salary_raw,
                apply_url=job.canonical_apply_url,
                apply_type=job.apply_type,
                ats_provider=job.ats_provider,
            )

            # Recalculate score and matched skills with frozen rules
            score, matched_skills = calculate_relevance_score(job_dc)
            new_is_active = (score >= MIN_RELEVANCE_THRESHOLD)

            # Track transitions
            if job.is_active and not new_is_active:
                stats["deactivated_count"] += 1
            elif not job.is_active and new_is_active:
                stats["reactivated_count"] += 1

            # Update DB record
            job.relevance_score = score
            job.matched_skills = matched_skills
            job.is_active = new_is_active

            if new_is_active:
                stats["after_active"] += 1
            else:
                stats["after_inactive"] += 1

            # Track 84-job benchmark (IDs 122 to 206)
            if 122 <= job.id <= 206:
                stats["benchmark_84"]["total"] += 1
                if new_is_active:
                    stats["benchmark_84"]["relevant_active"] += 1
                else:
                    stats["benchmark_84"]["not_relevant_inactive"] += 1

        if not dry_run:
            session.commit()
            print(f"[SUCCESS] Database changes committed to PostgreSQL.")
        else:
            session.rollback()
            print(f"[DRY RUN] No changes were committed to PostgreSQL.")

    return stats


def print_summary(stats: dict):
    print("\n" + "=" * 65)
    print("      DATABASE RELEVANCE & LIFECYCLE SYNCHRONIZATION")
    print("=" * 65)
    print(f"Total Jobs in Database        : {stats['total_jobs']}")
    print(f"Active Before Synchronization : {stats['before_active']}")
    print(f"Inactive Before               : {stats['before_inactive']}")
    print("-" * 65)
    print(f"Jobs Deactivated (score < 8.0): {stats['deactivated_count']}")
    print(f"Jobs Reactivated (score >= 8) : {stats['reactivated_count']}")
    print("-" * 65)
    print(f"Active After Synchronization  : {stats['after_active']}")
    print(f"Inactive After                : {stats['after_inactive']}")
    print("=" * 65)
    b84 = stats["benchmark_84"]
    print("      84-JOB BENCHMARK DATASET VALIDATION (IDs 122 - 206)")
    print("-" * 65)
    print(f"Benchmark Dataset Size        : {b84['total']}")
    print(f"Relevant & Active (score >= 8): {b84['relevant_active']} (Expected: 58)")
    print(f"Disqualified & Inactive (< 8) : {b84['not_relevant_inactive']} (Expected: 26)")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    is_dry = "--dry-run" in sys.argv
    res = sync_database_relevance(dry_run=is_dry)
    print_summary(res)
