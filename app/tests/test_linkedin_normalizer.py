import unittest
from models.normalizers.linkedin_normalizer import normalize_linkedin_job, normalize_linkedin_jobs


class TestLinkedInNormalizer(unittest.TestCase):
    def test_complete_linkedin_item(self):
        sample_item = {
            "jobId": "4460260022",
            "jobUrl": "https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/4460260022",
            "title": "Senior Backend Engineer – Python",
            "company": "GlobalLogic",
            "location": "Bengaluru, Karnataka, India",
            "postedAt": "2 weeks ago",
            "salary": "₹800,000.00/yr - ₹1,200,000.00/yr",
            "workType": "Full-time",
            "descriptionText": "We are looking for a Senior Backend Engineer (Python) to build and scale FastAPI and Django systems.",
            "descriptionHtml": "<p>We are looking for a <strong>Senior Backend Engineer</strong></p>",
        }

        job = normalize_linkedin_job(sample_item)
        self.assertEqual(job.id, "linkedin_4460260022")
        self.assertEqual(job.title, "Senior Backend Engineer – Python")
        self.assertEqual(job.company, "GlobalLogic")
        self.assertEqual(job.source, "linkedin")
        self.assertEqual(job.location, "Bengaluru, Karnataka, India")
        self.assertEqual(job.salary_raw, "₹800,000.00/yr - ₹1,200,000.00/yr")
        self.assertEqual(job.discovery_url, "https://www.linkedin.com/jobs/view/4460260022")
        self.assertIsNone(job.apply_url)
        self.assertEqual(job.posted_at, "2 weeks ago")
        self.assertIn("FastAPI and Django systems", job.description)

    def test_linkedin_missing_fields_safe(self):
        sparse_item = {
            "title": "Python Developer",
            "company": "Startup Co",
        }

        job = normalize_linkedin_job(sparse_item)
        self.assertTrue(job.id.startswith("linkedin_"))
        self.assertEqual(job.title, "Python Developer")
        self.assertEqual(job.company, "Startup Co")
        self.assertEqual(job.source, "linkedin")
        self.assertIsNone(job.location)
        self.assertIsNone(job.salary_raw)
        self.assertIsNone(job.apply_url)
        self.assertIsNone(job.discovery_url)
        self.assertEqual(job.description, "")

    def test_linkedin_remote_detection(self):
        remote_loc_item = {
            "jobId": "101",
            "title": "Backend Engineer",
            "company": "Tech Corp",
            "location": "Bengaluru, India (Remote)",
        }
        job = normalize_linkedin_job(remote_loc_item)
        self.assertTrue(job.is_remote)

        remote_title_item = {
            "jobId": "102",
            "title": "Remote Senior Python Engineer",
            "company": "Tech Corp",
            "location": "Bengaluru",
        }
        job2 = normalize_linkedin_job(remote_title_item)
        self.assertTrue(job2.is_remote)

    def test_batch_normalization(self):
        items = [
            {"jobId": "1", "title": "Dev A", "company": "Co A"},
            {"jobId": "2", "title": "Dev B", "company": "Co B"},
        ]
        jobs = normalize_linkedin_jobs(items)
        self.assertEqual(len(jobs), 2)
        self.assertEqual(jobs[0].id, "linkedin_1")
        self.assertEqual(jobs[1].id, "linkedin_2")


if __name__ == "__main__":
    unittest.main()
