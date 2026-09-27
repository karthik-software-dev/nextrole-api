import unittest
from models.normalizers.naukri_normalizer import normalize_naukri_job, normalize_naukri_jobs


class TestNaukriNormalizer(unittest.TestCase):
    def test_complete_naukri_item(self):
        sample_item = {
            "jobDetails": {
                "jobId": "170926923028",
                "title": "Backend Engineer",
                "companyDetail": {"name": "Predictive Data Sciences"},
                "locations": [{"label": "Bengaluru"}, {"label": "Hyderabad"}],
                "salaryDetail": {"salaryText": "12-18 Lacs PA"},
                "description": "<p>We're looking for a <strong>Python Backend Engineer</strong> with FastAPI.</p>",
                "staticUrl": "https://www.naukri.com/job-listings-backend-engineer-170926923028",
                "applyRedirectUrl": "https://atomicwork.greenhouse.io/jobs/123",
                "createdDate": "2026-09-17 14:39:52",
                "wfhType": None,
            }
        }

        job = normalize_naukri_job(sample_item)
        self.assertEqual(job.id, "naukri_170926923028")
        self.assertEqual(job.title, "Backend Engineer")
        self.assertEqual(job.company, "Predictive Data Sciences")
        self.assertEqual(job.source, "naukri")
        self.assertIn("Bengaluru", job.location)
        self.assertEqual(job.salary_raw, "12-18 Lacs PA")
        self.assertEqual(job.apply_url, "https://atomicwork.greenhouse.io/jobs/123")
        self.assertEqual(job.discovery_url, "https://www.naukri.com/job-listings-backend-engineer-170926923028")
        self.assertIn("Python Backend Engineer with FastAPI.", job.description)
        self.assertNotIn("<p>", job.description)

    def test_naukri_native_apply_fallback(self):
        sample_native = {
            "jobDetails": {
                "jobId": "999888777",
                "title": "Python Developer",
                "staticCompanyName": "Acme Tech",
                "locations": [{"label": "Bengaluru"}],
                "staticUrl": "https://www.naukri.com/job-listings-python-dev-999888777",
                "salaryDetail": {"salaryText": "Not Disclosed"},
                "applyRedirectUrl": None,
            }
        }

        job = normalize_naukri_job(sample_native)
        self.assertEqual(job.id, "naukri_999888777")
        self.assertEqual(job.apply_url, "https://www.naukri.com/job-listings-python-dev-999888777")
        self.assertEqual(job.discovery_url, "https://www.naukri.com/job-listings-python-dev-999888777")
        self.assertIsNone(job.salary_raw)

    def test_batch_normalization(self):
        items = [
            {"jobDetails": {"jobId": "1", "title": "Dev A"}},
            {"jobDetails": {"jobId": "2", "title": "Dev B"}},
        ]
        jobs = normalize_naukri_jobs(items)
        self.assertEqual(len(jobs), 2)
        self.assertEqual(jobs[0].id, "naukri_1")
        self.assertEqual(jobs[1].id, "naukri_2")


if __name__ == "__main__":
    unittest.main()
