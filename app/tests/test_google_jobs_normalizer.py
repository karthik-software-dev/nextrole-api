import unittest
from models.normalizers.google_jobs_normalizer import normalize_google_job, normalize_google_jobs


class TestGoogleJobsNormalizer(unittest.TestCase):
    def test_complete_google_job(self):
        sample = {
            "job_title": "Senior Software Engineer, Full Stack",
            "company_name": "Google",
            "apply_link": "https://www.google.com/about/careers/applications/jobs/results/114928826454024902",
            "location": "Bengaluru, Karnataka, India",
            "job_description": "We are seeking a senior backend software engineer with Python and distributed systems.",
            "qualifications": "5 years experience with Python and REST APIs.",
            "responsibilities": "Design and scale critical backend services.",
        }

        job = normalize_google_job(sample)
        self.assertTrue(job.id.startswith("google_"))
        self.assertEqual(job.title, "Senior Software Engineer, Full Stack")
        self.assertEqual(job.company, "Google")
        self.assertEqual(job.source, "google_jobs")
        self.assertEqual(job.location, "Bengaluru, Karnataka, India")
        self.assertFalse(job.is_remote)
        self.assertEqual(job.apply_url, "https://www.google.com/about/careers/applications/jobs/results/114928826454024902")
        self.assertEqual(job.discovery_url, "https://www.google.com/about/careers/applications/jobs/results/114928826454024902")
        self.assertIn("Qualifications:", job.description)
        self.assertIn("Responsibilities:", job.description)

    def test_missing_fields_safe(self):
        sparse = {
            "job_title": "Backend Developer",
        }
        job = normalize_google_job(sparse)
        self.assertTrue(job.id.startswith("google_"))
        self.assertEqual(job.title, "Backend Developer")
        self.assertEqual(job.company, "Unknown Company")
        self.assertIsNone(job.location)
        self.assertIsNone(job.apply_url)
        self.assertIsNone(job.discovery_url)
        self.assertEqual(job.description, "")

    def test_remote_detection(self):
        remote_loc = {
            "job_title": "Backend Engineer",
            "company_name": "Acme",
            "location": "Bengaluru (Remote)",
        }
        job = normalize_google_job(remote_loc)
        self.assertTrue(job.is_remote)

    def test_batch_normalization(self):
        items = [
            {"job_title": "Dev 1", "company_name": "Co 1"},
            {"job_title": "Dev 2", "company_name": "Co 2"},
        ]
        jobs = normalize_google_jobs(items)
        self.assertEqual(len(jobs), 2)
        self.assertEqual(jobs[0].title, "Dev 1")
        self.assertEqual(jobs[1].title, "Dev 2")


if __name__ == "__main__":
    unittest.main()
