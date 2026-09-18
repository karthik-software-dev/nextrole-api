import unittest
from models.job import Job
from processing.prioritization import (
    TIER_1_LABEL,
    calculate_priority_score,
)
from processing.relevance import calculate_relevance_score, filter_relevant_jobs


class TestV6RelevanceAndPrioritization(unittest.TestCase):
    # 1. Python Backend Engineer, 2 years → strong relevance
    def test_python_backend_engineer_2_years_strong_relevance(self):
        job = Job(
            id="v6_1",
            title="Python Backend Engineer",
            company="Tech Corp",
            description="Building APIs with Python, FastAPI, and PostgreSQL.",
            experience_min=2,
            experience_max=3,
        )
        score, matched = calculate_relevance_score(job)
        self.assertGreaterEqual(score, 18.0)
        self.assertIn("Python", matched)
        self.assertIn("FastAPI", matched)
        self.assertIn("PostgreSQL", matched)

    # 2. Backend Engineer, 1–3 years → strong relevance
    def test_backend_engineer_1_to_3_years_strong_relevance(self):
        job = Job(
            id="v6_2",
            title="Backend Engineer",
            company="Cloud Inc",
            description="Python backend services with REST APIs, Redis, and MySQL.",
            experience_min=1,
            experience_max=3,
        )
        score, matched = calculate_relevance_score(job)
        self.assertGreaterEqual(score, 18.0)
        self.assertIn("Sweet-Spot Exp (1-3 Yrs)", matched)

    # 3. Python + FastAPI + PostgreSQL + Redis → strong backend score
    def test_python_fastapi_postgres_redis_strong_backend_score(self):
        job = Job(
            id="v6_3",
            title="Python Developer",
            company="Data Scale",
            description="Requires Python, FastAPI, PostgreSQL, and Redis caching.",
        )
        score, matched = calculate_relevance_score(job)
        self.assertGreaterEqual(score, 15.0)
        self.assertIn("FastAPI", matched)
        self.assertIn("PostgreSQL", matched)
        self.assertIn("Redis", matched)

    # 4. Python + FastAPI + RAG → strong AI-backend score
    def test_python_fastapi_rag_strong_ai_backend_score(self):
        job = Job(
            id="v6_4",
            title="AI Backend Engineer",
            company="GenAI Corp",
            description="Developing AI pipelines using Python, FastAPI, LLMs, and RAG architectures.",
        )
        score, matched = calculate_relevance_score(job)
        self.assertGreaterEqual(score, 16.0)
        self.assertIn("AI-Backend Synergy", matched)
        self.assertIn("RAG", matched)
        self.assertIn("LLM", matched)

    # 5. Senior Backend Engineer, 7+ years → should not be High Priority (disqualified or heavily penalized)
    def test_senior_backend_engineer_7_plus_years_not_high_priority(self):
        job = Job(
            id="v6_5",
            title="Senior Backend Engineer",
            company="Enterprise Corp",
            description="Python, FastAPI, Postgres, Docker. 7+ years of experience required.",
            experience_min=7,
            apply_type="DIRECT_ATS",
        )
        score, matched = calculate_relevance_score(job)
        job.relevance_score = score
        job.matched_skills = matched
        p_score, tier = calculate_priority_score(job)
        # Should be disqualified (-100) and cannot be Tier 1
        self.assertNotEqual(tier, TIER_1_LABEL)

    # 6. Backend Engineer, 4–9 years → should be penalized appropriately (not High Priority)
    def test_backend_engineer_4_to_9_years_penalized(self):
        job = Job(
            id="v6_6",
            title="Backend Engineer",
            company="Health Scale",
            description="Python, FastAPI, PostgreSQL, Redis, Docker.",
            experience_min=4,
            experience_max=9,
            apply_type="DIRECT_ATS",
        )
        score, matched = calculate_relevance_score(job)
        self.assertIn("Senior Range Penalty", matched)
        job.relevance_score = score
        job.matched_skills = matched
        p_score, tier = calculate_priority_score(job)
        # Cannot be Tier 1 High Priority due to 4-9 yr senior range penalty
        self.assertNotEqual(tier, TIER_1_LABEL)

    # 7. Generic Software Engineer with Python + backend APIs → should remain relevant
    def test_generic_swe_with_python_and_backend_apis_remains_relevant(self):
        job = Job(
            id="v6_7",
            title="Software Engineer",
            company="SaaS Co",
            description="Working on distributed backend services with Python, FastAPI, REST APIs, and PostgreSQL.",
        )
        score, matched = calculate_relevance_score(job)
        self.assertGreaterEqual(score, 12.0)
        self.assertIn("Python", matched)
        self.assertIn("REST API", matched)

    # 8. Generic Software Engineer with no backend/Python evidence → should be rejected
    def test_generic_swe_without_backend_evidence_rejected(self):
        job = Job(
            id="v6_8",
            title="Software Engineer",
            company="UI Corp",
            description="Frontend UI development with HTML, CSS, JavaScript, and React.",
        )
        score, matched = calculate_relevance_score(job)
        self.assertEqual(score, 0.0)

    def test_generic_swe_with_only_python_and_system_design_rejected(self):
        job = Job(
            id="v6_8b",
            title="Software Engineer II",
            company="MegaCorp",
            description="Experience in C++, Java, Python, or Go. Work on large-scale system design and networking.",
        )
        score, matched = calculate_relevance_score(job)
        self.assertEqual(score, 0.0)

    def test_generic_fullstack_without_concrete_backend_rejected(self):
        job = Job(
            id="v6_8c",
            title="Software Engineer III, Full Stack",
            company="CloudCorp",
            description="Experience across back-end such as Java, Python, Golang or C++ and front-end JavaScript/HTML.",
        )
        score, matched = calculate_relevance_score(job)
        self.assertEqual(score, 0.0)

    def test_generic_fullstack_with_python_and_django_accepted(self):
        job = Job(
            id="v6_8d",
            title="Full Stack Engineer",
            company="FinTech",
            description="Building SaaS platform with Python, Django, React, and PostgreSQL.",
        )
        score, matched = calculate_relevance_score(job)
        self.assertGreaterEqual(score, 12.0)

    def test_generic_swe_2_with_postgres_and_rest_accepted(self):
        job = Job(
            id="v6_8e",
            title="Software Engineer 2",
            company="JLL",
            description="Python, PostgreSQL, REST APIs, Microservices, and Docker.",
        )
        score, matched = calculate_relevance_score(job)
        self.assertGreaterEqual(score, 12.0)

    # 9. QA Automation Engineer → excluded
    def test_qa_automation_engineer_hard_excluded(self):
        job = Job(
            id="v6_9",
            title="QA Automation Engineer",
            company="Quality Lab",
            description="Python, Selenium, PyTest, CI/CD, and PostgreSQL.",
        )
        score, _ = calculate_relevance_score(job)
        self.assertEqual(score, -100.0)

    # 10. Data Scientist → excluded/not relevant
    def test_data_scientist_hard_excluded(self):
        job = Job(
            id="v6_10",
            title="Senior Data Scientist",
            company="Analytics AI",
            description="Python, Machine Learning, Statistics, Pandas, SQL.",
        )
        score, _ = calculate_relevance_score(job)
        self.assertEqual(score, -100.0)

    # 11. ML Engineer → excluded according to target profile
    def test_ml_engineer_hard_excluded(self):
        job = Job(
            id="v6_11",
            title="Machine Learning Engineer",
            company="Model Corp",
            description="PyTorch, TensorFlow, Python, Kubernetes.",
        )
        score, _ = calculate_relevance_score(job)
        self.assertEqual(score, -100.0)

    # 12. Python Support Engineer → verify current behavior and avoid accidental false positives
    def test_python_support_engineer_hard_excluded(self):
        job = Job(
            id="v6_12",
            title="Python Support Engineer",
            company="Help Desk Co",
            description="Python, Linux, debugging client issues, tickets.",
        )
        score, _ = calculate_relevance_score(job)
        self.assertEqual(score, -100.0)

    # 13. Python Solution Engineer → verify current behavior
    def test_python_solution_engineer_hard_excluded(self):
        job = Job(
            id="v6_13",
            title="Python Solution Engineer",
            company="Sales Tech",
            description="Python, Pre-sales, Client demos, REST APIs.",
        )
        score, _ = calculate_relevance_score(job)
        self.assertEqual(score, -100.0)

    # 14. Python + microservices + Kafka + PostgreSQL → strong backend relevance
    def test_python_microservices_kafka_postgres_strong_backend(self):
        job = Job(
            id="v6_14",
            title="Backend Engineer",
            company="FinTech Stream",
            description="Python, Microservices architecture, Kafka streaming, and PostgreSQL database.",
        )
        score, matched = calculate_relevance_score(job)
        self.assertGreaterEqual(score, 18.0)
        self.assertIn("Microservices", matched)
        self.assertIn("Kafka", matched)
        self.assertIn("PostgreSQL", matched)

    # 15. Long description containing many unrelated technologies → should not produce excessive score
    def test_long_description_unrelated_technologies_does_not_exceed_cap(self):
        job = Job(
            id="v6_15",
            title="Backend Developer",
            company="Buzzword Inc",
            description="""
            Python, Django, FastAPI, Flask, REST API, GraphQL, gRPC, WebSocket,
            PostgreSQL, MySQL, SQLite, MongoDB, DynamoDB, Redis, Memcached,
            Docker, Kubernetes, AWS, GCP, Azure, Nginx, Linux, CI/CD, Git,
            React, Next.js, TypeScript, Tailwind, Redux, Zustand,
            LLM, RAG, LangChain, Vector DB, Pinecone, Qdrant
            """,
        )
        score, _ = calculate_relevance_score(job)
        # Score must be bounded (capped at title 10 + description 18 + synergies 4 = max 32)
        self.assertLessEqual(score, 32.0)

    # 16. Postgres + PostgreSQL → should not double-count unnecessarily
    def test_postgres_and_postgresql_do_not_double_count(self):
        job = Job(
            id="v6_16",
            title="Backend Engineer",
            company="DB Corp",
            description="Python backend requiring Postgres and PostgreSQL database design.",
        )
        score, matched = calculate_relevance_score(job)
        # Count of 'PostgreSQL' in matched_skills must be exactly 1
        postgres_matches = [m for m in matched if m == "PostgreSQL"]
        self.assertEqual(len(postgres_matches), 1)

    # 17. REST API + RESTful API → should not double-count unnecessarily
    def test_rest_api_and_restful_api_do_not_double_count(self):
        job = Job(
            id="v6_17",
            title="Backend Engineer",
            company="API Corp",
            description="Python backend requiring REST API and RESTful API development.",
        )
        score, matched = calculate_relevance_score(job)
        # Count of 'REST API' in matched_skills must be exactly 1
        rest_matches = [m for m in matched if m == "REST API"]
        self.assertEqual(len(rest_matches), 1)


if __name__ == "__main__":
    unittest.main()
