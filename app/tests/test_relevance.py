import unittest
from models.job import Job
from processing.relevance import calculate_relevance_score, filter_relevant_jobs


class TestRelevanceEngine(unittest.TestCase):
    def test_hard_exclusions(self):
        excluded_titles = [
            "Director of Engineering",
            "Senior Quality Engineer",
            "QA Automation Tester",
            "Test Architect - C#",
            "Consultant | Oracle Cloud Stack Dev",
            "Data Analyst Lead",
            "ML Engineer II",
            "Software Engineering Intern",
            "Okta Solution Engineer",
        ]

        for title in excluded_titles:
            job = Job(
                id="test_id",
                title=title,
                company="Test Co",
                description="We need Python, FastAPI, PostgreSQL and Redis.",
            )
            score, matched = calculate_relevance_score(job)
            self.assertEqual(score, -100.0, f"Title '{title}' should be hard excluded (-100.0)")

    def test_must_have_baseline(self):
        # Has Docker and AWS, but NO Python and NO Backend
        job = Job(
            id="test_2",
            title="Front End React Developer",
            company="Test Co",
            description="Looking for React, Tailwind, Docker, AWS and HTML/CSS.",
        )
        score, matched = calculate_relevance_score(job)
        self.assertEqual(score, 0.0, "Job without Python or Backend should score 0.0")

    def test_high_match_python_backend(self):
        job = Job(
            id="test_3",
            title="Python Backend Engineer",
            company="FastAPI Corp",
            description="Required: Python, FastAPI, PostgreSQL, RabbitMQ, Celery, Redis and Docker.",
        )
        score, matched = calculate_relevance_score(job)
        self.assertGreaterEqual(score, 20.0)
        self.assertIn("Python", matched)
        self.assertIn("FastAPI", matched)
        self.assertIn("PostgreSQL", matched)

    def test_substring_word_boundary_safety(self):
        job = Job(
            id="test_4",
            title="International Software Engineer",
            company="Global Inc",
            description="Developing web apps with Python and MySQL.",
        )
        score, matched = calculate_relevance_score(job)
        # Should NOT be excluded as 'intern' because of word boundaries
        self.assertGreater(score, 0.0)

    def test_filter_relevant_jobs_threshold(self):
        jobs = [
            Job(id="1", title="Python Backend Engineer", company="Co A", description="Python, FastAPI, PostgreSQL"),
            Job(id="2", title="Quality Engineer", company="Co B", description="Python, Selenium, QA"),
            Job(id="3", title="Front End Dev", company="Co C", description="HTML, CSS, React"),
        ]
        relevant = filter_relevant_jobs(jobs, min_score=12.0)
        self.assertEqual(len(relevant), 1)
        self.assertEqual(relevant[0].id, "1")

    def test_syllabus_topics_matching(self):
        job = Job(
            id="syllabus_1",
            title="Backend Engineer",
            company="Modern Cloud Corp",
            description="""
            We are building high scale APIs with Python and FastAPI.
            Must have deep knowledge of JWT, OAuth2, RBAC, System Design, and Rate Limiting.
            Experience with PostgreSQL, DB Indexing, Alembic, and Pydantic is required.
            Should be familiar with Background Tasks, Event Loop, and Model Context Protocol (MCP) agents.
            """,
        )
        score, matched = calculate_relevance_score(job)
        self.assertGreaterEqual(score, 20.0)
        self.assertIn("FastAPI", matched)
        self.assertIn("JWT", matched)
        self.assertIn("OAuth2", matched)
        self.assertIn("RBAC", matched)
        self.assertIn("System Design", matched)
        self.assertIn("Rate Limiting", matched)
        self.assertIn("PostgreSQL", matched)
        self.assertIn("DB Indexing", matched)
        self.assertIn("Alembic", matched)
        self.assertIn("Pydantic", matched)
        self.assertIn("Background Tasks", matched)
        self.assertIn("Event Loop", matched)
        self.assertIn("MCP", matched)


if __name__ == "__main__":
    unittest.main()
