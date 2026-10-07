from datetime import datetime, timezone
import hashlib
from typing import Any
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from models.job import Job as JobDataclass
from processing.salary_parser import parse_salary
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
    def get_latest_sync_timestamp(session: Session) -> datetime | None:
        """Returns the timestamp of the most recently updated job in the database."""
        stmt = select(func.max(Job.updated_at))
        return session.scalar(stmt)

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
        raw_apply_url = job_dc.apply_url or job_dc.discovery_url
        clean_apply_url = canonicalize_url(raw_apply_url) if raw_apply_url else None
        if clean_apply_url and len(clean_apply_url) > 2000:
            clean_apply_url = clean_apply_url[:2000]

        discovery_url = job_dc.discovery_url[:2000] if job_dc.discovery_url else None
        clean_title = clean_job_title(job_dc.title)
        if clean_title and len(clean_title) > 300:
            clean_title = clean_title[:300]

        safe_location = (job_dc.location[:250] + "...") if job_dc.location and len(job_dc.location) > 255 else job_dc.location
        safe_salary_raw = (job_dc.salary_raw[:495] + "...") if job_dc.salary_raw and len(job_dc.salary_raw) > 500 else job_dc.salary_raw
        safe_exp_raw = (job_dc.experience_raw[:250] + "...") if job_dc.experience_raw and len(job_dc.experience_raw) > 255 else job_dc.experience_raw
        safe_source_id = str(job_dc.id)[:255] if job_dc.id else None
        safe_source_name = str(job_dc.source)[:50] if job_dc.source else "UNKNOWN"
        safe_ats_provider = str(job_dc.ats_provider)[:100] if job_dc.ats_provider else None

        if job_dc.salary_min is not None or job_dc.salary_max is not None:
            sal_min, sal_max, sal_currency = job_dc.salary_min, job_dc.salary_max, job_dc.salary_currency
        else:
            sal_min, sal_max, sal_currency = parse_salary(safe_salary_raw)

        if existing_job:
            # Update existing canonical job
            existing_job.source_count += 1
            existing_job.last_seen_at = now
            existing_job.is_active = True  # Reactivate if it was previously inactive

            # Upgrade apply link if incoming has direct ATS link or existing is empty
            if job_dc.apply_type in ("DIRECT_ATS", "COMPANY_CAREERS") and existing_job.apply_type not in ("DIRECT_ATS", "COMPANY_CAREERS"):
                existing_job.canonical_apply_url = clean_apply_url
                existing_job.apply_type = job_dc.apply_type
                existing_job.ats_provider = safe_ats_provider
            elif not existing_job.canonical_apply_url and clean_apply_url:
                existing_job.canonical_apply_url = clean_apply_url

            # Title clean update if current title has raw artifacts
            if clean_title and existing_job.title != clean_title:
                existing_job.title = clean_title
                existing_job.normalized_title = normalize_title(clean_title)[:300]

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
                JobSource.source_name == safe_source_name,
                JobSource.source_job_id == safe_source_id,
            )
            existing_source = session.scalar(source_stmt)
            if existing_source:
                existing_source.last_seen_at = now
            else:
                new_source = JobSource(
                    job_id=existing_job.id,
                    source_name=safe_source_name,
                    source_job_id=safe_source_id,
                    discovery_url=discovery_url,
                    source_apply_url=clean_apply_url,
                    source_posted_at=str(job_dc.posted_at)[:100] if job_dc.posted_at else None,
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
        safe_city = (city[:95] + "...") if city and len(city) > 100 else city

        new_job = Job(
            company_id=company.id,
            title=clean_title,
            normalized_title=normalize_title(clean_title)[:300],
            dedup_hash=dedup_hash,
            location=safe_location,
            city=safe_city,
            location_bucket=loc_bucket[:20] if loc_bucket else "OTHER",
            is_remote=job_dc.is_remote,
            experience_min=job_dc.experience_min,
            experience_max=job_dc.experience_max,
            experience_raw=safe_exp_raw,
            salary_raw=safe_salary_raw,
            salary_min=sal_min,
            salary_max=sal_max,
            currency=sal_currency[:10] if sal_currency else "INR",
            description=job_dc.description,
            canonical_apply_url=clean_apply_url,
            apply_type=job_dc.apply_type[:30] if job_dc.apply_type else "UNKNOWN",
            ats_provider=safe_ats_provider,
            relevance_score=job_dc.relevance_score,
            matched_skills=job_dc.matched_skills,
            priority_score=job_dc.priority_score,
            priority_tier=job_dc.priority_tier[:40] if job_dc.priority_tier else "TIER 3",
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
            source_name=safe_source_name,
            source_job_id=safe_source_id,
            discovery_url=discovery_url,
            source_apply_url=clean_apply_url,
            source_posted_at=str(job_dc.posted_at)[:100] if job_dc.posted_at else None,
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
        remote_jobs = session.scalar(select(func.count(Job.id)).where(Job.is_active.is_(True), Job.is_remote.is_(True), Job.location_bucket.notin_(("ABROAD", "FOREIGN")))) or 0
        abroad_jobs = session.scalar(select(func.count(Job.id)).where(Job.is_active.is_(True), Job.location_bucket.in_(("ABROAD", "FOREIGN")))) or 0
        other_jobs = session.scalar(select(func.count(Job.id)).where(Job.is_active.is_(True), Job.location_bucket == "OTHER")) or 0

        # Group sources: distinguish aggregators and specific ATS scrapers
        raw_sources = session.execute(
            select(JobSource.id, JobSource.source_name, Job.ats_provider)
            .outerjoin(Job, JobSource.job_id == Job.id)
        ).all()
        normalized_counts: dict[str, int] = {}
        for _, s_name, ats_prov in raw_sources:
            norm = (s_name or "").lower()
            if "linkedin" in norm:
                key = "LinkedIn"
            elif "indeed" in norm:
                key = "Indeed"
            elif "naukri" in norm:
                key = "Naukri"
            elif "cutshort" in norm:
                key = "Cutshort"
            elif "hirist" in norm:
                key = "Hirist"
            elif "wellfound" in norm:
                key = "Wellfound"
            elif "shine" in norm:
                key = "Shine"
            elif "timesjobs" in norm:
                key = "TimesJobs"
            elif "internshala" in norm:
                key = "Internshala"
            elif "apna" in norm:
                key = "Apna"
            elif "freshersworld" in norm:
                key = "Freshersworld"
            elif "google" in norm:
                key = "Google Jobs"
            elif norm == "ats" or "direct" in norm or "careers" in norm:
                prov = (ats_prov or "").lower()
                if "smartrecruiters" in prov:
                    key = "SmartRecruiters"
                elif "greenhouse" in prov:
                    key = "Greenhouse"
                elif "workday" in prov:
                    key = "Workday"
                elif "lever" in prov:
                    key = "Lever"
                elif "ashby" in prov:
                    key = "Ashby"
                elif "bamboohr" in prov:
                    key = "BambooHR"
                elif "personio" in prov:
                    key = "Personio"
                elif "recruitee" in prov:
                    key = "Recruitee"
                elif "workable" in prov:
                    key = "Workable"
                elif "teamtailor" in prov:
                    key = "Teamtailor"
                elif "breezy" in prov:
                    key = "Breezy HR"
                elif "keka" in prov:
                    key = "Keka"
                elif "zoho" in prov:
                    key = "Zoho Recruit"
                elif "freshteam" in prov:
                    key = "Freshteam"
                elif "pyjamahr" in prov:
                    key = "PyjamaHR"
                else:
                    key = "Company Careers"
            else:
                key = s_name.strip() if s_name else "Other"
            normalized_counts[key] = normalized_counts.get(key, 0) + 1

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
            "abroad_jobs": abroad_jobs,
            "other_jobs": other_jobs,
            "sources_breakdown": sources_breakdown,
        }
