import unittest
from models.job import Job
from processing.deduplication import canonicalize_url, deduplicate_jobs, normalize_company, normalize_title


class TestDeduplication(unittest.TestCase):
    def test_canonicalize_url(self):
        dirty_url = "https://ats.rippling.com/rippling/jobs/123?jobSite=Indeed&utm_source=indeed&utm_medium=jobboard"
        clean = canonicalize_url(dirty_url)
        self.assertEqual(clean, "https://ats.rippling.com/rippling/jobs/123")

    def test_normalize_company(self):
        self.assertEqual(normalize_company("Intellicar Telematics Pvt Ltd"), "intellicar")
        self.assertEqual(normalize_company("Instawork Internal"), "instawork")
        self.assertEqual(normalize_company("Bain & Company, Inc."), "bain company")

    def test_normalize_title(self):
        self.assertEqual(
            normalize_title("Senior Associate- Full Stack Engineer(Retail)"),
            "senior associate full stack engineer",
        )
        self.assertEqual(
            normalize_title("Data Development platform engineer"),
            "data development platform engineer",
        )
        self.assertEqual(
            normalize_title("Data Development Platform Engineer"),
            "data development platform engineer",
        )

    def test_deduplicate_jobs_by_url(self):
        j1 = Job(
            id="1",
            title="Backend Engineer",
            company="Acme Corp",
            apply_url="https://jobs.greenhouse.io/acme/123?utm_source=indeed",
            relevance_score=15.0,
            matched_skills=["Python"],
        )
        j2 = Job(
            id="2",
            title="Backend Engineer",
            company="Acme Corp",
            apply_url="https://jobs.greenhouse.io/acme/123?jobSite=Indeed",
            relevance_score=18.0,
            matched_skills=["FastAPI"],
        )

        deduped = deduplicate_jobs([j1, j2])
        self.assertEqual(len(deduped), 1)
        self.assertEqual(deduped[0].duplicate_count, 2)
        self.assertEqual(deduped[0].relevance_score, 18.0)
        self.assertIn("Python", deduped[0].matched_skills)
        self.assertIn("FastAPI", deduped[0].matched_skills)

    def test_deduplicate_jobs_by_semantic_key(self):
        j1 = Job(
            id="1",
            title="Data Development Platform Engineer",
            company="eBay Inc",
            apply_url="https://ebay.com/job1",
            relevance_score=12.0,
        )
        j2 = Job(
            id="2",
            title="Data Development platform engineer",
            company="eBay",
            apply_url="https://ebay.com/job2",
            relevance_score=12.0,
        )

        deduped = deduplicate_jobs([j1, j2])
        self.assertEqual(len(deduped), 1)
        self.assertEqual(deduped[0].duplicate_count, 2)


if __name__ == "__main__":
    unittest.main()
