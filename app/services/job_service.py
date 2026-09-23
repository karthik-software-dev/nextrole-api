import math
from typing import Any
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from schemas.common import PaginatedResponse, PaginationMeta
from schemas.job import (
    JobCompanyOut,
    JobDetailOut,
    JobSourceOut,
    JobSummaryOut,
)
from storage.models.application import Application
from storage.models.company import Company
from storage.models.job import Job
from storage.repositories.job_repository import JobRepository


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
        max_exp: int | None = None,
        min_score: float | None = None,
        search: str | None = None,
        tag: str | None = None,
        active_only: bool = True,
    ) -> PaginatedResponse[JobSummaryOut]:
        """Queries and filters canonical jobs with pagination."""
        page = max(1, page)
        page_size = max(1, min(100, page_size))

        stmt = select(Job).join(Job.company).options(selectinload(Job.company))

        if active_only:
            stmt = stmt.where(Job.is_active.is_(True))

        if location_bucket:
            stmt = stmt.where(Job.location_bucket == location_bucket.upper())

        if priority_tier:
            stmt = stmt.where(Job.priority_tier.ilike(f"%{priority_tier}%"))

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
