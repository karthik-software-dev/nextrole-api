import unittest
from datetime import datetime, timezone, timedelta
from models.job import Job
from processing.central_processor import CentralJobProcessor


class TestCentralJobProcessor(unittest.TestCase):
    def setUp(self):
        self.processor = CentralJobProcessor()
        self.ref_date = datetime(2026, 9, 29, 12, 0, 0, tzinfo=timezone.utc)

    def test_central_processor_pipeline_flow(self):
        """Validates that a fresh Python backend role flows through as Tier 1 actionable."""
        fresh_date = (self.ref_date - timedelta(days=2)).isoformat()
        job = Job(
            id="job_test_1",
            title="Senior Python Backend Engineer",
            company="Acme Corp",
            source="greenhouse",
            location="Bangalore",
            is_remote=False,
            posted_at=fresh_date,
            experience_min=2,
            experience_max=4,
            description="Developing backend APIs using Python, FastAPI, and PostgreSQL.",
            apply_url="https://boards.greenhouse.io/acme/jobs/123",
        )

        actionable_jobs, irrelevant_jobs = self.processor.process_jobs(
            jobs=[job],
            location="Bangalore",
            max_days=7,
            min_relevance_score=8.0,
            reference_date=self.ref_date,
        )

        self.assertEqual(len(actionable_jobs), 1)
        self.assertEqual(len(irrelevant_jobs), 0)
        processed = actionable_jobs[0]
        self.assertGreaterEqual(processed.relevance_score, 12.0)
        self.assertIn("TIER", processed.priority_tier)
        self.assertIn("Python", processed.matched_skills)

    def test_central_processor_hard_exclusion(self):
        """Validates that non-backend / excluded roles (e.g. Sales, Frontend only) are rejected."""
        job = Job(
            id="job_test_sales",
            title="Enterprise Sales Manager",
            company="Acme Corp",
            source="workday",
            location="Bangalore",
            posted_at=(self.ref_date - timedelta(days=1)).isoformat(),
            description="Sales quota, B2B enterprise outreach.",
        )

        actionable_jobs, irrelevant_jobs = self.processor.process_jobs(
            jobs=[job],
            location="Bangalore",
            reference_date=self.ref_date,
        )

        self.assertEqual(len(actionable_jobs), 0)
        self.assertEqual(len(irrelevant_jobs), 1)
        self.assertEqual(irrelevant_jobs[0].id, "job_test_sales")

    def test_central_processor_freshness_rejection(self):
        """Validates that roles older than max_days window are filtered out."""
        stale_date = (self.ref_date - timedelta(days=20)).isoformat()
        job = Job(
            id="job_test_stale",
            title="Python Developer",
            company="Acme Corp",
            source="lever",
            location="Bangalore",
            posted_at=stale_date,
            description="Python FastAPI engineer.",
        )

        actionable_jobs, irrelevant_jobs = self.processor.process_jobs(
            jobs=[job],
            location="Bangalore",
            max_days=7,
            reference_date=self.ref_date,
        )

        self.assertEqual(len(actionable_jobs), 0)

    def test_central_processor_experience_ceiling(self):
        """Validates that roles requiring > 5 YOE are rejected as out-of-profile."""
        fresh_date = (self.ref_date - timedelta(days=1)).isoformat()
        job = Job(
            id="job_test_principal",
            title="Principal Python Architect",
            company="Acme Corp",
            source="ashby",
            location="Remote",
            is_remote=True,
            posted_at=fresh_date,
            experience_min=8,
            experience_max=12,
            description="10+ years Python architecture experience.",
        )

        actionable_jobs, irrelevant_jobs = self.processor.process_jobs(
            jobs=[job],
            max_days=7,
            reference_date=self.ref_date,
        )

        self.assertEqual(len(actionable_jobs), 0)
        self.assertEqual(len(irrelevant_jobs), 1)
        self.assertEqual(irrelevant_jobs[0].id, "job_test_principal")

    def test_central_processor_deduplication_and_ats_merge(self):
        """Validates cross-source deduplication preferring ATS source over aggregators."""
        fresh_date = (self.ref_date - timedelta(days=1)).isoformat()
        job_ats = Job(
            id="job_ats",
            title="Python Backend Engineer",
            company="Stripe",
            source="greenhouse",
            apply_type="DIRECT_ATS",
            apply_url="https://boards.greenhouse.io/stripe/jobs/1",
            location="Bangalore",
            posted_at=fresh_date,
            description="Full Greenhouse description with Python, Django, Postgres.",
        )
        job_aggregator = Job(
            id="job_agg",
            title="Python Backend Engineer",
            company="Stripe",
            source="shine",
            apply_type="PLATFORM",
            apply_url="https://www.shine.com/jobs/1",
            location="Bangalore",
            posted_at=fresh_date,
            description="Python backend engineering role at Stripe with Django and PostgreSQL.",
        )

        actionable_jobs, _ = self.processor.process_jobs(
            jobs=[job_ats, job_aggregator],
            location="Bangalore",
            reference_date=self.ref_date,
        )

        self.assertEqual(len(actionable_jobs), 1)
        survivor = actionable_jobs[0]
        self.assertEqual(survivor.apply_type, "DIRECT_ATS")
        self.assertEqual(survivor.duplicate_count, 2)
        self.assertIn("greenhouse", survivor.source)
        self.assertIn("shine", survivor.source)

    def test_central_processor_disclosed_salary_below_floor_filtered(self):
        """Validates that jobs with disclosed salary < 4 LPA are dropped, while >= 4 LPA survive."""
        fresh_date = (self.ref_date - timedelta(days=1)).isoformat()
        job_low = Job(
            id="job_low_sal",
            title="Python Developer",
            company="UnderpaidCo",
            source="indeed",
            location="Bangalore",
            posted_at=fresh_date,
            apply_url="https://indeed.com/viewjob?jk=123",
            salary_min=200000.0,
            salary_max=350000.0,
            salary_currency="INR",
            description="Python and REST APIs developer, 1-2 years experience.",
            experience_min=1,
            experience_max=2,
        )
        job_acceptable = Job(
            id="job_acceptable_sal",
            title="Python Developer",
            company="BaseCo",
            source="indeed",
            location="Bangalore",
            posted_at=fresh_date,
            apply_url="https://indeed.com/viewjob?jk=456",
            salary_min=400000.0,
            salary_max=450000.0,
            salary_currency="INR",
            description="Python and REST APIs developer, 1-2 years experience.",
            experience_min=1,
            experience_max=2,
        )
        actionable_jobs, irrelevant_jobs = self.processor.process_jobs(
            jobs=[job_low, job_acceptable],
            location="Bangalore",
            reference_date=self.ref_date,
        )
        self.assertEqual(len(actionable_jobs), 1)
        self.assertEqual(actionable_jobs[0].id, "job_acceptable_sal")
        self.assertEqual(len(irrelevant_jobs), 1)
        self.assertEqual(irrelevant_jobs[0].id, "job_low_sal")

    def test_central_processor_abroad_preservation_and_unsponsored_foreign_dropped(self):
        """Validates that verified abroad roles (Worldwide Remote / Visa Sponsor) are preserved alongside daily quota."""
        fresh_date = (self.ref_date - timedelta(days=1)).isoformat()
        job_blr = Job(
            id="job_blr",
            title="Python Developer",
            company="BangaloreCo",
            source="indeed",
            location="Bengaluru",
            posted_at=fresh_date,
            apply_url="https://indeed.com/viewjob?jk=1",
            description="Python FastAPI PostgreSQL developer.",
        )
        job_abroad = Job(
            id="job_abroad",
            title="Python Backend Engineer",
            company="GlobalCo",
            source="ashby",
            location="Worldwide Remote",
            posted_at=fresh_date,
            apply_url="https://jobs.ashbyhq.com/globalco/1",
            description="Worldwide remote Python backend engineer with FastAPI and PostgreSQL.",
        )
        job_foreign_unsponsored = Job(
            id="job_foreign_unsponsored",
            title="Python Developer",
            company="LocalNYC",
            source="indeed",
            location="New York, NY",
            posted_at=fresh_date,
            apply_url="https://indeed.com/viewjob?jk=2",
            description="On-site NYC Python developer. US citizens and green card holders only.",
        )
        actionable_jobs, irrelevant_jobs = self.processor.process_jobs(
            jobs=[job_blr, job_abroad, job_foreign_unsponsored],
            location="all",
            reference_date=self.ref_date,
        )
        actionable_ids = {j.id for j in actionable_jobs}
        self.assertIn("job_blr", actionable_ids)
        self.assertIn("job_abroad", actionable_ids)
        self.assertNotIn("job_foreign_unsponsored", actionable_ids)


if __name__ == "__main__":
    unittest.main()
