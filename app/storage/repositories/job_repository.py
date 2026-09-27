from datetime import datetime, timezone
import hashlib
from typing import Any
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from models.job import Job as JobDataclass
from models.normalizers import parse_salary
from processing.deduplication import (
    canonicalize_url,
    clean_job_title,
    normalize_company,
    normalize_title,
)
from processing.prioritization import get_location_bucket
from storage.models.company import Company
from storage.models.job import Job
from storage.models.job_source import JobSource
from storage.repositories.company_repository import CompanyRepository


def compute_dedup_hash(job: JobDataclass) -> str:
    """Computes a deterministic 64-char SHA-256 deduplication hash for a job opportunity."""
    canon_apply = canonicalize_url(job.apply_url or job.discovery_url)

    # 1. Direct verified apply link is the strongest requisition identifier
    if canon_apply and job.apply_type in ("DIRECT_ATS", "COMPANY_CAREERS"):
        key = f"url:{canon_apply.lower().strip()}"
        return hashlib.sha256(key.encode("utf-8")).hexdigest()

    # 2. Semantic fallback: normalized company + normalized title
    norm_co = normalize_company(job.company) or "unknown"
    norm_title = normalize_title(job.title) or "unknown"
    key = f"semantic:{norm_co}::{norm_title}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def extract_city(location: str | None) -> str | None:
    """Extracts prominent city from raw location string."""
    if not location:
        return None
    loc_lower = location.lower()
    if any(k in loc_lower for k in ["bengaluru", "bangalore"]):
        return "Bengaluru"
    if any(k in loc_lower for k in ["chennai", "madras"]):
        return "Chennai"
    if any(k in loc_lower for k in ["hyderabad"]):
        return "Hyderabad"
    if any(k in loc_lower for k in ["pune"]):
        return "Pune"
    if any(k in loc_lower for k in ["gurgaon", "gurugram", "noida", "delhi"]):
        return "Delhi NCR"
    parts = [p.strip() for p in location.split(",") if p.strip()]
    return parts[0] if parts else None


class JobRepository:
    """Data access repository for canonical Jobs and JobSources."""

    @staticmethod
    def upsert_job(session: Session, job_dc: JobDataclass) -> tuple[Job, bool]:
        """Upserts a canonical job and its source posting.

        Returns:
            tuple[Job, bool]: (job, is_new_record)
        """
        dedup_hash = compute_dedup_hash(job_dc)

        # 1. Resolve Company
        company = CompanyRepository.get_or_create_company(
            session=session,
            name=job_dc.company,
            ats_provider=job_dc.ats_provider,
            career_url=job_dc.apply_url if job_dc.apply_type == "COMPANY_CAREERS" else None,
        )

        # 2. Query for existing canonical job by dedup_hash
        stmt = select(Job).where(Job.dedup_hash == dedup_hash)
        existing_job = session.scalar(stmt)

        now = datetime.now(timezone.utc)
        clean_apply_url = canonicalize_url(job_dc.apply_url or job_dc.discovery_url)
        clean_title = clean_job_title(job_dc.title)

        if job_dc.salary_min is not None or job_dc.salary_max is not None:
            sal_min, sal_max, sal_currency = job_dc.salary_min, job_dc.salary_max, job_dc.salary_currency
        else:
            sal_min, sal_max, sal_currency = parse_salary(job_dc.salary_raw)

        if existing_job:
            # Update existing canonical job
            existing_job.source_count += 1
            existing_job.last_seen_at = now
            existing_job.is_active = True  # Reactivate if it was previously inactive

            # Upgrade apply link if incoming has direct ATS link or existing is empty
            if job_dc.apply_type in ("DIRECT_ATS", "COMPANY_CAREERS") and existing_job.apply_type not in ("DIRECT_ATS", "COMPANY_CAREERS"):
                existing_job.canonical_apply_url = clean_apply_url
                existing_job.apply_type = job_dc.apply_type
                existing_job.ats_provider = job_dc.ats_provider
            elif not existing_job.canonical_apply_url and clean_apply_url:
                existing_job.canonical_apply_url = clean_apply_url

            # Title clean update if current title has raw artifacts
            if clean_title and existing_job.title != clean_title:
                existing_job.title = clean_title
                existing_job.normalized_title = normalize_title(clean_title)

            # Salary numeric backfill if existing is null
            if (existing_job.salary_min is None and existing_job.salary_max is None) and (sal_min is not None or sal_max is not None):
                existing_job.salary_min = sal_min
                existing_job.salary_max = sal_max
                existing_job.currency = sal_currency

            # Keep higher priority scores, authoritatively synchronize relevance score
            if job_dc.priority_score > float(existing_job.priority_score):
                existing_job.priority_score = job_dc.priority_score
                existing_job.priority_tier = job_dc.priority_tier
            existing_job.relevance_score = job_dc.relevance_score
            existing_job.is_active = True

            # Union matched skills
            current_skills = list(existing_job.matched_skills or [])
            for s in job_dc.matched_skills:
                if s not in current_skills:
                    current_skills.append(s)
            existing_job.matched_skills = current_skills

            # Record / Update JobSource
            source_stmt = select(JobSource).where(
                JobSource.job_id == existing_job.id,
                JobSource.source_name == job_dc.source,
                JobSource.source_job_id == job_dc.id,
            )
            existing_source = session.scalar(source_stmt)
            if existing_source:
                existing_source.last_seen_at = now
            else:
                new_source = JobSource(
                    job_id=existing_job.id,
                    source_name=job_dc.source,
                    source_job_id=job_dc.id,
                    discovery_url=job_dc.discovery_url,
                    source_apply_url=clean_apply_url,
                    source_posted_at=job_dc.posted_at,
                    raw_payload=job_dc.raw_data if isinstance(job_dc.raw_data, dict) else {},
                    first_seen_at=now,
                    last_seen_at=now,
                )
                session.add(new_source)

            session.flush()
            session.refresh(existing_job)
            return existing_job, False

        # 3. Create New Canonical Job
        loc_bucket = get_location_bucket(job_dc)
        city = extract_city(job_dc.location)

        new_job = Job(
            company_id=company.id,
            title=clean_title,
            normalized_title=normalize_title(clean_title),
            dedup_hash=dedup_hash,
            location=job_dc.location,
            city=city,
            location_bucket=loc_bucket,
            is_remote=job_dc.is_remote,
            experience_min=job_dc.experience_min,
            experience_max=job_dc.experience_max,
            experience_raw=job_dc.experience_raw,
            salary_raw=job_dc.salary_raw,
            salary_min=sal_min,
            salary_max=sal_max,
            currency=sal_currency,
            description=job_dc.description,
            canonical_apply_url=clean_apply_url,
            apply_type=job_dc.apply_type,
            ats_provider=job_dc.ats_provider,
            relevance_score=job_dc.relevance_score,
            matched_skills=job_dc.matched_skills,
            priority_score=job_dc.priority_score,
            priority_tier=job_dc.priority_tier,
            status="discovered",
            source_count=1,
            is_active=True,
            tags=[],
            metadata_json={},
            first_seen_at=now,
            last_seen_at=now,
        )
        session.add(new_job)
        session.flush()

        # Add initial JobSource
        new_source = JobSource(
            job_id=new_job.id,
            source_name=job_dc.source,
            source_job_id=job_dc.id,
            discovery_url=job_dc.discovery_url,
            source_apply_url=clean_apply_url,
            source_posted_at=job_dc.posted_at,
            raw_payload=job_dc.raw_data if isinstance(job_dc.raw_data, dict) else {},
            first_seen_at=now,
            last_seen_at=now,
        )
        session.add(new_source)
        session.flush()

        return new_job, True

    @staticmethod
    def deactivate_irrelevant_job(session: Session, job_dc: JobDataclass) -> bool:
        """If an irrelevant job already exists in the database, updates its relevance score
        and sets is_active = False. Does NOT insert new irrelevant jobs.

        Returns:
            bool: True if an existing job was found and deactivated, False otherwise.
        """
        dedup_hash = compute_dedup_hash(job_dc)
        stmt = select(Job).where(Job.dedup_hash == dedup_hash)
        existing_job = session.scalar(stmt)

        if existing_job:
            now = datetime.now(timezone.utc)
            existing_job.relevance_score = job_dc.relevance_score
            existing_job.is_active = False
            existing_job.last_seen_at = now
            session.flush()
            return True

        return False

    @staticmethod
    def get_active_jobs(
        session: Session,
        limit: int = 50,
        location_bucket: str | None = None,
        priority_tier: str | None = None,
    ) -> list[Job]:
        """Fetches active, prioritized jobs."""
        stmt = select(Job).where(Job.is_active.is_(True))
        if location_bucket:
            stmt = stmt.where(Job.location_bucket == location_bucket.upper())
        if priority_tier:
            stmt = stmt.where(Job.priority_tier.ilike(f"%{priority_tier}%"))

        stmt = stmt.order_by(Job.priority_score.desc(), Job.relevance_score.desc()).limit(limit)
        return list(session.scalars(stmt).all())

    @staticmethod
    def deactivate_job(session: Session, job_id: int) -> bool:
        """Soft-deactivates a job (marks is_active = False)."""
        job = session.get(Job, job_id)
        if job:
            job.is_active = False
            session.flush()
            return True
        return False

    @staticmethod
    def get_database_stats(session: Session) -> dict[str, Any]:
        """Aggregates high-level metrics from PostgreSQL."""
        total_jobs = session.scalar(select(func.count(Job.id))) or 0
        active_jobs = session.scalar(select(func.count(Job.id)).where(Job.is_active.is_(True))) or 0
        tier1_jobs = session.scalar(select(func.count(Job.id)).where(Job.is_active.is_(True), Job.priority_tier.ilike("%TIER 1%"))) or 0
        tier2_jobs = session.scalar(select(func.count(Job.id)).where(Job.is_active.is_(True), Job.priority_tier.ilike("%TIER 2%"))) or 0
        total_companies = session.scalar(select(func.count(Company.id))) or 0
        total_sources = session.scalar(select(func.count(JobSource.id))) or 0

        blr_jobs = session.scalar(select(func.count(Job.id)).where(Job.is_active.is_(True), Job.location_bucket == "BANGALORE")) or 0
        maa_jobs = session.scalar(select(func.count(Job.id)).where(Job.is_active.is_(True), Job.location_bucket == "CHENNAI")) or 0
        remote_jobs = session.scalar(select(func.count(Job.id)).where(Job.is_active.is_(True), Job.is_remote.is_(True))) or 0
        other_jobs = session.scalar(select(func.count(Job.id)).where(Job.is_active.is_(True), Job.location_bucket == "OTHER")) or 0

        # Group sources
        raw_sources = session.execute(
            select(JobSource.source_name, func.count(JobSource.id))
            .group_by(JobSource.source_name)
        ).all()
        normalized_counts: dict[str, int] = {
            "LinkedIn": 0,
            "Naukri": 0,
            "Indeed": 0,
            "Wellfound": 0,
            "Company Sites": 0,
        }
        for s_name, s_count in raw_sources:
            norm = (s_name or "").lower()
            if "linkedin" in norm:
                normalized_counts["LinkedIn"] += s_count
            elif "naukri" in norm:
                normalized_counts["Naukri"] += s_count
            elif "indeed" in norm:
                normalized_counts["Indeed"] += s_count
            elif "wellfound" in norm:
                normalized_counts["Wellfound"] += s_count
            else:
                normalized_counts["Company Sites"] += s_count

        sources_breakdown = [
            {"name": k, "count": v}
            for k, v in sorted(normalized_counts.items(), key=lambda item: item[1], reverse=True)
            if v > 0
        ]

        return {
            "total_jobs": total_jobs,
            "active_jobs": active_jobs,
            "inactive_jobs": total_jobs - active_jobs,
            "tier1_jobs": tier1_jobs,
            "tier2_jobs": tier2_jobs,
            "total_companies": total_companies,
            "total_sources": total_sources,
            "bangalore_jobs": blr_jobs,
            "chennai_jobs": maa_jobs,
            "remote_jobs": remote_jobs,
            "other_jobs": other_jobs,
            "sources_breakdown": sources_breakdown,
        }
