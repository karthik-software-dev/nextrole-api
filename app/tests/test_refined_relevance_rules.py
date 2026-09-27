"""
Regression test suite for refined relevance rules and experience parsing.
Verifies Rules A-E, Unicode dash normalization, the 16 synthetic protection cases,
and the key benchmark regression jobs.
"""

import json
import os
import unittest
from models.job import Job
from models.normalizers.experience_parser import extract_experience
from processing.relevance import calculate_relevance_score

RELEVANCE_THRESHOLD = 8.0


class TestExperienceParserUnicode(unittest.TestCase):
    """Verifies Unicode dash normalization and minimum experience handling."""

    def test_unicode_en_dash_range(self):
        # Unicode \u2013 (en-dash)
        text = "Candidates must have 3\u20135 years of software engineering experience."
        min_exp, max_exp, raw = extract_experience(text)
        self.assertEqual(min_exp, 3)
        self.assertEqual(max_exp, 5)
        self.assertEqual(raw, "3-5 Yrs")

    def test_unicode_em_dash_range(self):
        # Unicode \u2014 (em-dash)
        text = "Requires 2\u20145 years experience in backend systems."
        min_exp, max_exp, raw = extract_experience(text)
        self.assertEqual(min_exp, 2)
        self.assertEqual(max_exp, 5)

    def test_senior_ranges(self):
        # 5-10, 6-9, 8-12
        cases = [
            ("5-10 years of experience", 5, 10),
            ("6\u20139 years of experience", 6, 9),
            ("8\u201412 years of experience", 8, 12),
        ]
        for text, exp_min, exp_max in cases:
            p_min, p_max, _ = extract_experience(text)
            self.assertEqual(p_min, exp_min, f"Failed min for {text}")
            self.assertEqual(p_max, exp_max, f"Failed max for {text}")

    def test_explicit_minimum_and_plus(self):
        cases = [
            ("5+ years of experience", 5, None),
            ("At least 5 years of relevant software development experience", 5, None),
            ("minimum 2 years of experience", 2, None),
        ]
        for text, exp_min, exp_max in cases:
            p_min, p_max, _ = extract_experience(text)
            self.assertEqual(p_min, exp_min, f"Failed min for {text}")
            self.assertEqual(p_max, exp_max, f"Failed max for {text}")


class TestQualityEngineeringRuleC(unittest.TestCase):
    """Verifies Rule C: QE context protection vs genuine QA/SDET role exclusion."""

    def test_protects_qe_context_in_software_role(self):
        # db_job_145 pattern: software/AI engineer in a quality engineering org
        job = Job(
            id="test_qe_protect",
            title="AI Engineer, Agentic Systems (Quality Engineering)",
            company="Palo Alto Networks",
            description=(
                "Build agentic systems, AI orchestration, LLMs, and Python microservices. "
                "Design REST APIs using FastAPI, Docker, and relational databases. "
                "2-3 years software engineering experience."
            ),
            experience_min=2,
            experience_max=3,
        )
        score, _ = calculate_relevance_score(job)
        self.assertGreaterEqual(score, RELEVANCE_THRESHOLD)

    def test_rejects_genuine_qa_and_sdet_titles(self):
        disqualified_titles = [
            "Quality Engineer",
            "QA Engineer",
            "SDET",
            "Software Development Engineer in Test",
            "Test Automation Engineer",
            "QA Automation Engineer",
            "Software Engineer in Test",
        ]
        for title in disqualified_titles:
            job = Job(
                id="test_qa",
                title=title,
                company="TechCorp",
                description="Write automated test cases using Selenium and Cypress with Python. 2 years experience.",
                experience_min=2,
                experience_max=3,
            )
            score, _ = calculate_relevance_score(job)
            self.assertEqual(score, -100.0, f"Expected disqualification for title: {title}")


class TestGenericBackendDetectionRuleE(unittest.TestCase):
    """Verifies Rule E: generic titles are accepted if backed by concrete backend/API evidence."""

    def test_accepts_product_data_gateway_generic_role(self):
        # db_job_195 pattern
        job = Job(
            id="test_generic_gateway",
            title="Software Engineer II - Product Data Gateway",
            company="Tech Corp",
            description=(
                "Build high-throughput data gateway and REST APIs using Python, PostgreSQL, and Redis. "
                "Develop microservices, distributed systems, and backend services. 2-4 years experience."
            ),
            experience_min=2,
            experience_max=4,
        )
        score, _ = calculate_relevance_score(job)
        self.assertGreaterEqual(score, RELEVANCE_THRESHOLD)

    def test_rejects_generic_title_with_no_backend_evidence(self):
        # Generic role with python but only data/scripting/cli, no backend/api/db
        job = Job(
            id="test_generic_no_backend",
            title="Software Engineer",
            company="ScriptCo",
            description="Write standalone Python desktop automation scripts and GUI tools. 2 years experience.",
            experience_min=2,
            experience_max=3,
        )
        score, _ = calculate_relevance_score(job)
        self.assertEqual(score, 0.0)


class TestLanguageAlignmentRuleA(unittest.TestCase):
    """Verifies Rule A: Python ecosystem alignment and conflicting primary title languages."""

    def test_accepts_python_backend(self):
        job = Job(
            id="test_py_backend",
            title="Python Backend Developer",
            company="ApiCo",
            description="Build scalable REST APIs with Python, FastAPI, and PostgreSQL. 2 years experience.",
            experience_min=2,
            experience_max=3,
        )
        score, _ = calculate_relevance_score(job)
        self.assertGreaterEqual(score, RELEVANCE_THRESHOLD)

    def test_rejects_conflicting_title_languages(self):
        conflicting_titles = [
            "Java Backend Engineer",
            "Core Java Developer",
            "Golang Backend Engineer",
            "C++ Software Engineer",
            ".NET Backend Developer",
            "Ruby on Rails Developer",
        ]
        for title in conflicting_titles:
            job = Job(
                id="test_conflict_lang",
                title=title,
                company="OtherStack",
                description="Build services using SQL and distributed systems. 2 years exp.",
                experience_min=2,
                experience_max=3,
            )
            score, _ = calculate_relevance_score(job)
            self.assertEqual(score, -100.0, f"Expected disqualification for title: {title}")

    def test_rejects_backend_with_zero_python(self):
        job = Job(
            id="test_no_python",
            title="Backend Engineer",
            company="StackX",
            description="Build backend microservices and REST APIs using PostgreSQL and Redis. 2 years exp.",
            experience_min=2,
            experience_max=3,
        )
        score, _ = calculate_relevance_score(job)
        self.assertEqual(score, 0.0)


class TestSpecializedEngineeringRuleB(unittest.TestCase):
    """Verifies Rule B: specialized disciplines excluded unless hybrid backend/python."""

    def test_rejects_pure_data_sre_security(self):
        titles = [
            "Data Engineer",
            "Site Reliability Engineer",
            "Site Reliability Engineering",
            "Application Security Engineer",
            "Application Security Engineer II",
        ]
        for title in titles:
            job = Job(
                id="test_specialized",
                title=title,
                company="Corp",
                description="Work with Python, SQL, and distributed infrastructure. 2 years experience.",
                experience_min=2,
                experience_max=4,
            )
            score, _ = calculate_relevance_score(job)
            self.assertEqual(score, -100.0, f"Expected disqualification for {title}")

    def test_rejects_developer_tooling_and_devex(self):
        titles = [
            "Software Engineer II - Dev Accelerator",
            "Developer Productivity Engineer",
            "Developer Experience Engineer",
            "DevEx Engineer",
            "Developer Tooling Engineer",
            "Build Engineer",
        ]
        for title in titles:
            job = Job(
                id="test_devex",
                title=title,
                company="Corp",
                description="Build internal CLI tools, CI/CD pipelines, and developer frameworks using Python and gRPC. 2 years exp.",
                experience_min=2,
                experience_max=4,
            )
            score, _ = calculate_relevance_score(job)
            self.assertEqual(score, -100.0, f"Expected disqualification for {title}")

    def test_rejects_computer_vision(self):
        job = Job(
            id="test_cv",
            title="Computer Vision Engineer",
            company="VisionCo",
            description="Train YOLO and PyTorch object detection models, mAP metrics, GStreamer, and FastAPI serving on Linux. 2 years exp.",
            experience_min=2,
            experience_max=3,
        )
        score, _ = calculate_relevance_score(job)
        self.assertEqual(score, -100.0, "Expected disqualification for Computer Vision Engineer")

    def test_accepts_hybrid_backend_platforms(self):
        hybrid_titles = [
            "Backend Engineer - Data Platform",
            "Backend Engineer - Security Platform",
        ]
        for title in hybrid_titles:
            job = Job(
                id="test_hybrid",
                title=title,
                company="Corp",
                description="Build backend ingestion APIs and services in Python, PostgreSQL, and Kafka. 2-4 years exp.",
                experience_min=2,
                experience_max=4,
            )
            score, _ = calculate_relevance_score(job)
            self.assertGreaterEqual(score, RELEVANCE_THRESHOLD, f"Expected match for {title}")


class TestSyntheticProtectionCases16(unittest.TestCase):
    """Verifies the 16 core synthetic target profile test cases all pass."""

    PROTECTION_CASES = [
        {"title": "Python Backend Developer", "description": "Building REST APIs with Python, FastAPI, PostgreSQL, and Docker. Experience: 2 years.", "exp_min": 2, "exp_max": 4},
        {"title": "Backend Engineer - Python", "description": "Core backend services using Python, Redis, microservices, and MySQL. 1-3 years experience.", "exp_min": 1, "exp_max": 3},
        {"title": "FastAPI Backend Engineer", "description": "Design high throughput API endpoints using FastAPI, PostgreSQL, and RabbitMQ.", "exp_min": 2, "exp_max": 3},
        {"title": "Django Backend Developer", "description": "Build scalable web applications with Python and Django. 2 years experience.", "exp_min": 2, "exp_max": 4},
        {"title": "Flask Developer", "description": "Develop microservices with Flask, Python, SQLAlchemy, and Docker.", "exp_min": 1, "exp_max": 3},
        {"title": "Python API Engineer", "description": "API development using Python, FastAPI, REST, and distributed systems.", "exp_min": 2, "exp_max": 4},
        {"title": "Python Full Stack Developer", "description": "Full stack role with Python, Django backend and React frontend. 2-3 years exp.", "exp_min": 2, "exp_max": 3},
        {"title": "Backend Engineer with Python", "description": "Join our backend team building services in Python and PostgreSQL. 2 years exp.", "exp_min": 2, "exp_max": 4},
        {"title": "AI Backend Engineer using Python", "description": "Deploy LLM and RAG pipelines on Python, FastAPI, and LangChain backend.", "exp_min": 2, "exp_max": 3},
        {"title": "Software Engineer - Python APIs", "description": "Design and build RESTful APIs and backend services using Python and PostgreSQL. 2-4 years experience.", "exp_min": 2, "exp_max": 4},
        {"title": "Software Engineer - Backend Services", "description": "Develop server-side distributed services in Python, RabbitMQ, and Redis. 2 years experience.", "exp_min": 2, "exp_max": 3},
        {"title": "Python Microservices Engineer", "description": "Architect and implement microservices using Python, Docker, and Kafka. 2-3 years exp.", "exp_min": 2, "exp_max": 3},
        {"title": "Python API Developer", "description": "Develop high performance REST APIs using Python, FastAPI, and SQL databases. 1-3 years exp.", "exp_min": 1, "exp_max": 3},
        {"title": "Backend Engineer - Data Platform", "description": "Build backend ingestion APIs and data services in Python, PostgreSQL, and Kafka. 2-4 years exp.", "exp_min": 2, "exp_max": 4},
        {"title": "Backend Engineer - Security Platform", "description": "Develop core security service APIs and authorization services in Python and Docker. 2-4 years exp.", "exp_min": 2, "exp_max": 4},
        {"title": "AI Backend Engineer - Python", "description": "Server-side AI orchestration, LangChain agents, FastAPI, and vector databases in Python. 2 years exp.", "exp_min": 2, "exp_max": 3},
    ]

    def test_all_16_protection_cases(self):
        for case in self.PROTECTION_CASES:
            job = Job(
                id="test_case",
                title=case["title"],
                company="TargetCo",
                description=case["description"],
                experience_min=case["exp_min"],
                experience_max=case["exp_max"],
            )
            score, _ = calculate_relevance_score(job)
            self.assertGreaterEqual(
                score,
                RELEVANCE_THRESHOLD,
                f"Protection case failed: '{case['title']}' scored {score:.1f} (expected >= {RELEVANCE_THRESHOLD})"
            )


class TestBenchmarkRegressionJobs(unittest.TestCase):
    """Verifies classification against the validated 16 benchmark regression jobs."""

    @classmethod
    def setUpClass(cls):
        # Locate dataset_94_jobs.json
        possible_paths = [
            os.path.join(os.path.dirname(__file__), "data", "dataset_94_jobs.json"),
            os.path.join(os.path.dirname(__file__), "..", "..", "ollama-python-test", "dataset_94_jobs.json"),
            os.path.join(os.getcwd(), "ollama-python-test", "dataset_94_jobs.json"),
            os.path.join(os.getcwd(), "..", "ollama-python-test", "dataset_94_jobs.json"),
        ]
        cls.dataset = {}
        for p in possible_paths:
            if os.path.exists(p):
                with open(p, "r", encoding="utf-8") as f:
                    cls.dataset = {item["id"]: item for item in json.load(f)}
                break

    def _eval_job(self, job_id: str) -> tuple[float, str]:
        self.assertIn(job_id, self.dataset, f"Job {job_id} not found in benchmark dataset")
        raw = self.dataset[job_id]
        job = Job(
            id=raw["id"],
            title=raw["title"],
            company=raw["company"],
            description=raw["description"],
            experience_min=raw.get("experience_min"),
            experience_max=raw.get("experience_max"),
            experience_raw=raw.get("experience_raw"),
        )
        score, _ = calculate_relevance_score(job)
        classification = "RELEVANT" if score >= RELEVANCE_THRESHOLD else "NOT_RELEVANT"
        return score, classification

    def test_positive_regression_jobs(self):
        expected_relevant = ["db_job_145", "db_job_195", "db_job_197"]
        for jid in expected_relevant:
            score, classification = self._eval_job(jid)
            self.assertEqual(
                classification,
                "RELEVANT",
                f"Expected {jid} to be RELEVANT, got {classification} (score: {score:.1f})"
            )

    def test_negative_regression_jobs(self):
        expected_not_relevant = [
            "db_job_139", "db_job_146", "db_job_170", "db_job_177", "db_job_180",
            "db_job_181", "db_job_184", "db_job_187", "db_job_190", "db_job_191",
            "db_job_192", "db_job_198", "db_job_201", "db_job_202", "db_job_203"
        ]
        for jid in expected_not_relevant:
            score, classification = self._eval_job(jid)
            self.assertEqual(
                classification,
                "NOT_RELEVANT",
                f"Expected {jid} to be NOT_RELEVANT, got {classification} (score: {score:.1f})"
            )


if __name__ == "__main__":
    unittest.main()
