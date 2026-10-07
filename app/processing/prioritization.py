from models.job import Job

TIER_1_LABEL = "⭐ TIER 1 (HIGH PRIORITY)"
TIER_2_LABEL = "⚡ TIER 2 (SOLID MATCH)"
TIER_3_LABEL = "📌 TIER 3 (STANDARD)"

CORE_FRAMEWORKS = {
    "fastapi", "flask",
    # Title-cased & canonical variants for backward-compatibility
    "Fastapi", "Flask", "FastAPI"
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
    "sydney", "australia", "singapore", "dubai", "uae", "ireland", "dublin",
    "netherlands", "amsterdam", "paris", "france", "emea", "latam", "europe",
    "north america"
]

INDIA_LOCATIONS = [
    "india", "bengaluru", "bangalore", "chennai", "hyderabad",
    "pune", "mumbai", "delhi", "noida", "gurgaon", "gurugram",
    "karnataka", "tamil nadu", "telangana", "maharashtra"
]

GLOBAL_REMOTE_KEYWORDS = [
    "worldwide", "anywhere", "global", "all locations", "remote - any",
    "remote (worldwide)", "remote - worldwide", "remote, anywhere", "work from anywhere"
]

VISA_SPONSOR_KEYWORDS = [
    "visa sponsorship", "sponsorship available", "sponsorship provided",
    "sponsors visa", "visa support", "relocation assistance", "relocation package",
    "relocation support", "relocation provided", "open to relocation",
    "we sponsor visas", "we sponsor work visas", "relocation to"
]


def get_location_bucket(job: Job) -> str:
    """Classifies a job's location into BANGALORE, CHENNAI, REMOTE_INDIA, ABROAD, or FOREIGN.

    Excludes non-remote foreign jobs without visa sponsorship (to prevent ATS auto-rejection),
    while preserving Bangalore, Chennai, Remote (India), and curated Abroad (Global Remote / Visa Sponsored).
    """
    loc = (job.location or "").lower()
    desc = (job.description or "").lower()
    title = (job.title or "").lower()

    is_foreign = any(f in loc for f in FOREIGN_LOCATIONS)
    has_india = any(ind in loc for ind in INDIA_LOCATIONS)
    has_global = any(g in loc for g in GLOBAL_REMOTE_KEYWORDS) or any(g in title for g in GLOBAL_REMOTE_KEYWORDS)
    has_visa_sponsor = any(v in desc or v in title for v in VISA_SPONSOR_KEYWORDS)
    is_remote_flag = bool(getattr(job, "is_remote", False)) or any(r in loc for r in ["remote", "work from home", "wfh", "pan india"])

    is_dedicated_abroad = getattr(job, "source", "") in ("indeed_abroad", "remotive", "jobicy", "wwr", "arbeitnow", "relocateme", "linkedin_abroad")
    is_target_abroad_hub = any(h in loc for h in ["dubai", "uae", "singapore", "emirates"])

    # 1. Abroad / International Qualified:
    # Dedicated abroad sources (Remotive, Indeed Abroad), Worldwide Remote,
    # target international hubs (Dubai, Singapore), or foreign on-site with explicit Visa Sponsorship
    if is_dedicated_abroad or has_global or (is_foreign and (has_visa_sponsor or is_target_abroad_hub)):
        return "ABROAD"

    # 2. Unsponsored Foreign Disqualification:
    # Foreign locations without Indian presence, without worldwide remote, and without visa sponsorship
    if is_foreign and not has_india:
        return "FOREIGN"

    # 3. Bangalore primary bucket (80% target)
    if any(k in loc for k in ["bengaluru", "bangalore", "karnataka"]):
        return "BANGALORE"

    # 4. Chennai primary bucket (15% target)
    if any(k in loc for k in ["chennai", "tamil nadu"]):
        return "CHENNAI"

    # 5. Remote India (5% target)
    if is_remote_flag and (has_india or not is_foreign):
        return "REMOTE_INDIA"

    # 6. Other (On-site jobs in other Indian cities e.g. Pune, Hyderabad, Mumbai, Delhi)
    return "OTHER"


def calculate_match_percentage(priority_score: float) -> int:
    """Normalizes an open priority score into an intuitive 0-100% candidate match score.

    Tier 1 (Priority >= 22.0): 80% to 100% Match (Grade A)
    Tier 2 (Priority 16.0 - 21.9): 65% to 79% Match (Grade B)
    Tier 3 (Priority 8.0 - 15.9): 50% to 64% Match (Grade C)
    Inactive (< 8.0): < 50%
    """
    score = float(priority_score)
    if score >= 22.0:
        return min(100, 80 + int(round(min(20.0, ((score - 22.0) / 23.0) * 20.0))))
    elif score >= 16.0:
        return 65 + int(round(((score - 16.0) / 6.0) * 14.0))
    elif score >= 8.0:
        return 50 + int(round(((score - 8.0) / 8.0) * 14.0))
    else:
        return max(0, int(round((score / 8.0) * 49.0)))


def calculate_priority_score(job: Job) -> tuple[float, str]:
    """Calculates an actionable priority score and assigns a priority tier in V6.

    Combines relevance score with application friction, target stack synergy, location alignment,
    freshness recency, and hiring urgency.

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

    # 2b. Location Alignment Priority Bonus
    if job.location:
        loc_bucket = get_location_bucket(job)
        loc_lower = (job.location or "").lower()
        has_india = any(ind in loc_lower for ind in INDIA_LOCATIONS)
        is_global_remote = any(g in loc_lower for g in GLOBAL_REMOTE_KEYWORDS)

        if loc_bucket == "BANGALORE":
            priority += 3.0
        elif loc_bucket == "CHENNAI":
            priority += 1.5
        elif loc_bucket == "REMOTE_INDIA":
            priority += 2.0
            matched.add("Remote (India)")
        elif loc_bucket == "ABROAD":
            desc = (job.description or "").lower()
            title = (job.title or "").lower()
            is_reloc_source = getattr(job, "source", "") == "relocateme"
            has_visa = is_reloc_source or any(v in desc or v in title for v in VISA_SPONSOR_KEYWORDS) or any(h in loc_lower for h in ["dubai", "uae", "singapore", "emirates"])
            if has_visa:
                priority += 3.0
                matched.add("Visa Sponsor / Relocation")
            else:
                priority += 2.0
                matched.add("Global Remote")
        else:
            # Check if this is an exceptional opportunity in other Indian hubs (Hyderabad, Pune, Mumbai, etc.)
            is_top_opportunity = has_india and (job.relevance_score >= 24.0 or getattr(job, "is_target_company", False))
            if is_top_opportunity:
                priority += 1.5  # Promotes top regional opportunity into Tier 1 contention
            elif is_global_remote:
                priority += 1.0  # Genuine global remote boost
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
    if "Scalable Backend Synergy" in matched:
        priority += 1.5

    # 5. Target SDE-1 / SDE-2 Role Boost
    if "SDE-1/2 Target Role" in matched:
        priority += 1.5

    # 5b. Early-Stage Startup & Founding Team Boost
    # Small startups (5-10, 10-20, 20-50 team sizes) offer high impact, equity, and rapid hiring cycles
    title_lower = (job.title or "").lower()
    raw_data = getattr(job, "raw_data", None) or {}
    company_size = str(raw_data.get("company_size_label") or raw_data.get("company_size") or "").lower()

    is_founding_role = any(f in title_lower for f in [
        "founding engineer", "founding backend", "founding ai", "founding full stack",
        "founding fullstack", "founding developer", "member of technical staff", "mts"
    ])
    is_small_startup_size = any(s in company_size for s in [
        "1-10", "11-50", "1-20", "20-50", "seed", "series a"
    ])

    if is_founding_role:
        priority += 2.0
        matched.add("Founding / Core Team")
    if is_small_startup_size:
        priority += 1.5
        matched.add("Early-Stage Startup (1-50)")

    # 6. Hiring Demand Boost (Company posted multiple active listings for this role)
    if job.duplicate_count > 1:
        priority += 1.0

    # 6b. Freshness Recency Boost (Jobs posted recently get an urgent priority boost)
    posted_str = job.posted_at
    if not posted_str and isinstance(getattr(job, "raw_data", None), dict):
        posted_str = job.raw_data.get("datePosted") or job.raw_data.get("posted_date")

    if posted_str:
        try:
            from datetime import datetime, timezone
            clean_posted = str(posted_str).replace("Z", "+00:00")
            p_dt = datetime.fromisoformat(clean_posted)
            if p_dt.tzinfo is None:
                p_dt = p_dt.replace(tzinfo=timezone.utc)
            now_utc = datetime.now(timezone.utc)
            age_hours = (now_utc - p_dt).total_seconds() / 3600.0

            if 0 <= age_hours <= 24:
                priority += 3.0
                matched.add("Posted < 24h")
            elif 24 < age_hours <= 72:
                priority += 2.0
                matched.add("Posted < 3d")
            elif 72 < age_hours <= 168:
                priority += 1.0
                matched.add("Posted < 7d")
        except Exception:
            pass

    # 6c. Realistic Compensation Alignment (Floor: 4 LPA, Target Sweet Spot: 5-15 LPA)
    if job.salary_min is not None or job.salary_max is not None:
        curr = getattr(job, "salary_currency", "INR") or "INR"
        if curr == "INR":
            sal_max_lpa = (job.salary_max or job.salary_min or 0.0) / 100_000.0
            sal_min_lpa = (job.salary_min or job.salary_max or 0.0) / 100_000.0

            # Below 4 LPA floor penalty if disclosed
            if sal_max_lpa < 4.0:
                priority -= 4.0
                matched.add("Below 4 LPA Floor")
            # Target Sweet Spot: 5 - 15 LPA (High call conversion & realistic market target for 2 yrs exp)
            elif (5.0 <= sal_max_lpa <= 16.0) or (5.0 <= sal_min_lpa <= 15.0):
                priority += 2.5
                matched.add("Target Comp (5-15 LPA)")
            # High comp (> 15 LPA)
            elif sal_max_lpa > 16.0:
                priority += 1.0
                matched.add("High Comp (15+ LPA)")
            # Acceptable baseline: 4 - 5 LPA
            elif 4.0 <= sal_max_lpa < 5.0:
                priority += 0.5
                matched.add("Comp Disclosed (4-5 LPA)")
        elif curr in ("USD", "EUR", "GBP", "AED", "SGD", "CAD", "AUD"):
            priority += 1.5
            matched.add("Comp Disclosed (Global)")

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

    job.matched_skills = list(matched)
    return round(priority, 1), tier


def select_by_location_quota(jobs: list[Job], target_total: int = 100) -> list[Job]:
    """Selects jobs respecting the 80% Bangalore / 15% Chennai / 5% Remote India distribution.
    Excludes non-remote foreign jobs.

    If Chennai or Remote India has fewer qualified jobs than its quota, slots smoothly roll over
    to Bangalore (primary focus).
    """
    valid_jobs = [j for j in jobs if get_location_bucket(j) not in ("FOREIGN", "ABROAD")]
    if len(valid_jobs) <= target_total:
        return valid_jobs

    blr_jobs = [j for j in valid_jobs if get_location_bucket(j) == "BANGALORE"]
    maa_jobs = [j for j in valid_jobs if get_location_bucket(j) == "CHENNAI"]
    remote_jobs = [j for j in valid_jobs if get_location_bucket(j) == "REMOTE_INDIA"]

    target_blr = int(target_total * 0.80)  # 80 jobs (80%)
    target_maa = int(target_total * 0.15)  # 15 jobs (15%)
    target_remote = target_total - target_blr - target_maa  # 5 jobs (5%)

    selected_maa = maa_jobs[:target_maa]
    selected_remote = remote_jobs[:target_remote]

    # Rollover remaining unfilled slots to Bangalore
    remaining_slots = target_total - len(selected_maa) - len(selected_remote)
    selected_blr = blr_jobs[:remaining_slots]

    # If Bangalore still has remaining capacity, backfill from remaining pool
    selected = selected_blr + selected_maa + selected_remote
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
