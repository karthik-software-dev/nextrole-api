import unittest

from models.job import Job
from models.normalizers.experience_parser import extract_experience
from processing.relevance import calculate_relevance_score, filter_relevant_jobs


class TestExperienceParserAndFilter(unittest.TestCase):
    def test_extract_experience_ranges(self):
        min_e, max_e, raw_e = extract_experience("Candidate must have 1-3 years of software experience.")
        self.assertEqual(min_e, 1)
        self.assertEqual(max_e, 3)
        self.assertEqual(raw_e, "1-3 Yrs")

        min_e, max_e, raw_e = extract_experience("Requires 2 to 5 Yrs hands-on Python development.")
        self.assertEqual(min_e, 2)
        self.assertEqual(max_e, 5)
        self.assertEqual(raw_e, "2-5 Yrs")

    def test_extract_experience_minimums(self):
        min_e, max_e, raw_e = extract_experience("Requires minimum 2 years of experience with FastAPI.")
        self.assertEqual(min_e, 2)
        self.assertIsNone(max_e)
        self.assertEqual(raw_e, "2+ Yrs")

        min_e, max_e, raw_e = extract_experience("At least 3 yrs of Python backend experience.")
        self.assertEqual(min_e, 3)
        self.assertIsNone(max_e)
        self.assertEqual(raw_e, "3+ Yrs")

        min_e, max_e, raw_e = extract_experience("Must have 5+ years of experience.")
        self.assertEqual(min_e, 5)
        self.assertIsNone(max_e)
        self.assertEqual(raw_e, "5+ Yrs")

    def test_extract_experience_safety_guard(self):
        # Company history numbers should not be treated as candidate experience
        min_e, max_e, raw_e = extract_experience("Founded over 100 years ago in engineering.")
        self.assertIsNone(min_e)
        self.assertIsNone(max_e)

    def test_senior_title_disqualification(self):
        # Overly senior titles should be hard disqualified
        titles = [
            "Staff Software Engineer",
            "Principal Software Engineer",
            "Lead Backend Developer",
            "Tech Lead - Python",
            "Enterprise Architect",
        ]
        for t in titles:
            job = Job(
                id="test_sr",
                title=t,
                company="Test Corp",
                description="Python, FastAPI, Postgres, Microservices",
            )
            score, _ = calculate_relevance_score(job)
            self.assertEqual(score, -100.0, f"Title '{t}' should have been disqualified with -100.0")

    def test_high_experience_disqualification(self):
        # Minimum experience > 4 should be hard disqualified
        job_high = Job(
            id="test_high_exp",
            title="Software Engineer",
            company="Test Corp",
            description="Python, FastAPI, Postgres",
            experience_min=6,
            experience_max=10,
            experience_raw="6-10 Yrs",
        )
        score, _ = calculate_relevance_score(job_high)
        self.assertEqual(score, -100.0, "Role with min experience > 4 should be disqualified")

    def test_sweet_spot_experience_bonus(self):
        # 1 to 5 years should receive sweet spot bonus (+3.0)
        job_sweet = Job(
            id="test_sweet_exp",
            title="Backend Developer",
            company="Test Corp",
            description="Python, FastAPI, Postgres, Microservices",
            experience_min=2,
            experience_max=4,
            experience_raw="2-4 Yrs",
        )
        score, skills = calculate_relevance_score(job_sweet)
        self.assertGreaterEqual(score, 12.0)
        self.assertIn("Sweet-Spot Exp (1-5 Yrs)", skills)

    def test_sde_title_bonus(self):
        # SDE-2 title should receive target role bonus (+2.0)
        job_sde = Job(
            id="test_sde2",
            title="SDE-2 Backend Engineer",
            company="Test Corp",
            description="Python, FastAPI, Postgres, Microservices",
            experience_min=2,
            experience_max=4,
        )
        score, skills = calculate_relevance_score(job_sde)
        self.assertIn("SDE-1/2 Target Role", skills)


if __name__ == "__main__":
    unittest.main()
