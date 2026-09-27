import unittest
from uuid import uuid4
from sqlalchemy import select

from models.job import Job as JobDataclass
from storage.database import get_db, init_db
from storage.models.job import Job
from storage.models.application import Application
from storage.repositories.application_repository import ApplicationRepository
from storage.repositories.job_repository import JobRepository


class TestRelevancePersistenceLifecycle(unittest.TestCase):
    """Automated tests verifying the relevance persistence lifecycle and state transitions."""

    @classmethod
    def setUpClass(cls):
        """Initializes database schema and ensures Postgres connection."""
        success = init_db()
        if not success:
            raise RuntimeError("PostgreSQL database connection failed.")

    def test_existing_relevant_becomes_irrelevant_deactivated(self):
        """Existing relevant job (score=25.0, is_active=True) must be deactivated when re-evaluated as irrelevant."""
        test_uid = uuid4().hex[:6]
        co_name = f"TestCo_Deact_{test_uid}"
        title = "Python Backend Developer"

        with get_db() as session:
            # 1. Create initial relevant job
            job_dc = JobDataclass(
                id=f"job_rel_{test_uid}",
                title=title,
                company=co_name,
                source="indeed",
                location="Bengaluru",
                relevance_score=25.0,
                priority_score=28.0,
            )
            job, is_new = JobRepository.upsert_job(session, job_dc)
            self.assertTrue(is_new)
            self.assertTrue(job.is_active)
            self.assertEqual(float(job.relevance_score), 25.0)
            job_id = job.id

            # 2. Re-evaluate as irrelevant (score = 0.0)
            irrelevant_dc = JobDataclass(
                id=f"job_rel_{test_uid}",
                title=title,
                company=co_name,
                source="indeed",
                location="Bengaluru",
                relevance_score=0.0,
                priority_score=0.0,
            )
            deactivated = JobRepository.deactivate_irrelevant_job(session, irrelevant_dc)
            self.assertTrue(deactivated)

            # 3. Verify in database
            stored = session.get(Job, job_id)
            self.assertIsNotNone(stored)
            self.assertFalse(stored.is_active)
            self.assertEqual(float(stored.relevance_score), 0.0)

    def test_new_irrelevant_job_not_inserted(self):
        """A brand new irrelevant job must NOT be inserted into PostgreSQL."""
        test_uid = uuid4().hex[:6]
        co_name = f"TestCo_NewIrrel_{test_uid}"

        with get_db() as session:
            new_irrelevant_dc = JobDataclass(
                id=f"job_new_irrel_{test_uid}",
                title="Java Enterprise Architect",
                company=co_name,
                source="indeed",
                location="Bengaluru",
                relevance_score=-100.0,
                priority_score=0.0,
            )
            # Must return False and not insert
            deactivated = JobRepository.deactivate_irrelevant_job(session, new_irrelevant_dc)
            self.assertFalse(deactivated)

            # Verify no job exists for this company
            found = session.scalar(select(Job).where(Job.title == "Java Enterprise Architect"))
            # Make sure it's not our newly generated company
            stmt = select(Job).join(Job.company).where(Job.company.has(name=co_name))
            co_job = session.scalar(stmt)
            self.assertIsNone(co_job)

    def test_inactive_job_reactivated_when_relevant(self):
        """A previously inactive job must be cleanly reactivated when it becomes relevant again."""
        test_uid = uuid4().hex[:6]
        co_name = f"TestCo_Reactivate_{test_uid}"
        title = "Senior Python Engineer"

        with get_db() as session:
            # 1. Insert initial job
            job_dc = JobDataclass(
                id=f"job_react_{test_uid}",
                title=title,
                company=co_name,
                source="indeed",
                location="Bengaluru",
                relevance_score=20.0,
                priority_score=22.0,
            )
            job, _ = JobRepository.upsert_job(session, job_dc)
            job_id = job.id

            # 2. Deactivate it
            JobRepository.deactivate_job(session, job_id)
            stored = session.get(Job, job_id)
            self.assertFalse(stored.is_active)

            # 3. Upsert again with relevant score
            relevant_dc = JobDataclass(
                id=f"job_react_{test_uid}",
                title=title,
                company=co_name,
                source="ats",
                location="Bengaluru",
                relevance_score=30.0,
                priority_score=35.0,
            )
            updated_job, is_new = JobRepository.upsert_job(session, relevant_dc)
            self.assertFalse(is_new)
            self.assertEqual(updated_job.id, job_id)
            self.assertTrue(updated_job.is_active)
            self.assertEqual(float(updated_job.relevance_score), 30.0)

    def test_authoritative_score_synchronization(self):
        """Relevance score in database must authoritatively synchronize with current engine score."""
        test_uid = uuid4().hex[:6]
        co_name = f"TestCo_ScoreSync_{test_uid}"
        title = "Backend Developer - Python"

        with get_db() as session:
            # 1. Insert with initial score
            job_dc = JobDataclass(
                id=f"job_sync_{test_uid}",
                title=title,
                company=co_name,
                source="indeed",
                location="Bengaluru",
                relevance_score=28.0,
                priority_score=30.0,
            )
            job, _ = JobRepository.upsert_job(session, job_dc)
            job_id = job.id
            self.assertEqual(float(job.relevance_score), 28.0)

            # 2. Update with recalculated score (even if lower, e.g. 19.0)
            recalculated_dc = JobDataclass(
                id=f"job_sync_{test_uid}",
                title=title,
                company=co_name,
                source="indeed",
                location="Bengaluru",
                relevance_score=19.0,
                priority_score=22.0,
            )
            updated_job, _ = JobRepository.upsert_job(session, recalculated_dc)
            self.assertEqual(float(updated_job.relevance_score), 19.0)
            self.assertTrue(updated_job.is_active)

    def test_application_preserved_when_job_deactivated(self):
        """User Application record and history must remain intact and retrievable when a job is marked inactive."""
        test_uid = uuid4().hex[:6]
        co_name = f"TestCo_AppPreserve_{test_uid}"

        with get_db() as session:
            # 1. Insert job
            job_dc = JobDataclass(
                id=f"job_app_{test_uid}",
                title="Python Developer",
                company=co_name,
                source="ats",
                location="Bengaluru",
                relevance_score=25.0,
                priority_score=28.0,
            )
            job, _ = JobRepository.upsert_job(session, job_dc)
            job_id = job.id

            # 2. Record application for user #1
            app = ApplicationRepository.record_application(
                session=session,
                user_id=1,
                job_id=job_id,
                resume_version="v2_python.pdf",
                portal_type="Direct ATS",
                notes="Applied via careers portal",
                initial_status="applied",
            )
            app_id = app.id
            session.commit()

            # 3. Deactivate the job
            deactivated = JobRepository.deactivate_job(session, job_id)
            self.assertTrue(deactivated)

            # 4. Verify job is inactive, but application remains intact
            stored_job = session.get(Job, job_id)
            self.assertFalse(stored_job.is_active)

            stored_app = session.get(Application, app_id)
            self.assertIsNotNone(stored_app)
            self.assertEqual(stored_app.status, "applied")
            self.assertEqual(stored_app.job_id, job_id)
            self.assertEqual(stored_app.resume_version, "v2_python.pdf")

    def test_multi_source_dedup_and_source_count_intact(self):
        """Cross-source duplicate arrivals must increment source_count and update timestamps."""
        test_uid = uuid4().hex[:6]
        co_name = f"TestCo_MultiSrc_{test_uid}"
        title = "Software Engineer - Python"

        with get_db() as session:
            # Source 1: Indeed
            job1 = JobDataclass(
                id=f"indeed_{test_uid}",
                title=title,
                company=co_name,
                source="indeed",
                location="Bengaluru",
                relevance_score=24.0,
                priority_score=26.0,
            )
            rec1, is_new1 = JobRepository.upsert_job(session, job1)
            self.assertTrue(is_new1)
            self.assertEqual(rec1.source_count, 1)

            # Source 2: ATS for the same role
            job2 = JobDataclass(
                id=f"ats_{test_uid}",
                title=title,
                company=co_name,
                source="ats",
                location="Bengaluru",
                relevance_score=26.0,
                priority_score=29.0,
            )
            rec2, is_new2 = JobRepository.upsert_job(session, job2)
            self.assertFalse(is_new2)
            self.assertEqual(rec1.id, rec2.id)
            self.assertEqual(rec2.source_count, 2)
            self.assertTrue(rec2.is_active)
