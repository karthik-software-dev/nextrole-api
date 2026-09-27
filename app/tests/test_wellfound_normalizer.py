import unittest
from models.normalizers.wellfound_normalizer import normalize_wellfound_job, normalize_wellfound_jobs


class TestWellfoundNormalizer(unittest.TestCase):
    def test_complete_wellfound_item(self):
        sample_item = {
            "jobId": "4144491",
            "title": "Backend Engineer",
            "companyName": "The Product Highway",
            "jobUrl": "https://wellfound.com/jobs/4144491-backend-engineer",
            "compensation": "₹25L – ₹36L",
            "remote": False,
            "locations": ["Bengaluru"],
            "description": "We are looking for a **Python Backend Engineer** using FastAPI and PostgreSQL.",
            "postedAt": "2026-08-06T16:30:37.000Z",
        }

        job = normalize_wellfound_job(sample_item)
        self.assertEqual(job.id, "wellfound_4144491")
        self.assertEqual(job.title, "Backend Engineer")
        self.assertEqual(job.company, "The Product Highway")
        self.assertEqual(job.source, "wellfound")
        self.assertEqual(job.location, "Bengaluru")
        self.assertFalse(job.is_remote)
        self.assertEqual(job.salary_raw, "₹25L – ₹36L")
        self.assertEqual(job.salary_min, 2500000.0)
        self.assertEqual(job.salary_max, 3600000.0)
        self.assertEqual(job.discovery_url, "https://wellfound.com/jobs/4144491-backend-engineer")
        self.assertEqual(job.apply_url, "https://wellfound.com/jobs/4144491-backend-engineer")
        self.assertIn("Python Backend Engineer", job.description)
        self.assertIn("FastAPI and PostgreSQL.", job.description)

    def test_wellfound_missing_fields_safe(self):
        sparse_item = {
            "title": "Software Engineer",
            "companyName": "New Startup",
        }

        job = normalize_wellfound_job(sparse_item)
        self.assertTrue(job.id.startswith("wellfound_"))
        self.assertEqual(job.title, "Software Engineer")
        self.assertEqual(job.company, "New Startup")
        self.assertEqual(job.source, "wellfound")
        self.assertIsNone(job.location)
        self.assertIsNone(job.salary_raw)
        self.assertIsNone(job.discovery_url)
        self.assertIsNone(job.apply_url)
        self.assertEqual(job.description, "")

    def test_wellfound_remote_detection(self):
        remote_bool_item = {
            "jobId": "201",
            "title": "Backend Engineer",
            "companyName": "Zahln",
            "remote": True,
            "locations": ["Bengaluru", "Pune"],
        }
        job = normalize_wellfound_job(remote_bool_item)
        self.assertTrue(job.is_remote)

        remote_title_item = {
            "jobId": "202",
            "title": "Remote Python Engineer",
            "companyName": "Zahln",
            "remote": False,
            "locations": ["Bengaluru"],
        }
        job2 = normalize_wellfound_job(remote_title_item)
        self.assertTrue(job2.is_remote)

    def test_batch_normalization(self):
        items = [
            {"jobId": "1", "title": "Dev A", "companyName": "Co A"},
            {"jobId": "2", "title": "Dev B", "companyName": "Co B"},
        ]
        jobs = normalize_wellfound_jobs(items)
        self.assertEqual(len(jobs), 2)
        self.assertEqual(jobs[0].id, "wellfound_1")
        self.assertEqual(jobs[1].id, "wellfound_2")


if __name__ == "__main__":
    unittest.main()
