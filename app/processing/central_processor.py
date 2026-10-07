"""Central Job Processing Layer.

Single Source of Truth for:
1. Normalization & Structured Enrichment
2. Freshness evaluation
3. Experience & Seniority filtering
4. Hard title & language exclusions
5. Python/backend ecosystem relevance
6. Location, remote & foreign job filtering
7. Cross-source semantic deduplication
8. Direct ATS apply link & source merging
9. Relevance scoring (>= 8.0)
10. Priority scoring & Tier 1/2/3 classification
11. Final actionable vs irrelevant determination
"""

import logging
import re
from datetime import datetime, timezone
from typing import Optional

from models.job import Job
from processing.experience_parser import extract_experience
from processing.salary_parser import format_salary_display, parse_salary
from processing.deduplication import clean_job_title, deduplicate_jobs
from processing.prioritization import (
    get_location_bucket,
    prioritize_jobs,
    select_by_location_quota,
)
from processing.relevance import calculate_relevance_score, filter_relevant_jobs
from processing.url_validator import validate_job_urls

logger = logging.getLogger("processing.central_processor")


class CentralJobProcessor:
    """Consolidated single processing engine for the entire Job Agent system."""

    @staticmethod
    def normalize_job_fields(job: Job) -> Job:
        """Enriches and standardizes raw job fields before evaluation."""
        if job.title:
            job.title = clean_job_title(job.title)

        # Experience enrichment if not present
        if job.experience_min is None and (job.description or job.experience_raw):
            text_to_check = f"{job.experience_raw or ''} {job.description or ''}"
            e_min, e_max, e_raw = extract_experience(text_to_check)
            if e_min is not None:
                job.experience_min = e_min
                job.experience_max = e_max
            if e_raw and not job.experience_raw:
                job.experience_raw = e_raw

        # Salary enrichment if raw string present, or check description for clear compensation statements
        if job.salary_min is None:
            if job.salary_raw:
                s_min, s_max, s_curr = parse_salary(job.salary_raw)
                if s_min is not None or s_max is not None:
                    job.salary_min = s_min
                    job.salary_max = s_max
                    job.salary_currency = s_curr
            elif job.description:
                sal_match = re.search(
                    r"(?:salary|ctc|compensation|stipend|package)\s*(?::|-|is)?\s*([₹INR$\w\s\.\,\-]+?(?:LPA|Lacs?|Lakhs?|p\.?a\.?|per\s+annum|/yr|a\s+year))",
                    job.description,
                    re.IGNORECASE,
                )
                if sal_match:
                    raw_extracted = sal_match.group(0).strip()
                    s_min, s_max, s_curr = parse_salary(raw_extracted)
                    if s_min is not None or s_max is not None:
                        job.salary_raw = raw_extracted
                        job.salary_min = s_min
                        job.salary_max = s_max
                        job.salary_currency = s_curr

        # Format salary_raw with dual currency display if numeric min/max present
        if job.salary_min is not None or job.salary_max is not None:
            curr = getattr(job, "salary_currency", None) or getattr(job, "currency", "INR") or "INR"
            formatted = format_salary_display(job.salary_min, job.salary_max, currency=curr, salary_raw=job.salary_raw)
            if formatted:
                job.salary_raw = formatted

        # Fallback apply_url to discovery_url if missing
        if not job.apply_url and job.discovery_url:
            job.apply_url = job.discovery_url

        return job

    @classmethod
    def process_jobs(
        cls,
        jobs: list[Job],
        location: str = "all",
        max_days: Optional[int] = 14,
        min_relevance_score: float = 8.0,
        reference_date: Optional[datetime] = None,
        check_liveness: bool = False,
    ) -> tuple[list[Job], list[Job]]:
        """Executes the unified central processing pipeline.

        Returns:
            tuple[actionable_jobs, irrelevant_jobs]:
                actionable_jobs: Deduplicated, scored, prioritized, and geo-filtered jobs ready for DB upsert.
                irrelevant_jobs: Jobs that scored < min_relevance_score, for DB deactivation.
        """
        logger.info(f"[CentralProcessor] Starting processing on {len(jobs)} candidate jobs (location='{location}', max_days={max_days}, check_liveness={check_liveness})")

        # 1. Normalization & Structured Enrichment
        enriched_jobs = [cls.normalize_job_fields(j) for j in jobs]

        # 2. Freshness Evaluation (if max_days configured)
        if max_days and max_days > 0:
            now_utc = reference_date if reference_date is not None else datetime.now(timezone.utc)
            filtered_by_date = []
            for j in enriched_jobs:
                posted_str = j.posted_at
                if not posted_str and isinstance(j.raw_data, dict):
                    posted_str = j.raw_data.get("datePosted") or j.raw_data.get("posted_date")

                if posted_str:
                    try:
                        clean_posted = str(posted_str).replace("Z", "+00:00")
                        # Handle YYYY-MM-DD or full ISO
                        p_dt = datetime.fromisoformat(clean_posted)
                        if p_dt.tzinfo is None:
                            p_dt = p_dt.replace(tzinfo=timezone.utc)
                        age = (now_utc - p_dt).total_seconds() / 86400.0
                        if age > max_days:
                            continue
                    except Exception:
                        pass
                filtered_by_date.append(j)
            enriched_jobs = filtered_by_date

        # 3. Relevance Scoring, Hard Exclusions & Experience Gate
        relevant_jobs = filter_relevant_jobs(enriched_jobs, min_score=min_relevance_score)
        irrelevant_jobs = [j for j in enriched_jobs if j.relevance_score < min_relevance_score]

        # 3b. Minimum Disclosed Compensation Floor Gate (4 LPA minimum for India/INR roles)
        above_floor_jobs = []
        for j in relevant_jobs:
            curr = getattr(j, "salary_currency", "INR") or "INR"
            if curr == "INR" and j.salary_max is not None and j.salary_max > 0:
                max_lpa = j.salary_max / 100_000.0
                if max_lpa < 4.0:
                    logger.info(f"[CentralProcessor] Disclosed salary {max_lpa} LPA for '{j.title}' @ '{j.company}' is below 4.0 LPA floor. Deactivating.")
                    irrelevant_jobs.append(j)
                    continue
            above_floor_jobs.append(j)
        relevant_jobs = above_floor_jobs

        logger.info(f"[CentralProcessor] Relevance & Floor filter: {len(relevant_jobs)} relevant (>= {min_relevance_score} and >= 4 LPA), {len(irrelevant_jobs)} irrelevant.")

        # 4. Cross-Source Semantic Deduplication & Direct ATS Link Promotion
        unique_jobs = deduplicate_jobs(relevant_jobs)
        logger.info(f"[CentralProcessor] Deduplication: {len(relevant_jobs)} -> {len(unique_jobs)} unique postings.")

        # 5. URL Validation, ATS Classification & Optional Liveness Verification
        validated_jobs = validate_job_urls(unique_jobs, check_liveness=check_liveness)

        # 5b. Disqualify roles with missing or unresolvable application URLs
        actionable_url_jobs = []
        for j in validated_jobs:
            has_valid_url = bool(j.apply_url or j.discovery_url)
            if j.apply_type == "MISSING" or not has_valid_url:
                j.relevance_score = -100.0
                irrelevant_jobs.append(j)
            else:
                actionable_url_jobs.append(j)
        validated_jobs = actionable_url_jobs

        # 6. Priority Scoring & Tier Classification
        prioritized_jobs = prioritize_jobs(validated_jobs)

        # 7. Location Bucketing, Foreign Job Disqualification & Quota
        # Exclude non-remote unsponsored foreign jobs
        prioritized_jobs = [j for j in prioritized_jobs if get_location_bucket(j) != "FOREIGN"]

        loc_lower = (location or "all").strip().lower()
        if loc_lower in ("bangalore", "bengaluru", "blr"):
            actionable_jobs = [j for j in prioritized_jobs if get_location_bucket(j) == "BANGALORE"]
        elif loc_lower in ("chennai", "maa"):
            actionable_jobs = [j for j in prioritized_jobs if get_location_bucket(j) == "CHENNAI"]
        elif loc_lower in ("remote_india", "remote", "remote (in)", "remote(in)", "wfh"):
            actionable_jobs = [j for j in prioritized_jobs if get_location_bucket(j) == "REMOTE_INDIA"]
        elif loc_lower in ("abroad", "global", "international"):
            actionable_jobs = [j for j in prioritized_jobs if get_location_bucket(j) == "ABROAD"]
        elif loc_lower in ("other", "hyd", "hyderabad", "pune"):
            actionable_jobs = [j for j in prioritized_jobs if get_location_bucket(j) == "OTHER"]
        else:
            quota_jobs = select_by_location_quota(prioritized_jobs, target_total=100)
            abroad_jobs = [j for j in prioritized_jobs if get_location_bucket(j) == "ABROAD"]
            actionable_jobs = quota_jobs + abroad_jobs

        logger.info(f"[CentralProcessor] Final actionable jobs: {len(actionable_jobs)}")
        return actionable_jobs, irrelevant_jobs
