from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from schemas.application import (
    ApplicationCreateIn,
    ApplicationHistoryOut,
    ApplicationOut,
    ApplicationUpdateIn,
)
from schemas.job import JobSummaryOut
from storage.models.application import Application
from storage.models.application_history import ApplicationHistory
from storage.models.job import Job
from storage.repositories.application_repository import ApplicationRepository


def _to_application_out(app: Application) -> ApplicationOut:
    """Helper to convert an Application ORM instance to ApplicationOut."""
    job_summary = None
    if app.job:
        j = app.job
        job_summary = JobSummaryOut(
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
        )

    history_out = [
        ApplicationHistoryOut(
            id=h.id,
            previous_status=h.previous_status,
            new_status=h.new_status,
            changed_at=h.changed_at,
            note=h.note,
        )
        for h in sorted(app.history, key=lambda x: x.changed_at)
    ]

    return ApplicationOut(
        id=app.id,
        user_id=app.user_id,
        job_id=app.job_id,
        status=app.status,
        applied_at=app.applied_at,
        resume_version=app.resume_version,
        portal_type=app.portal_type,
        notes=app.notes,
        follow_up_date=app.follow_up_date,
        is_active=app.is_active,
        job=job_summary,
        history=history_out,
        created_at=app.created_at,
        updated_at=app.updated_at,
    )


class ApplicationService:
    """Service handling personal application workflows and audit history."""

    @staticmethod
    def create_application(session: Session, data: ApplicationCreateIn) -> ApplicationOut:
        """Tracks an application for a canonical job."""
        job = session.get(Job, data.job_id)
        if not job:
            raise ValueError(f"Job with ID {data.job_id} does not exist.")

        app = ApplicationRepository.record_application(
            session=session,
            user_id=data.user_id,
            job_id=data.job_id,
            resume_version=data.resume_version,
            portal_type=data.portal_type,
            notes=data.notes,
            initial_status=data.initial_status,
        )
        session.commit()
        session.refresh(app)
        return _to_application_out(app)

    @staticmethod
    def update_application(
        session: Session,
        application_id: int,
        data: ApplicationUpdateIn,
    ) -> ApplicationOut | None:
        """Updates an application and appends a transition record to history."""
        app = session.get(Application, application_id)
        if not app:
            return None

        # Update fields
        if data.resume_version is not None:
            app.resume_version = data.resume_version
        if data.portal_type is not None:
            app.portal_type = data.portal_type
        if data.notes is not None:
            app.notes = data.notes
        if data.follow_up_date is not None:
            app.follow_up_date = data.follow_up_date

        # Update status if changed
        if data.status and data.status != app.status:
            ApplicationRepository.update_status(
                session=session,
                application_id=app.id,
                new_status=data.status,
                note=data.note_for_history or data.notes,
            )

        session.commit()
        session.refresh(app)
        return _to_application_out(app)

    @staticmethod
    def get_application_by_id(session: Session, application_id: int) -> ApplicationOut | None:
        """Fetches an application with full history and job details."""
        stmt = (
            select(Application)
            .where(Application.id == application_id)
            .options(
                selectinload(Application.job).selectinload(Job.company),
                selectinload(Application.history),
            )
        )
        app = session.scalar(stmt)
        if not app:
            return None
        return _to_application_out(app)

    @staticmethod
    def list_applications(
        session: Session,
        status: str | None = None,
        user_id: int = 1,
    ) -> list[ApplicationOut]:
        """Lists active applications."""
        stmt = (
            select(Application)
            .where(Application.is_active.is_(True), Application.user_id == user_id)
            .options(
                selectinload(Application.job).selectinload(Job.company),
                selectinload(Application.history),
            )
        )
        if status:
            stmt = stmt.where(Application.status == status)

        stmt = stmt.order_by(Application.updated_at.desc())
        apps = session.scalars(stmt).all()
        return [_to_application_out(a) for a in apps]
