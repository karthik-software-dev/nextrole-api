import unittest
from uuid import uuid4
from sqlalchemy import select

from models.job import Job as JobDataclass
from storage.database import get_db, init_db
from storage.models.application import Application
from storage.models.application_history import ApplicationHistory
from storage.models.company import Company
from storage.models.job import Job
from storage.models.job_source import JobSource
from storage.repositories.application_repository import ApplicationRepository
from storage.repositories.company_repository import CompanyRepository
from storage.repositories.job_repository import JobRepository


class TestPostgresDatabase(unittest.TestCase):
    """Automated test suite for PostgreSQL database, models, and repositories."""

    @classmethod
    def setUpClass(cls):
        """Initializes database schema and prepares test connection."""
        success = init_db()
        if not success:
            raise RuntimeError("PostgreSQL database initialization failed. Ensure Postgres is running on port 5432.")

    def test_company_normalization_and_deduplication(self):
        """Tests that varied company representations resolve to a single normalized entity."""
        test_uid = uuid4().hex[:6]
        co_base = f"UniqueTestCo_{test_uid}"
        with get_db() as session:
            co1 = CompanyRepository.get_or_create_company(session, f"{co_base} Pvt Ltd")
            co2 = CompanyRepository.get_or_create_company(session, f"{co_base} Inc.")
            co3 = CompanyRepository.get_or_create_company(session, co_base)

            self.assertEqual(co1.id, co2.id)
            self.assertEqual(co1.id, co3.id)
            self.assertEqual(co1.normalized_name, co_base.lower())

            total_companies = session.scalar(select(Company))
            self.assertIsNotNone(total_companies)

    def test_job_upsert_and_cross_source_deduplication(self):
        """Tests that multiple sources (Indeed + ATS) for the same job resolve to 1 canonical Job."""
        test_uid = uuid4().hex[:6]
        with get_db() as session:
            indeed_job = JobDataclass(
                id=f"test_indeed_{test_uid}",
                title="Python Backend Engineer",
                company=f"TestServiceNow_{test_uid} Pvt Ltd",
                source="indeed",
                location="Bengaluru, Karnataka",
                apply_url=f"https://jobs.smartrecruiters.com/TestServiceNow/{test_uid}?utm_source=indeed",
                apply_type="DIRECT_ATS",
                ats_provider="SmartRecruiters ATS",
                relevance_score=22.0,
                matched_skills=["FastAPI", "PostgreSQL"],
                priority_score=26.0,
                priority_tier="⚡ TIER 2 (SOLID MATCH)",
            )

            job_rec1, is_new1 = JobRepository.upsert_job(session, indeed_job)
            self.assertTrue(is_new1)
            self.assertEqual(job_rec1.source_count, 1)

            ats_job = JobDataclass(
                id=f"test_ats_{test_uid}",
                title="Python Backend Engineer",
                company=f"TestServiceNow_{test_uid}",
                source="ats",
                location="Bengaluru",
                apply_url=f"https://jobs.smartrecruiters.com/TestServiceNow/{test_uid}",
                apply_type="DIRECT_ATS",
                ats_provider="SmartRecruiters ATS",
                relevance_score=25.0,
                matched_skills=["FastAPI", "Docker", "Redis"],
                priority_score=31.0,
                priority_tier="⭐ TIER 1 (HIGH PRIORITY)",
            )

            job_rec2, is_new2 = JobRepository.upsert_job(session, ats_job)
            self.assertFalse(is_new2)  # Merged into existing job
            self.assertEqual(job_rec2.id, job_rec1.id)
            self.assertEqual(job_rec2.source_count, 2)
            self.assertEqual(float(job_rec2.relevance_score), 25.0)
            self.assertEqual(float(job_rec2.priority_score), 31.0)
            self.assertEqual(job_rec2.priority_tier, "⭐ TIER 1 (HIGH PRIORITY)")
            self.assertEqual(job_rec2.canonical_apply_url, f"https://jobs.smartrecruiters.com/TestServiceNow/{test_uid}")
            self.assertIn("Docker", job_rec2.matched_skills)
            self.assertIn("PostgreSQL", job_rec2.matched_skills)

    def test_soft_delete_with_is_active(self):
        """Tests that deactivating a job sets is_active=False without deleting data."""
        test_uid = uuid4().hex[:6]
        with get_db() as session:
            job_dc = JobDataclass(
                id=f"test_naukri_{test_uid}",
                title="Backend Developer",
                company=f"TestSwiggy_{test_uid}",
                source="naukri",
                location="Bengaluru",
                relevance_score=20.0,
                priority_score=23.0,
            )
            job, _ = JobRepository.upsert_job(session, job_dc)
            job_id = job.id

            active_jobs = JobRepository.get_active_jobs(session, limit=500)
            active_ids = [j.id for j in active_jobs]
            self.assertIn(job_id, active_ids)

            success = JobRepository.deactivate_job(session, job_id)
            self.assertTrue(success)

            active_after = JobRepository.get_active_jobs(session, limit=500)
            active_ids_after = [j.id for j in active_after]
            self.assertNotIn(job_id, active_ids_after)

            stored_job = session.get(Job, job_id)
            self.assertIsNotNone(stored_job)
            self.assertFalse(stored_job.is_active)

    def test_application_workflow_and_audit_history(self):
        """Tests application creation, status transitions, and audit trail logging."""
        test_uid = uuid4().hex[:6]
        with get_db() as session:
            job_dc = JobDataclass(
                id=f"test_ats_uber_{test_uid}",
                title="Software Engineer II - Backend",
                company=f"TestUber_{test_uid}",
                source="ats",
                location="Bengaluru",
                relevance_score=28.0,
                priority_score=34.0,
            )
            job, _ = JobRepository.upsert_job(session, job_dc)

            app = ApplicationRepository.record_application(
                session=session,
                user_id=1,
                job_id=job.id,
                resume_version="resume_python_v4.pdf",
                portal_type="direct_ats",
                notes=f"Targeting Payments Platform team {test_uid}",
            )
            self.assertEqual(app.status, "drafted")
            self.assertEqual(len(app.history), 1)
            self.assertEqual(app.history[0].new_status, "drafted")

            app_applied = ApplicationRepository.update_status(
                session=session,
                application_id=app.id,
                new_status="applied",
                note="Submitted direct ATS application",
            )
            self.assertEqual(app_applied.status, "applied")
            self.assertIsNotNone(app_applied.applied_at)

            app_interview = ApplicationRepository.update_status(
                session=session,
                application_id=app.id,
                new_status="interviewing",
                note="Round 1 Technical Screening scheduled",
            )
            self.assertEqual(app_interview.status, "interviewing")

            history = session.scalars(
                select(ApplicationHistory)
                .where(ApplicationHistory.application_id == app.id)
                .order_by(ApplicationHistory.changed_at)
            ).all()
            self.assertEqual(len(history), 3)
            self.assertEqual(history[0].new_status, "drafted")
            self.assertEqual(history[1].new_status, "applied")
            self.assertEqual(history[2].new_status, "interviewing")

    def test_location_bucket_queries(self):
        """Tests that active jobs can be filtered by location bucket."""
        test_uid = uuid4().hex[:6]
        with get_db() as session:
            blr_job = JobDataclass(
                id=f"test_blr_{test_uid}",
                title="Python Developer",
                company=f"TestPhonePe_{test_uid}",
                source="linkedin",
                location="Bengaluru, Karnataka",
                priority_score=30.0,
            )
            maa_job = JobDataclass(
                id=f"test_maa_{test_uid}",
                title="Python Backend Engineer",
                company=f"TestZoho_{test_uid}",
                source="ats",
                location="Chennai, Tamil Nadu",
                priority_score=28.0,
            )
            JobRepository.upsert_job(session, blr_job)
            JobRepository.upsert_job(session, maa_job)

            blr_results = JobRepository.get_active_jobs(session, location_bucket="BANGALORE")
            maa_results = JobRepository.get_active_jobs(session, location_bucket="CHENNAI")

            self.assertTrue(any(f"TestPhonePe_{test_uid}" in j.company.name for j in blr_results))
            self.assertTrue(any(f"TestZoho_{test_uid}" in j.company.name for j in maa_results))


if __name__ == "__main__":
    unittest.main()
