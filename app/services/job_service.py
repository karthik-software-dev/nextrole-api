import math
import re
from typing import Any
from sqlalchemy import and_, func, not_, or_, select
from sqlalchemy.orm import Session, selectinload

from datetime import datetime, timedelta, timezone
from schemas.common import PaginatedResponse, PaginationMeta
from schemas.job import (
    FilterCountItem,
    FilterCountsOut,
    JobCompanyOut,
    JobDetailOut,
    JobSourceOut,
    JobSummaryOut,
)
from storage.models.application import Application
from storage.models.company import Company
from storage.models.job import Job
from storage.models.job_source import JobSource
from storage.repositories.job_repository import JobRepository
from processing.prioritization import calculate_match_percentage
from processing.salary_parser import format_salary_display


def sanitize_salary_display(
    salary_raw: str | None,
    salary_min: float | None,
    salary_max: float | None,
    currency: str = "INR",
) -> str | None:
    if salary_min is not None or salary_max is not None:
        formatted = format_salary_display(salary_min, salary_max, currency, salary_raw)
        if formatted:
            return formatted
    if not salary_raw:
        return None
    clean = salary_raw.strip()
    if len(clean) > 45:
        return None
    clean_lower = clean.lower()
    if any(bad in clean_lower for bad in ("about", "description", "summary", "equity", "role", "looking for", "industry")):
        return None
    if not any(c.isdigit() for c in clean):
        return None
    return clean


class JobService:
    """Service handling job search, filtering, pagination, and details."""

    @staticmethod
    def get_jobs(
        session: Session,
        page: int = 1,
        page_size: int = 20,
        location_bucket: str | None = None,
        priority_tier: str | None = None,
        is_remote: bool | None = None,
        work_mode: str | None = None,
        max_exp: int | None = None,
        min_score: float | None = None,
        salary: str | None = None,
        source: str | None = None,
        app_status: str | None = None,
        days: int | None = None,
        search: str | None = None,
        tag: str | None = None,
        active_only: bool = True,
    ) -> PaginatedResponse[JobSummaryOut]:
        """Queries and filters canonical jobs with pagination."""
        page = max(1, page)
        page_size = max(1, min(100, page_size))

        stmt = select(Job).join(Job.company).options(
            selectinload(Job.company),
            selectinload(Job.application),
        )

        if active_only:
            stmt = stmt.where(Job.is_active.is_(True))

        if location_bucket:
            loc_upper = location_bucket.strip().upper()
            if loc_upper in ("REMOTE", "REMOTE_INDIA", "REMOTE (IN)", "REMOTE(IN)"):
                stmt = stmt.where(Job.location_bucket == "REMOTE_INDIA")
            elif loc_upper in ("ABROAD", "GLOBAL", "INTERNATIONAL"):
                stmt = stmt.where(Job.location_bucket == "ABROAD")
            elif loc_upper in ("OTHER", "OTHER_HUBS", "OTHERS"):
                stmt = stmt.where(Job.location_bucket == "OTHER")
            else:
                stmt = stmt.where(Job.location_bucket == loc_upper)

        if work_mode:
            modes = [m.strip().lower() for m in work_mode.split(",") if m.strip()]
            mode_conds = []
            is_hybrid_safe = or_(
                func.coalesce(Job.location, "").ilike("%hybrid%"),
                func.coalesce(Job.title, "").ilike("%hybrid%"),
                func.coalesce(Job.description, "").ilike("%hybrid%"),
            )
            is_abroad_cond = Job.location_bucket == "ABROAD"
            for wm in modes:
                if wm in ("remote", "wfh", "work_from_home"):
                    mode_conds.append(
                        and_(
                            or_(Job.is_remote.is_(True), Job.location_bucket == "REMOTE_INDIA"),
                            not_(is_hybrid_safe),
                            not_(is_abroad_cond),
                        )
                    )
                elif wm in ("office", "wfo", "work_from_office"):
                    mode_conds.append(
                        and_(
                            Job.is_remote.is_(False),
                            Job.location_bucket != "REMOTE_INDIA",
                            not_(is_hybrid_safe),
                            not_(is_abroad_cond),
                        )
                    )
                elif wm == "hybrid":
                    mode_conds.append(is_hybrid_safe)
                elif wm in ("abroad", "relocation"):
                    mode_conds.append(and_(is_abroad_cond, not_(is_hybrid_safe)))
            if mode_conds:
                stmt = stmt.where(or_(*mode_conds))

        if priority_tier:
            p_clean = priority_tier.strip().lower().replace(" ", "").replace("_", "")
            if p_clean in ("tier1", "1"):
                stmt = stmt.where(Job.priority_tier.ilike("%TIER 1%"))
            elif p_clean in ("tier2", "2"):
                stmt = stmt.where(Job.priority_tier.ilike("%TIER 2%"))
            elif p_clean in ("tier3", "3"):
                stmt = stmt.where(Job.priority_tier.ilike("%TIER 3%"))
            else:
                stmt = stmt.where(Job.priority_tier.ilike(f"%{priority_tier}%"))

        if salary and salary.strip().lower() != "all":
            sal_key = salary.strip().lower()
            if sal_key in ("undisclosed", "none", "not_disclosed", "competitive"):
                stmt = stmt.where(Job.salary_min.is_(None), Job.salary_max.is_(None))
            elif sal_key == "4-8":
                stmt = stmt.where(Job.salary_max >= 400000, Job.salary_min <= 800000)
            elif sal_key == "8-15":
                stmt = stmt.where(Job.salary_max >= 800000, Job.salary_min <= 1500000)
            elif sal_key == "15-25":
                stmt = stmt.where(Job.salary_max >= 1500000, Job.salary_min <= 2500000)
            elif sal_key in ("25+", "25plus"):
                stmt = stmt.where(Job.salary_max >= 2500000)

        if is_remote is not None:
            stmt = stmt.where(Job.is_remote.is_(is_remote))

        if max_exp is not None:
            stmt = stmt.where(
                or_(
                    Job.experience_min.is_(None),
                    Job.experience_min <= max_exp,
                )
            )

        if min_score is not None:
            stmt = stmt.where(Job.relevance_score >= min_score)

        if source and source.strip().lower() != "all":
            src_clean = source.strip().lower()
            if src_clean in ("ats", "company_careers", "careers", "direct_ats"):
                stmt = stmt.where(or_(Job.apply_type == "COMPANY_CAREERS", Job.ats_provider.is_not(None)))
            else:
                stmt = stmt.where(
                    or_(
                        Job.sources.any(JobSource.source_name.ilike(f"%{src_clean}%")),
                        Job.ats_provider.ilike(f"%{src_clean}%"),
                    )
                )

        if app_status and app_status.strip().lower() != "all":
            st_clean = app_status.strip().lower()
            if st_clean in ("unapplied", "new", "fresh"):
                stmt = stmt.where(
                    or_(
                        Job.application == None,
                        Job.application.has(Application.status.in_(("discovered", "saved", None))),
                    )
                )
            else:
                stmt = stmt.where(Job.application.has(Application.status.ilike(f"%{st_clean}%")))

        if days is not None and days > 0:
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)
            stmt = stmt.where(Job.first_seen_at >= cutoff)

        if tag:
            stmt = stmt.where(Job.tags.any(tag))

        if search:
            search_clean = f"%{search.strip()}%"
            stmt = stmt.where(
                or_(
                    Job.title.ilike(search_clean),
                    Company.name.ilike(search_clean),
                    Job.description.ilike(search_clean),
                )
            )

        # Count total matching records
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = session.scalar(count_stmt) or 0

        # Sort and paginate
        stmt = stmt.order_by(Job.priority_score.desc(), Job.relevance_score.desc())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)

        db_jobs = session.scalars(stmt).all()

        items = [
            JobSummaryOut(
                id=j.id,
                company_id=j.company_id,
                company_name=j.company.name,
                title=j.title,
                location=j.location,
                city=j.city,
                location_bucket=j.location_bucket,
                is_remote=j.is_remote,
                experience_min=j.experience_min,
                experience_max=j.experience_max,
                experience_raw=j.experience_raw,
                salary_raw=sanitize_salary_display(
                    j.salary_raw,
                    float(j.salary_min) if j.salary_min is not None else None,
                    float(j.salary_max) if j.salary_max is not None else None,
                    j.currency or "INR",
                ),
                salary_min=float(j.salary_min) if j.salary_min is not None else None,
                salary_max=float(j.salary_max) if j.salary_max is not None else None,
                currency=j.currency or "INR",
                canonical_apply_url=j.canonical_apply_url,
                apply_type=j.apply_type,
                ats_provider=j.ats_provider,
                relevance_score=float(j.relevance_score),
                matched_skills=j.matched_skills or [],
                priority_score=float(j.priority_score),
                priority_tier=j.priority_tier,
                match_percentage=calculate_match_percentage(j.priority_score),
                status=j.status,
                application_status=j.application.status if j.application else None,
                source_count=j.source_count,
                is_active=j.is_active,
                tags=j.tags or [],
                description_snippet=re.sub(r"\s+", " ", j.description).strip()[:180] + "..." if j.description else None,
                first_seen_at=j.first_seen_at,
                last_seen_at=j.last_seen_at,
            )
            for j in db_jobs
        ]

        total_pages = math.ceil(total / page_size) if total > 0 else 0

        return PaginatedResponse(
            items=items,
            meta=PaginationMeta(
                total=total,
                page=page,
                page_size=page_size,
                total_pages=total_pages,
            ),
        )

    @staticmethod
    def get_filter_counts(session: Session) -> FilterCountsOut:
        """Computes live counts for work modes, locations, experience, and salary bands."""
        total_active = session.scalar(select(func.count(Job.id)).where(Job.is_active.is_(True))) or 0

        is_hybrid_safe = or_(
            func.coalesce(Job.location, "").ilike("%hybrid%"),
            func.coalesce(Job.title, "").ilike("%hybrid%"),
            func.coalesce(Job.description, "").ilike("%hybrid%"),
        )
        is_abroad_cond = Job.location_bucket == "ABROAD"

        wfo_count = session.scalar(
            select(func.count(Job.id)).where(
                Job.is_active.is_(True),
                Job.is_remote.is_(False),
                Job.location_bucket != "REMOTE_INDIA",
                not_(is_hybrid_safe),
                not_(is_abroad_cond),
            )
        ) or 0
        wfh_count = session.scalar(
            select(func.count(Job.id)).where(
                Job.is_active.is_(True),
                or_(Job.is_remote.is_(True), Job.location_bucket == "REMOTE_INDIA"),
                not_(is_hybrid_safe),
                not_(is_abroad_cond),
            )
        ) or 0
        hybrid_count = session.scalar(
            select(func.count(Job.id)).where(Job.is_active.is_(True), is_hybrid_safe)
        ) or 0
        abroad_count = session.scalar(
            select(func.count(Job.id)).where(Job.is_active.is_(True), is_abroad_cond, not_(is_hybrid_safe))
        ) or 0

        blr_count = session.scalar(select(func.count(Job.id)).where(Job.is_active.is_(True), Job.location_bucket == "BANGALORE")) or 0
        chn_count = session.scalar(select(func.count(Job.id)).where(Job.is_active.is_(True), Job.location_bucket == "CHENNAI")) or 0
        remote_in_count = session.scalar(select(func.count(Job.id)).where(Job.is_active.is_(True), Job.location_bucket == "REMOTE_INDIA")) or 0
        other_count = session.scalar(select(func.count(Job.id)).where(Job.is_active.is_(True), Job.location_bucket == "OTHER")) or 0
        abroad_loc_count = session.scalar(select(func.count(Job.id)).where(Job.is_active.is_(True), Job.location_bucket == "ABROAD")) or 0

        exp_sweet_spot = session.scalar(select(func.count(Job.id)).where(Job.is_active.is_(True), or_(Job.experience_min.is_(None), Job.experience_min <= 2), or_(Job.experience_max.is_(None), Job.experience_max >= 2))) or 0
        exp_0_2 = session.scalar(select(func.count(Job.id)).where(Job.is_active.is_(True), or_(Job.experience_min.is_(None), Job.experience_min <= 2))) or 0
        exp_3_5 = session.scalar(select(func.count(Job.id)).where(Job.is_active.is_(True), Job.experience_min >= 3, Job.experience_min <= 5)) or 0

        sal_4_8 = session.scalar(select(func.count(Job.id)).where(Job.is_active.is_(True), Job.salary_max >= 400000, Job.salary_min <= 800000)) or 0
        sal_8_15 = session.scalar(select(func.count(Job.id)).where(Job.is_active.is_(True), Job.salary_max >= 800000, Job.salary_min <= 1500000)) or 0
        sal_15_25 = session.scalar(select(func.count(Job.id)).where(Job.is_active.is_(True), Job.salary_max >= 1500000, Job.salary_min <= 2500000)) or 0
        sal_25_plus = session.scalar(select(func.count(Job.id)).where(Job.is_active.is_(True), Job.salary_max >= 2500000)) or 0
        sal_undisclosed = session.scalar(select(func.count(Job.id)).where(Job.is_active.is_(True), Job.salary_min.is_(None), Job.salary_max.is_(None))) or 0

        # Priority Tiers
        tier1_count = session.scalar(select(func.count(Job.id)).where(Job.is_active.is_(True), Job.priority_tier.ilike("%TIER 1%"))) or 0
        tier2_count = session.scalar(select(func.count(Job.id)).where(Job.is_active.is_(True), Job.priority_tier.ilike("%TIER 2%"))) or 0
        tier3_count = session.scalar(select(func.count(Job.id)).where(Job.is_active.is_(True), Job.priority_tier.ilike("%TIER 3%"))) or 0

        # Application Tracking Statuses
        unapplied_count = session.scalar(
            select(func.count(Job.id)).outerjoin(Job.application).where(
                Job.is_active.is_(True),
                or_(Application.id.is_(None), Application.status.in_(("discovered", "saved", None)))
            )
        ) or 0
        drafted_count = session.scalar(
            select(func.count(Job.id)).join(Job.application).where(Job.is_active.is_(True), Application.status == "drafted")
        ) or 0
        applied_count = session.scalar(
            select(func.count(Job.id)).join(Job.application).where(Job.is_active.is_(True), Application.status == "applied")
        ) or 0
        interviewing_count = session.scalar(
            select(func.count(Job.id)).join(Job.application).where(Job.is_active.is_(True), Application.status == "interviewing")
        ) or 0

        # Freshness buckets
        now = datetime.now(timezone.utc)
        f_24h = session.scalar(select(func.count(Job.id)).where(Job.is_active.is_(True), Job.first_seen_at >= now - timedelta(days=1))) or 0
        f_3d = session.scalar(select(func.count(Job.id)).where(Job.is_active.is_(True), Job.first_seen_at >= now - timedelta(days=3))) or 0
        f_7d = session.scalar(select(func.count(Job.id)).where(Job.is_active.is_(True), Job.first_seen_at >= now - timedelta(days=7))) or 0
        f_14d = session.scalar(select(func.count(Job.id)).where(Job.is_active.is_(True), Job.first_seen_at >= now - timedelta(days=14))) or 0

        # Sources (Option B: Live counts exactly matching get_jobs query)
        canonical_sources = [
            ("greenhouse", "Greenhouse"),
            ("ashby", "Ashby"),
            ("indeed", "Indeed"),
            ("hirist", "Hirist"),
            ("wellfound", "Wellfound"),
            ("cutshort", "Cutshort"),
            ("workday", "Workday"),
            ("linkedin", "LinkedIn"),
            ("smartrecruiters", "SmartRecruiters"),
            ("apna", "Apna"),
            ("internshala", "Internshala"),
            ("yc", "YC"),
            ("shine", "Shine"),
            ("relocateme", "RelocateMe"),
            ("lever", "Lever"),
            ("naukri", "Naukri"),
            ("remotive", "Remotive"),
            ("wwr", "We Work Remotely"),
        ]
        sources_list = []
        for s_key, s_label in canonical_sources:
            cnt = session.scalar(
                select(func.count(Job.id.distinct()))
                .outerjoin(Job.sources)
                .where(
                    Job.is_active.is_(True),
                    or_(
                        JobSource.source_name.ilike(f"%{s_key}%"),
                        Job.ats_provider.ilike(f"%{s_key}%"),
                    ),
                )
            ) or 0
            if cnt > 0:
                sources_list.append(FilterCountItem(key=s_key, label=s_label, count=cnt))
        sources_list.sort(key=lambda x: x.count, reverse=True)

        return FilterCountsOut(
            total_active=total_active,
            work_modes=[
                FilterCountItem(key="wfo", label="Work from office", count=wfo_count),
                FilterCountItem(key="wfh", label="Work from home", count=wfh_count),
                FilterCountItem(key="hybrid", label="Hybrid", count=hybrid_count),
                FilterCountItem(key="abroad", label="Abroad / Relocation", count=abroad_count),
            ],
            locations=[
                FilterCountItem(key="BANGALORE", label="Bangalore", count=blr_count),
                FilterCountItem(key="CHENNAI", label="Chennai", count=chn_count),
                FilterCountItem(key="REMOTE_INDIA", label="Remote (IN)", count=remote_in_count),
                FilterCountItem(key="OTHER", label="Other Hubs (Pune, Hyd, NCR)", count=other_count),
                FilterCountItem(key="ABROAD", label="Abroad / Expat", count=abroad_loc_count),
            ],
            experience_buckets=[
                FilterCountItem(key="sweet_spot_2yr", label="2 Yrs Sweet Spot (1–3 Yrs)", count=exp_sweet_spot),
                FilterCountItem(key="0-2", label="0–2 Yrs (Entry / SDE-1)", count=exp_0_2),
                FilterCountItem(key="3-5", label="3–5 Yrs (SDE-2)", count=exp_3_5),
            ],
            salary_buckets=[
                FilterCountItem(key="4-8", label="4–8 Lakhs", count=sal_4_8),
                FilterCountItem(key="8-15", label="8–15 Lakhs", count=sal_8_15),
                FilterCountItem(key="15-25", label="15–25 Lakhs", count=sal_15_25),
                FilterCountItem(key="25+", label="25+ Lakhs", count=sal_25_plus),
                FilterCountItem(key="undisclosed", label="Not Disclosed / Competitive", count=sal_undisclosed),
            ],
            tiers=[
                FilterCountItem(key="tier1", label="⭐ Tier 1 (High Priority)", count=tier1_count),
                FilterCountItem(key="tier2", label="⚡ Tier 2 (Solid Match)", count=tier2_count),
                FilterCountItem(key="tier3", label="📌 Tier 3 (Standard)", count=tier3_count),
            ],
            sources=sources_list,
            application_statuses=[
                FilterCountItem(key="unapplied", label="🟢 Not Applied / Fresh", count=unapplied_count),
                FilterCountItem(key="drafted", label="📝 Drafted", count=drafted_count),
                FilterCountItem(key="applied", label="📨 Applied", count=applied_count),
                FilterCountItem(key="interviewing", label="🎯 Interviewing", count=interviewing_count),
            ],
            freshness_buckets=[
                FilterCountItem(key="1", label="⚡ Past 24 Hours", count=f_24h),
                FilterCountItem(key="3", label="📅 Past 3 Days", count=f_3d),
                FilterCountItem(key="7", label="🗓️ Past 7 Days", count=f_7d),
                FilterCountItem(key="14", label="📆 Past 14 Days", count=f_14d),
            ],
        )

    @staticmethod
    def get_job_by_id(session: Session, job_id: int) -> JobDetailOut | None:
        """Fetches complete details for a single job opportunity."""
        stmt = (
            select(Job)
            .where(Job.id == job_id)
            .options(
                selectinload(Job.company),
                selectinload(Job.sources),
                selectinload(Job.application),
            )
        )
        j = session.scalar(stmt)
        if not j:
            return None

        company_out = (
            JobCompanyOut(
                id=j.company.id,
                name=j.company.name,
                normalized_name=j.company.normalized_name,
                website=j.company.website,
                career_url=j.company.career_url,
                ats_provider=j.company.ats_provider,
                is_target=j.company.is_target,
            )
            if j.company
            else None
        )

        sources_out = [
            JobSourceOut(
                id=src.id,
                source_name=src.source_name,
                source_job_id=src.source_job_id,
                discovery_url=src.discovery_url,
                source_apply_url=src.source_apply_url,
                source_posted_at=src.source_posted_at,
                first_seen_at=src.first_seen_at,
                last_seen_at=src.last_seen_at,
            )
            for src in j.sources
        ]

        app_status = j.application.status if j.application else None

        return JobDetailOut(
            id=j.id,
            company_id=j.company_id,
            company_name=j.company.name if j.company else "Unknown",
            title=j.title,
            location=j.location,
            city=j.city,
            location_bucket=j.location_bucket,
            is_remote=j.is_remote,
            experience_min=j.experience_min,
            experience_max=j.experience_max,
            experience_raw=j.experience_raw,
            salary_raw=sanitize_salary_display(
                j.salary_raw,
                float(j.salary_min) if j.salary_min is not None else None,
                float(j.salary_max) if j.salary_max is not None else None,
                j.currency or "INR",
            ),
            salary_min=float(j.salary_min) if j.salary_min is not None else None,
            salary_max=float(j.salary_max) if j.salary_max is not None else None,
            currency=j.currency or "INR",
            canonical_apply_url=j.canonical_apply_url,
            apply_type=j.apply_type,
            ats_provider=j.ats_provider,
            relevance_score=float(j.relevance_score),
            matched_skills=j.matched_skills or [],
            priority_score=float(j.priority_score),
            priority_tier=j.priority_tier,
            match_percentage=calculate_match_percentage(j.priority_score),
            status=j.status,
            source_count=j.source_count,
            is_active=j.is_active,
            tags=j.tags or [],
            first_seen_at=j.first_seen_at,
            last_seen_at=j.last_seen_at,
            description=j.description,
            company=company_out,
            sources=sources_out,
            application_status=app_status,
            metadata_json=j.metadata_json or {},
        )

    @staticmethod
    def deactivate_job(session: Session, job_id: int) -> bool:
        """Soft-deletes a job by marking is_active = False."""
        return JobRepository.deactivate_job(session, job_id)
