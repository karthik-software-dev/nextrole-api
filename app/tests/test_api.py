import unittest
from fastapi.testclient import TestClient

from models.job import Job as JobDataclass
from server import app
from storage.database import engine, get_db, init_db
from storage.repositories.job_repository import JobRepository


class TestFastAPIBackend(unittest.TestCase):
    """End-to-end automated test suite for FastAPI backend endpoints."""

    @classmethod
    def setUpClass(cls):
        """Initializes database schema and prepares test client."""
        init_db()
        cls.client = TestClient(app)

        # Seed test data for API testing
        with get_db() as session:
            job_dc = JobDataclass(
                id="api_test_job_1",
                title="Python Backend Developer",
                company="Razorpay Tech",
                source="indeed",
                location="Bengaluru, Karnataka",
                apply_url="https://jobs.smartrecruiters.com/Razorpay/1001",
                apply_type="DIRECT_ATS",
                ats_provider="SmartRecruiters ATS",
                relevance_score=26.0,
                matched_skills=["FastAPI", "PostgreSQL", "Docker"],
                priority_score=31.0,
                priority_tier="⭐ TIER 1 (HIGH PRIORITY)",
            )
            cls.test_job, _ = JobRepository.upsert_job(session, job_dc)
            cls.test_job_id = cls.test_job.id
            cls.test_company_id = cls.test_job.company_id

    def setUp(self):
        """Ensures clean isolated state before each test method."""
        with get_db() as session:
            from sqlalchemy import text
            from storage.models.job import Job as DBJob
            job = session.get(DBJob, self.test_job_id)
            if job:
                job.is_active = True
            session.execute(text("DELETE FROM applications WHERE job_id = :jid"), {"jid": self.test_job_id})
            session.commit()



    def test_health_check_endpoint(self):
        """Tests GET /health returns 200 and connected status."""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["database"], "connected")

    def test_root_information_endpoint(self):
        """Tests GET / returns service metadata and docs links."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["name"], "Job Agent API")
        self.assertIn("docs_url", data)

    def test_list_jobs_with_filters(self):
        """Tests GET /api/v1/jobs with pagination and filters."""
        # Unfiltered listing
        response = self.client.get("/api/v1/jobs?page=1&page_size=10")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("items", data)
        self.assertIn("meta", data)
        self.assertGreaterEqual(data["meta"]["total"], 1)

        # Filter by Bangalore
        blr_response = self.client.get("/api/v1/jobs?location=BANGALORE")
        self.assertEqual(blr_response.status_code, 200)
        blr_data = blr_response.json()
        self.assertGreaterEqual(len(blr_data["items"]), 1)
        for j in blr_data["items"]:
            self.assertEqual(j["location_bucket"], "BANGALORE")

        # Filter by search term
        search_response = self.client.get("/api/v1/jobs?search=Razorpay%20Tech")
        self.assertEqual(search_response.status_code, 200)
        search_data = search_response.json()
        self.assertGreaterEqual(len(search_data["items"]), 1)
        self.assertEqual(search_data["items"][0]["company_name"], "Razorpay Tech")

    def test_get_job_detail_and_404(self):
        """Tests GET /api/v1/jobs/{id} and 404 handling."""
        response = self.client.get(f"/api/v1/jobs/{self.test_job_id}")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["id"], self.test_job_id)
        self.assertEqual(data["title"], "Python Backend Developer")
        self.assertIsNotNone(data["company"])
        self.assertGreaterEqual(len(data["sources"]), 1)

        # Test non-existent job ID returns 404
        bad_response = self.client.get("/api/v1/jobs/99999999")
        self.assertEqual(bad_response.status_code, 404)

    def test_deactivate_job_endpoint(self):
        """Tests PATCH /api/v1/jobs/{id}/deactivate (soft-delete)."""
        response = self.client.patch(f"/api/v1/jobs/{self.test_job_id}/deactivate")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data["is_active"])

        # Confirm job is now excluded from active_only query
        active_response = self.client.get(f"/api/v1/jobs?search=Razorpay%20Tech&active_only=true")
        self.assertEqual(active_response.status_code, 200)
        self.assertEqual(len(active_response.json()["items"]), 0)

        # Confirm job is visible when active_only=false
        inactive_response = self.client.get(f"/api/v1/jobs?search=Razorpay%20Tech&active_only=false")
        self.assertEqual(inactive_response.status_code, 200)
        self.assertGreaterEqual(len(inactive_response.json()["items"]), 1)

    def test_companies_endpoints(self):
        """Tests GET /api/v1/companies and GET /api/v1/companies/{id}."""
        list_response = self.client.get("/api/v1/companies?page=1&page_size=10")
        self.assertEqual(list_response.status_code, 200)
        list_data = list_response.json()
        self.assertGreaterEqual(len(list_data["items"]), 1)

        detail_response = self.client.get(f"/api/v1/companies/{self.test_company_id}")
        self.assertEqual(detail_response.status_code, 200)
        detail_data = detail_response.json()
        self.assertEqual(detail_data["id"], self.test_company_id)
        self.assertEqual(detail_data["name"], "Razorpay Tech")

    def test_application_lifecycle_endpoints(self):
        """Tests POST /api/v1/applications and PATCH /api/v1/applications/{id} status update."""
        # 1. Create application
        create_payload = {
            "job_id": self.test_job_id,
            "user_id": 1,
            "resume_version": "fastapi_backend_v5.pdf",
            "portal_type": "direct_ats",
            "notes": "Referred by Senior Engineer on Payments team",
            "initial_status": "drafted",
        }
        create_res = self.client.post("/api/v1/applications", json=create_payload)
        self.assertEqual(create_res.status_code, 201)
        app_data = create_res.json()
        app_id = app_data["id"]
        self.assertEqual(app_data["status"], "drafted")
        self.assertEqual(len(app_data["history"]), 1)

        # 2. Get application detail
        get_res = self.client.get(f"/api/v1/applications/{app_id}")
        self.assertEqual(get_res.status_code, 200)
        self.assertEqual(get_res.json()["id"], app_id)

        # 3. Update application status to 'applied'
        update_payload = {
            "status": "applied",
            "notes": "Application submitted via SmartRecruiters",
            "note_for_history": "Submitted application with tailored resume",
        }
        update_res = self.client.patch(f"/api/v1/applications/{app_id}", json=update_payload)
        self.assertEqual(update_res.status_code, 200)
        updated_data = update_res.json()
        self.assertEqual(updated_data["status"], "applied")
        self.assertIsNotNone(updated_data["applied_at"])
        self.assertEqual(len(updated_data["history"]), 2)
        self.assertEqual(updated_data["history"][1]["new_status"], "applied")

    def test_dashboard_summary_endpoint(self):
        """Tests GET /api/v1/dashboard/summary aggregates all required metrics."""
        response = self.client.get("/api/v1/dashboard/summary")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("total_jobs", data)
        self.assertIn("active_jobs", data)
        self.assertIn("tier1_jobs", data)
        self.assertIn("location_breakdown", data)
        self.assertIn("application_breakdown", data)

    def test_analytics_summary_endpoint(self):
        """Tests GET /api/v1/analytics/summary aggregates KPIs, job intelligence, applications, and performance."""
        response = self.client.get("/api/v1/analytics/summary?range=30d")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("kpis", data)
        self.assertIn("job_intelligence", data)
        self.assertIn("application_analytics", data)
        self.assertIn("agent_performance", data)
        self.assertIn("applications", data["kpis"])
        self.assertIn("interviews", data["kpis"])
        self.assertIn("match_scores", data["job_intelligence"])
        self.assertIn("top_skills", data["job_intelligence"])
        self.assertIn("salary_distribution", data["job_intelligence"])
        self.assertIn("funnel", data["application_analytics"])
        self.assertIn("filtering_efficiency_pct", data["agent_performance"])

    def test_settings_endpoints(self):
        """Tests GET and PUT /api/v1/settings for profile and scoring preferences."""
        # 1. Test GET /api/v1/settings
        get_res = self.client.get("/api/v1/settings")
        self.assertEqual(get_res.status_code, 200)
        data = get_res.json()
        self.assertIn("profile", data)
        self.assertIn("scoring", data)
        self.assertIn("name", data["profile"])
        self.assertIn("min_experience", data["scoring"])
        self.assertIn("min_score", data["scoring"])

        # 2. Test PUT /api/v1/settings
        update_payload = {
            "profile": {
                "name": "Karthik Software Dev",
                "email": "karthik.dev@test.local",
                "target_role": "Senior Python Backend Engineer",
            },
            "scoring": {
                "min_experience": 2,
                "max_experience": 6,
                "min_score": 10.5,
                "target_locations": ["Bangalore", "Chennai", "Remote", "Hyderabad"],
            },
        }
        put_res = self.client.put("/api/v1/settings", json=update_payload)
        self.assertEqual(put_res.status_code, 200)
        updated_data = put_res.json()
        self.assertEqual(updated_data["profile"]["name"], "Karthik Software Dev")
        self.assertEqual(updated_data["profile"]["target_role"], "Senior Python Backend Engineer")
        self.assertEqual(updated_data["scoring"]["min_experience"], 2)
        self.assertEqual(updated_data["scoring"]["min_score"], 10.5)
        self.assertIn("Hyderabad", updated_data["scoring"]["target_locations"])


if __name__ == "__main__":
    unittest.main()
