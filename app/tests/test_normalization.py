import unittest
from models.job import Job
from models.normalizers.indeed_normalizer import normalize_indeed_job, normalize_indeed_jobs


class TestIndeedNormalizer(unittest.TestCase):
    def test_complete_item_normalization(self):
        sample_raw = {
            "id": "ind_12345",
            "positionName": "Senior Python Backend Engineer",
            "company": "FastAPI Labs",
            "location": "Bengaluru, Karnataka",
            "salary": "₹25,00,000 - ₹35,00,000 a year",
            "description": "Looking for Python, FastAPI and PostgreSQL expert.",
            "url": "https://in.indeed.com/viewjob?jk=ind_12345",
            "externalApplyLink": "https://boards.greenhouse.io/fastapilabs/jobs/12345",
            "postedAt": "2026-09-15",
            "isRemote": True,
        }

        job: Job = normalize_indeed_job(sample_raw)

        self.assertEqual(job.id, "ind_12345")
        self.assertEqual(job.title, "Senior Python Backend Engineer")
        self.assertEqual(job.company, "FastAPI Labs")
        self.assertEqual(job.location, "Bengaluru, Karnataka")
        self.assertTrue(job.is_remote)
        self.assertEqual(job.salary_raw, "₹25,00,000 - ₹35,00,000 a year")
        self.assertEqual(job.apply_url, "https://boards.greenhouse.io/fastapilabs/jobs/12345")
        self.assertEqual(job.discovery_url, "https://in.indeed.com/viewjob?jk=ind_12345")
        self.assertEqual(job.source, "indeed")
        self.assertEqual(job.raw_data, sample_raw)

    def test_sparse_item_normalization(self):
        sample_sparse = {
            "positionName": "Backend Developer",
            "company": "Acme Corp",
            "url": "https://in.indeed.com/viewjob?jk=acme999&from=serp",
        }

        job: Job = normalize_indeed_job(sample_sparse)

        self.assertEqual(job.id, "acme999")
        self.assertEqual(job.title, "Backend Developer")
        self.assertEqual(job.company, "Acme Corp")
        self.assertIsNone(job.location)
        self.assertFalse(job.is_remote)
        self.assertIsNone(job.salary_raw)
        self.assertEqual(job.apply_url, "https://in.indeed.com/viewjob?jk=acme999&from=serp")
        self.assertEqual(job.discovery_url, "https://in.indeed.com/viewjob?jk=acme999&from=serp")

    def test_fallback_id_generation(self):
        sample_no_id = {
            "positionName": "Python Engineer",
            "company": "Stealth AI",
        }

        job: Job = normalize_indeed_job(sample_no_id)
        self.assertTrue(len(job.id) > 0)
        self.assertEqual(job.title, "Python Engineer")
        self.assertEqual(job.company, "Stealth AI")

    def test_batch_normalization(self):
        raw_list = [
            {"positionName": "Role A", "company": "Co A"},
            {"positionName": "Role B", "company": "Co B"},
        ]
        jobs = normalize_indeed_jobs(raw_list)
        self.assertEqual(len(jobs), 2)
        self.assertIsInstance(jobs[0], Job)
        self.assertIsInstance(jobs[1], Job)


if __name__ == "__main__":
    unittest.main()
