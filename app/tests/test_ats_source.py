import unittest
from models.job import Job
from custom_scraper.ats_normalizer import (
    normalize_smartrecruiters_job,
    normalize_greenhouse_job,
    normalize_ats_jobs,
)
from processing.deduplication import deduplicate_jobs


class TestATSSource(unittest.TestCase):
    def test_smartrecruiters_normalizer(self):
        sample = {
            "id": "744000150304369",
            "name": "Senior Software AIML Engineer",
            "location": {"city": "Hyderabad", "region": "Telangana", "country": "in", "remote": False},
            "releasedDate": "2026-09-18T05:00:00.000Z",
            "jobAd": {
                "sections": {
                    "jobDescription": {"text": "<p>Build production AI backend systems with Python and FastAPI.</p>"},
                    "qualifications": {"text": "5+ years backend experience with Python and REST APIs."},
                }
            },
        }

        job = normalize_smartrecruiters_job(sample, company_name="ServiceNow", company_identifier="ServiceNow")
        self.assertEqual(job.id, "ats_servicenow_744000150304369")
        self.assertEqual(job.title, "Senior Software AIML Engineer")
        self.assertEqual(job.company, "ServiceNow")
        self.assertEqual(job.source, "ats")
        self.assertIn("Hyderabad", job.location)
        self.assertFalse(job.is_remote)
        self.assertEqual(job.apply_url, "https://jobs.smartrecruiters.com/ServiceNow/744000150304369")
        self.assertIn("Build production AI backend systems with Python and FastAPI.", job.description)
        self.assertNotIn("<p>", job.description)

    def test_greenhouse_normalizer(self):
        sample = {
            "id": 4729937005,
            "title": "Backend Platform Engineer",
            "location": {"name": "Bengaluru, India"},
            "absolute_url": "https://job-boards.greenhouse.io/razorpaysoftwareprivatelimited/jobs/4729937005",
            "content": "<p>Looking for a <strong>Senior Python Engineer</strong> for payment pipelines.</p>",
            "updated_at": "2026-09-17T10:00:00Z",
        }

        job = normalize_greenhouse_job(sample, company_name="Razorpay", board_token="razorpaysoftwareprivatelimited")
        self.assertEqual(job.id, "ats_razorpaysoftwareprivatelimited_4729937005")
        self.assertEqual(job.title, "Backend Platform Engineer")
        self.assertEqual(job.company, "Razorpay")
        self.assertEqual(job.source, "ats")
        self.assertEqual(job.location, "Bengaluru, India")
        self.assertEqual(job.apply_url, "https://job-boards.greenhouse.io/razorpaysoftwareprivatelimited/jobs/4729937005")
        self.assertIn("Looking for a Senior Python Engineer for payment pipelines.", job.description)

    def test_deduplication_prefers_ats_official_apply_url(self):
        indeed_job = Job(
            id="indeed_123",
            title="Senior Staff Software Engineer, Moveworks",
            company="ServiceNow",
            source="indeed",
            location="Bengaluru, Karnataka",
            discovery_url="https://in.indeed.com/viewjob?jk=indeed_123",
            apply_url="https://in.indeed.com/apply/redirect/123",
            relevance_score=15.0,
        )

        official_ats_job = Job(
            id="ats_servicenow_744000149796910",
            title="Senior Staff Software Engineer, Moveworks",
            company="ServiceNow",
            source="ats",
            location="Bengaluru, Karnataka",
            discovery_url="https://jobs.smartrecruiters.com/ServiceNow/744000149796910",
            apply_url="https://jobs.smartrecruiters.com/ServiceNow/744000149796910",
            relevance_score=18.0,
        )

        merged = deduplicate_jobs([indeed_job, official_ats_job])
        self.assertEqual(len(merged), 1)
        # Should retain the official SmartRecruiters ATS URL
        self.assertEqual(merged[0].apply_url, "https://jobs.smartrecruiters.com/ServiceNow/744000149796910")
        self.assertIn("indeed", merged[0].source)
        self.assertIn("ats", merged[0].source)
        self.assertEqual(merged[0].duplicate_count, 2)
    def test_ashby_normalizer(self):
        from custom_scraper.ats_normalizer import normalize_ashby_job

        sample = {
            "id": "d3bc1ced-3ce4-4086-a050-555055dbb1ff",
            "title": "Backend Systems Engineer",
            "location": "Bengaluru, India",
            "secondaryLocations": [{"location": "Remote - India"}],
            "isRemote": True,
            "jobUrl": "https://jobs.ashbyhq.com/linear/d3bc1ced-3ce4-4086-a050-555055dbb1ff",
            "descriptionPlain": "Build real-time backend synchronization in Python and distributed systems.",
            "publishedAt": "2026-09-22T18:21:27.232+00:00",
        }

        job = normalize_ashby_job(sample, company_name="Linear", identifier="linear")
        self.assertEqual(job.id, "ats_ashby_linear_d3bc1ced-3ce4-4086-a050-555055dbb1ff")
        self.assertEqual(job.title, "Backend Systems Engineer")
        self.assertEqual(job.company, "Linear")
        self.assertEqual(job.source, "ats")
        self.assertIn("Bengaluru, India", job.location)
        self.assertIn("Remote - India", job.location)
        self.assertTrue(job.is_remote)
        self.assertEqual(job.apply_url, "https://jobs.ashbyhq.com/linear/d3bc1ced-3ce4-4086-a050-555055dbb1ff")
        self.assertEqual(job.ats_provider, "Ashby")
        self.assertEqual(job.apply_type, "DIRECT_ATS")
        self.assertEqual(job.posted_at, "2026-09-22T18:21:27.232+00:00")
        self.assertIn("Build real-time backend synchronization", job.description)

    def test_fetch_ashby_postings_mocked(self):
        from unittest.mock import MagicMock, patch
        from config.target_companies import TargetCompany
        from custom_scraper.ats_source import fetch_ashby_postings

        comp = TargetCompany(
            name="Linear",
            identifier="linear",
            ats_type="ashby",
            career_url="https://jobs.ashbyhq.com/linear",
            location_filter="India",
        )

        mock_resp = MagicMock()
        mock_resp.read.return_value = b'{"jobs": [{"id": "1", "title": "Staff Backend Engineer", "location": "India", "isRemote": true}]}'
        mock_resp.__enter__.return_value = mock_resp
        mock_resp.__exit__.return_value = None

        with patch("urllib.request.urlopen", return_value=mock_resp):
            items = fetch_ashby_postings(comp)
            self.assertEqual(len(items), 1)
            self.assertEqual(items[0]["title"], "Staff Backend Engineer")


if __name__ == "__main__":
    unittest.main()
