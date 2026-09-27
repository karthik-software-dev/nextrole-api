from models.job import Job

TIER_1_LABEL = "⭐ TIER 1 (HIGH PRIORITY)"
TIER_2_LABEL = "⚡ TIER 2 (SOLID MATCH)"
TIER_3_LABEL = "📌 TIER 3 (STANDARD)"

CORE_FRAMEWORKS = {
    "fastapi", "flask", "django", "django rest framework", "drf",
    # Title-cased & canonical variants for backward-compatibility
    "Fastapi", "Flask", "Django", "Django Rest Framework", "Drf", "FastAPI"
}

CORE_DATABASES = {
    "postgresql", "postgres", "sqlalchemy", "mysql", "sqlite", "sql", "database",
    "database design", "query optimization", "orm", "db design", "db indexing",
    "indexing", "alembic", "pydantic", "redis", "mongodb", "pgvector", "caching",
    # Title-cased & canonical variants for backward-compatibility
    "Postgresql", "Postgres", "Sqlalchemy", "Mysql", "Sql", "Database",
    "Database Design", "Query Optimization", "Orm", "PostgreSQL", "SQLAlchemy",
    "DB Design", "DB Indexing", "Alembic", "Pydantic", "Redis", "pgvector"
}

FOREIGN_LOCATIONS = [
    "london", "united kingdom", "uk",
    "new york", "ny", "united states", "usa", "san francisco", "california",
    "seattle", "washington", "toronto", "canada", "berlin", "germany",
    "sydney", "australia", "singapore", "dubai", "uae"
]


def get_location_bucket(job: Job) -> str:
    """Classifies a job's location into BANGALORE, CHENNAI, OTHER, or FOREIGN."""
    loc = (job.location or "").lower()

    # Check for non-remote foreign location
    if not job.is_remote:
        is_foreign = any(f in loc for f in FOREIGN_LOCATIONS)
        has_india = any(
            ind in loc
            for ind in [
                "india", "bengaluru", "bangalore", "chennai", "hyderabad",
                "pune", "mumbai", "delhi", "noida", "gurgaon", "karnataka", "tamil nadu"
            ]
        )
        if is_foreign and not has_india:
            return "FOREIGN"

    if any(k in loc for k in ["bengaluru", "bangalore", "karnataka"]):
        return "BANGALORE"
    elif any(k in loc for k in ["chennai", "tamil nadu"]):
        return "CHENNAI"
    else:
        return "OTHER"


def calculate_priority_score(job: Job) -> tuple[float, str]:
    """Calculates an actionable priority score and assigns a priority tier in V6.

    Combines relevance score with application friction, target stack synergy, location alignment, and hiring urgency.

    Returns:
        tuple[float, str]: (priority_score, priority_tier)
    """
    priority = job.relevance_score
    matched = set(job.matched_skills)
    matched_lower = {s.lower() for s in job.matched_skills}

    # 1. Application Actionability & Friction
    if job.apply_type == "DIRECT_ATS":
        priority += 3.0
    elif job.apply_type == "COMPANY_CAREERS":
        priority += 2.0
    elif job.apply_type == "AGGREGATOR_REDIRECT":
        priority -= 2.0
    elif job.apply_type == "MISSING":
        priority -= 5.0

    # 2. Seniority & Experience Alignment in Priority
    if "Sweet-Spot Exp (1-3 Yrs)" in matched:
        priority += 2.0
    elif "Sweet-Spot Exp (1-5 Yrs)" in matched:
        priority += 1.0

    if "Senior Exp (4+ Yrs)" in matched:
        priority -= 3.0
    if "Senior Range Penalty" in matched:
        priority -= 4.0
    if "Senior Role Penalty" in matched:
        priority -= 4.0
    if "High Exp Penalty" in matched:
        priority -= 5.0

    # 2b. Location Alignment Priority Bonus (80% Bangalore / 15% Chennai / 5% Other)
    if job.location:
        loc_bucket = get_location_bucket(job)
        if loc_bucket == "BANGALORE":
            priority += 3.0
        elif loc_bucket == "CHENNAI":
            priority += 1.5
        else:
            priority += 0.5

    # 3. Core Framework & Database Synergy (FastAPI/Flask/Django + Postgres/SQLAlchemy)
    fw_lower = {s.lower() for s in CORE_FRAMEWORKS}
    db_lower = {s.lower() for s in CORE_DATABASES}

    has_fw = bool(matched & CORE_FRAMEWORKS) or bool(matched_lower & fw_lower)
    has_db = bool(matched & CORE_DATABASES) or bool(matched_lower & db_lower)

    if has_fw and has_db:
        priority += 2.0
    elif has_fw or has_db:
        priority += 1.0

    # 4. Multi-Stack Synergy Boosts
    if "Full-Stack Synergy" in matched:
        priority += 1.5
    if "AI-Backend Synergy" in matched:
        priority += 1.5

    # 5. Target SDE-1 / SDE-2 Role Boost
    if "SDE-1/2 Target Role" in matched:
        priority += 1.5

    # 6. Hiring Demand Boost (Company posted multiple active listings for this role)
    if job.duplicate_count > 1:
        priority += 1.0

    # 7. Tier Classification
    # Tier 1 requires high technical match + direct apply link + junior/mid seniority
    disqualifying_penalties = {
        "Senior Role Penalty",
        "Senior Range Penalty",
        "Senior Exp (4+ Yrs)",
        "High Exp Penalty",
    }
    if priority >= 22.0 and not (matched & disqualifying_penalties):
        tier = TIER_1_LABEL
    elif priority >= 16.0:
        tier = TIER_2_LABEL
    else:
        tier = TIER_3_LABEL

    return round(priority, 1), tier


def select_by_location_quota(jobs: list[Job], target_total: int = 100) -> list[Job]:
    """Selects jobs respecting the 80% Bangalore / 15% Chennai / 5% Other distribution.
    Excludes non-remote foreign jobs.

    If Chennai or Other has fewer qualified jobs than its quota, slots smoothly roll over
    to Bangalore (primary focus).
    """
    valid_jobs = [j for j in jobs if get_location_bucket(j) != "FOREIGN"]
    if len(valid_jobs) <= target_total:
        return valid_jobs

    blr_jobs = [j for j in valid_jobs if get_location_bucket(j) == "BANGALORE"]
    maa_jobs = [j for j in valid_jobs if get_location_bucket(j) == "CHENNAI"]
    other_jobs = [j for j in valid_jobs if get_location_bucket(j) == "OTHER"]

    target_blr = int(target_total * 0.80)  # 80 jobs (80%)
    target_maa = int(target_total * 0.15)  # 15 jobs (15%)
    target_other = target_total - target_blr - target_maa  # 5 jobs (5%)

    selected_maa = maa_jobs[:target_maa]
    selected_other = other_jobs[:target_other]

    # Rollover remaining unfilled slots to Bangalore
    remaining_slots = target_total - len(selected_maa) - len(selected_other)
    selected_blr = blr_jobs[:remaining_slots]

    # If Bangalore still has remaining capacity, backfill from remaining pool
    selected = selected_blr + selected_maa + selected_other
    if len(selected) < target_total:
        used_ids = {j.id for j in selected}
        remaining_pool = [j for j in valid_jobs if j.id not in used_ids]
        selected.extend(remaining_pool[: target_total - len(selected)])

    selected.sort(
        key=lambda j: (j.priority_score, j.relevance_score),
        reverse=True,
    )
    return selected


def prioritize_jobs(jobs: list[Job], target_total: int | None = None) -> list[Job]:
    """Calculates priority scores, assigns tiers, and orders jobs for maximum actionability."""
    for job in jobs:
        p_score, tier = calculate_priority_score(job)
        job.priority_score = p_score
        job.priority_tier = tier

    jobs.sort(
        key=lambda j: (j.priority_score, j.relevance_score),
        reverse=True,
    )

    if target_total and target_total > 0:
        return select_by_location_quota(jobs, target_total=target_total)

    return jobs
