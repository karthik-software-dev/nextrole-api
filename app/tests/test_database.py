import unittest
from sqlalchemy import select, text

from models.job import Job as JobDataclass
from storage.database import engine, get_db, init_db
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

    def setUp(self):
        """Cleans tables before each test to ensure isolation."""
        with engine.begin() as conn:
            conn.execute(text("TRUNCATE TABLE applications, application_history, job_sources, jobs, companies CASCADE;"))

    def test_company_normalization_and_deduplication(self):
        """Tests that varied company representations resolve to a single normalized entity."""
        with get_db() as session:
            co1 = CompanyRepository.get_or_create_company(session, "Razorpay Pvt Ltd")
            co2 = CompanyRepository.get_or_create_company(session, "Razorpay Inc.")
            co3 = CompanyRepository.get_or_create_company(session, "Razorpay")

            self.assertEqual(co1.id, co2.id)
            self.assertEqual(co1.id, co3.id)
            self.assertEqual(co1.normalized_name, "razorpay")

            # Check database row count
            total_companies = session.scalar(select(Company))
            self.assertIsNotNone(total_companies)

    def test_job_upsert_and_cross_source_deduplication(self):
        """Tests that multiple sources (Indeed + ATS) for the same job resolve to 1 canonical Job."""
        with get_db() as session:
            indeed_job = JobDataclass(
                id="indeed_job_101",
                title="Python Backend Engineer",
                company="ServiceNow Pvt Ltd",
                source="indeed",
                location="Bengaluru, Karnataka",
                apply_url="https://jobs.smartrecruiters.com/ServiceNow/999?utm_source=indeed",
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

            # Sighting 2 from direct ATS with higher score and additional skill
            ats_job = JobDataclass(
                id="ats_servicenow_999",
                title="Python Backend Engineer",
                company="ServiceNow",
                source="ats",
                location="Bengaluru",
                apply_url="https://jobs.smartrecruiters.com/ServiceNow/999",
                apply_type="DIRECT_ATS",
                ats_provider="SmartRecruiters ATS",
                relevance_score=25.0,
                matched_skills=["FastAPI", "Docker", "Redis"],
                priority_score=31.0,
                priority_tier="⭐ TIER 1 (HIGH PRIORITY)",
            )

            job_rec2, is_new2 = JobRepository.upsert_job(session, ats_job)
            self.assertFalse(is_new2)
            self.assertEqual(job_rec1.id, job_rec2.id)
            self.assertEqual(job_rec2.source_count, 2)
            self.assertEqual(float(job_rec2.priority_score), 31.0)
            self.assertEqual(job_rec2.priority_tier, "⭐ TIER 1 (HIGH PRIORITY)")
            self.assertIn("Docker", job_rec2.matched_skills)
            self.assertIn("PostgreSQL", job_rec2.matched_skills)

            # Verify 2 distinct JobSource records attached to this Job
            sources = session.scalars(select(JobSource).where(JobSource.job_id == job_rec2.id)).all()
            self.assertEqual(len(sources), 2)
            source_names = {s.source_name for s in sources}
            self.assertEqual(source_names, {"indeed", "ats"})

    def test_soft_delete_with_is_active(self):
        """Tests that deactivating a job sets is_active=False without deleting data."""
        with get_db() as session:
            job_dc = JobDataclass(
                id="naukri_201",
                title="Backend Developer",
                company="Swiggy",
                source="naukri",
                location="Bengaluru",
                relevance_score=20.0,
                priority_score=23.0,
            )
            job, _ = JobRepository.upsert_job(session, job_dc)
            job_id = job.id

            # Active before deactivation
            active_jobs = JobRepository.get_active_jobs(session)
            self.assertEqual(len(active_jobs), 1)

            # Deactivate (Soft-Delete)
            success = JobRepository.deactivate_job(session, job_id)
            self.assertTrue(success)

            # Excluded from active queries
            active_after = JobRepository.get_active_jobs(session)
            self.assertEqual(len(active_after), 0)

            # Record still preserved in database
            stored_job = session.get(Job, job_id)
            self.assertIsNotNone(stored_job)
            self.assertFalse(stored_job.is_active)

    def test_application_workflow_and_audit_history(self):
        """Tests application creation, status transitions, and audit trail logging."""
        with get_db() as session:
            job_dc = JobDataclass(
                id="ats_uber_1",
                title="Software Engineer II - Backend",
                company="Uber India",
                source="ats",
                location="Bengaluru",
                relevance_score=28.0,
                priority_score=34.0,
            )
            job, _ = JobRepository.upsert_job(session, job_dc)

            # Create application (Status: drafted)
            app = ApplicationRepository.record_application(
                session=session,
                user_id=1,
                job_id=job.id,
                resume_version="resume_python_v4.pdf",
                portal_type="direct_ats",
                notes="Targeting Payments Platform team",
            )
            self.assertEqual(app.status, "drafted")
            self.assertEqual(len(app.history), 1)
            self.assertEqual(app.history[0].new_status, "drafted")

            # Transition to 'applied'
            app_applied = ApplicationRepository.update_status(
                session=session,
                application_id=app.id,
                new_status="applied",
                note="Submitted direct ATS application",
            )
            self.assertEqual(app_applied.status, "applied")
            self.assertIsNotNone(app_applied.applied_at)

            # Transition to 'interviewing'
            app_interview = ApplicationRepository.update_status(
                session=session,
                application_id=app.id,
                new_status="interviewing",
                note="Round 1 Technical Screening scheduled",
            )
            self.assertEqual(app_interview.status, "interviewing")
            self.assertEqual(len(app_interview.history), 3)
            self.assertEqual(app_interview.history[1].new_status, "applied")
            self.assertEqual(app_interview.history[2].new_status, "interviewing")

    def test_location_bucket_queries(self):
        """Tests that active jobs can be filtered by location bucket."""
        with get_db() as session:
            blr_job = JobDataclass(
                id="blr_1",
                title="Python Developer",
                company="PhonePe",
                source="linkedin",
                location="Bengaluru, Karnataka",
                priority_score=30.0,
            )
            maa_job = JobDataclass(
                id="maa_1",
                title="Python Backend Engineer",
                company="Zoho",
                source="ats",
                location="Chennai, Tamil Nadu",
                priority_score=28.0,
            )
            JobRepository.upsert_job(session, blr_job)
            JobRepository.upsert_job(session, maa_job)

            blr_results = JobRepository.get_active_jobs(session, location_bucket="BANGALORE")
            maa_results = JobRepository.get_active_jobs(session, location_bucket="CHENNAI")

            self.assertEqual(len(blr_results), 1)
            self.assertEqual(blr_results[0].company.name, "PhonePe")
            self.assertEqual(len(maa_results), 1)
            self.assertEqual(maa_results[0].company.name, "Zoho")


if __name__ == "__main__":
    unittest.main()
