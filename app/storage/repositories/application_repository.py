from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.orm import Session

from storage.models.application import Application
from storage.models.application_history import ApplicationHistory


class ApplicationRepository:
    """Data access repository for Applications and status audit history."""

    @staticmethod
    def record_application(
        session: Session,
        user_id: int,
        job_id: int,
        resume_version: str | None = None,
        portal_type: str | None = None,
        notes: str | None = None,
        initial_status: str = "drafted",
    ) -> Application:
        """Creates or retrieves an application and records initial history."""
        stmt = select(Application).where(
            Application.user_id == user_id,
            Application.job_id == job_id,
        )
        app = session.scalar(stmt)
        if app:
            if app.status == "drafted" and initial_status == "applied":
                app.status = "applied"
                app.applied_at = datetime.now(timezone.utc)
                if portal_type:
                    app.portal_type = portal_type
                history = ApplicationHistory(
                    application_id=app.id,
                    previous_status="drafted",
                    new_status="applied",
                    note=notes or "Application submitted (promoted from Saved / Draft)",
                )
                session.add(history)
                session.flush()
            return app

        now = datetime.now(timezone.utc)
        applied_at = now if initial_status == "applied" else None

        app = Application(
            user_id=user_id,
            job_id=job_id,
            status=initial_status,
            applied_at=applied_at,
            resume_version=resume_version,
            portal_type=portal_type,
            notes=notes,
            is_active=True,
            metadata_json={},
        )
        session.add(app)
        session.flush()

        # Record initial status in audit history
        history = ApplicationHistory(
            application_id=app.id,
            previous_status=None,
            new_status=initial_status,
            note=notes or "Initial record created",
        )
        session.add(history)
        session.flush()

        return app

    @staticmethod
    def update_status(
        session: Session,
        application_id: int,
        new_status: str,
        note: str | None = None,
    ) -> Application | None:
        """Updates application status and logs transition in history."""
        app = session.get(Application, application_id)
        if not app:
            return None

        old_status = app.status
        app.status = new_status

        if new_status == "applied" and not app.applied_at:
            app.applied_at = datetime.now(timezone.utc)

        history = ApplicationHistory(
            application_id=app.id,
            previous_status=old_status,
            new_status=new_status,
            note=note,
        )
        session.add(history)
        session.flush()
        session.refresh(app)

        return app

    @staticmethod
    def get_applications(
        session: Session,
        user_id: int | None = None,
        status: str | None = None,
    ) -> list[Application]:
        """Fetches active applications with optional filtering."""
        stmt = select(Application).where(Application.is_active.is_(True))
        if user_id:
            stmt = stmt.where(Application.user_id == user_id)
        if status:
            stmt = stmt.where(Application.status == status)

        stmt = stmt.order_by(Application.created_at.desc())
        return list(session.scalars(stmt).all())

    @staticmethod
    def delete_by_job_id(
        session: Session,
        user_id: int,
        job_id: int,
    ) -> bool:
        """Deletes an application for a specific user and job (e.g. un-saving a draft)."""
        stmt = select(Application).where(
            Application.user_id == user_id,
            Application.job_id == job_id,
        )
        app = session.scalar(stmt)
        if app:
            session.delete(app)
            session.flush()
            return True
        return False
