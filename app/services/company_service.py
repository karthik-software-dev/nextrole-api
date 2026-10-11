import math
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from schemas.common import PaginatedResponse, PaginationMeta
from schemas.company import CompanyDetailOut, CompanyOut
from schemas.job import JobSummaryOut
from storage.models.company import Company
from storage.models.job import Job


class CompanyService:
    """Service handling company directory queries and profiles."""

    @staticmethod
    def get_companies(
        session: Session,
        page: int = 1,
        page_size: int = 20,
        is_target: bool | None = None,
        search: str | None = None,
        location: str | None = None,
        min_jobs: int | None = None,
    ) -> PaginatedResponse[CompanyOut]:
        """Fetches a paginated directory of companies with open active jobs count."""
        page = max(1, page)
        page_size = max(1, min(100, page_size))

        # Join with jobs to aggregate active vacancies
        active_jobs_sub = (
            select(Job.company_id, func.count(Job.id).label("job_count"))
            .where(Job.is_active.is_(True))
            .group_by(Job.company_id)
            .subquery()
        )

        stmt = (
            select(
                Company,
                func.coalesce(active_jobs_sub.c.job_count, 0).label("active_jobs_count"),
            )
            .outerjoin(active_jobs_sub, Company.id == active_jobs_sub.c.company_id)
            .where(Company.is_active.is_(True))
        )

        if min_jobs is not None and min_jobs > 0:
            stmt = stmt.where(func.coalesce(active_jobs_sub.c.job_count, 0) >= min_jobs)

        from config.target_companies import TARGET_COMPANIES
        target_names_set = {c.name.strip().lower() for c in TARGET_COMPANIES}

        if is_target is not None:
            if is_target:
                stmt = stmt.where(
                    or_(
                        Company.is_target.is_(True),
                        func.lower(Company.name).in_(target_names_set) if target_names_set else False,
                    )
                )
            else:
                stmt = stmt.where(
                    Company.is_target.is_(False),
                    ~func.lower(Company.name).in_(target_names_set) if target_names_set else True,
                )

        if search:
            stmt = stmt.where(Company.name.ilike(f"%{search.strip()}%"))

        if location:
            loc_upper = location.strip().upper()
            if loc_upper == "ABROAD":
                abroad_sub = (
                    select(Job.company_id)
                    .where(Job.is_active.is_(True), Job.location_bucket == "ABROAD")
                    .distinct()
                    .subquery()
                )
                abroad_target_names = [c.name.lower() for c in TARGET_COMPANIES if getattr(c, "category", "india") == "abroad"]
                stmt = stmt.where(
                    or_(
                        Company.id.in_(select(abroad_sub.c.company_id)),
                        func.lower(Company.name).in_(abroad_target_names) if abroad_target_names else False
                    )
                )
            elif loc_upper == "INDIA":
                india_sub = (
                    select(Job.company_id)
                    .where(
                        Job.is_active.is_(True),
                        Job.location_bucket.in_(("BANGALORE", "CHENNAI", "REMOTE_INDIA", "OTHER"))
                    )
                    .distinct()
                    .subquery()
                )
                india_target_names = [c.name.lower() for c in TARGET_COMPANIES if getattr(c, "category", "india") == "india"]
                stmt = stmt.where(
                    or_(
                        Company.id.in_(select(india_sub.c.company_id)),
                        func.lower(Company.name).in_(india_target_names) if india_target_names else False
                    )
                )

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = session.scalar(count_stmt) or 0

        # Order by companies with most active jobs first, then alphabetically
        stmt = stmt.order_by(
            func.coalesce(active_jobs_sub.c.job_count, 0).desc(),
            Company.name.asc(),
        )
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)

        rows = session.execute(stmt).all()

        items = [
            CompanyOut(
                id=co.id,
                name=co.name,
                normalized_name=co.normalized_name,
                website=co.website,
                career_url=co.career_url,
                ats_provider=co.ats_provider,
                is_target=co.is_target or (co.name.strip().lower() in target_names_set),
                is_active=co.is_active,
                active_jobs_count=job_count,
                created_at=co.created_at,
            )
            for co, job_count in rows
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
    def get_company_by_id(session: Session, company_id: int) -> CompanyDetailOut | None:
        """Fetches company profile along with all active open positions."""
        company = session.get(Company, company_id)
        if not company or not company.is_active:
            return None

        # Fetch active open jobs for this company
        jobs_stmt = (
            select(Job)
            .where(Job.company_id == company_id, Job.is_active.is_(True))
            .order_by(Job.priority_score.desc())
        )
        active_jobs = session.scalars(jobs_stmt).all()

        open_jobs_out = [
            JobSummaryOut(
                id=j.id,
                company_id=j.company_id,
                company_name=company.name,
                title=j.title,
                location=j.location,
                city=j.city,
                location_bucket=j.location_bucket,
                is_remote=j.is_remote,
                experience_min=j.experience_min,
                experience_max=j.experience_max,
                experience_raw=j.experience_raw,
                salary_raw=j.salary_raw,
                canonical_apply_url=j.canonical_apply_url,
                apply_type=j.apply_type,
                ats_provider=j.ats_provider,
                relevance_score=float(j.relevance_score),
                matched_skills=j.matched_skills or [],
                priority_score=float(j.priority_score),
                priority_tier=j.priority_tier,
                status=j.status,
                source_count=j.source_count,
                is_active=j.is_active,
                tags=j.tags or [],
                first_seen_at=j.first_seen_at,
                last_seen_at=j.last_seen_at,
            )
            for j in active_jobs
        ]

        return CompanyDetailOut(
            id=company.id,
            name=company.name,
            normalized_name=company.normalized_name,
            website=company.website,
            career_url=company.career_url,
            ats_provider=company.ats_provider,
            is_target=company.is_target,
            is_active=company.is_active,
            active_jobs_count=len(open_jobs_out),
            created_at=company.created_at,
            open_jobs=open_jobs_out,
            metadata_json=company.metadata_json or {},
        )
