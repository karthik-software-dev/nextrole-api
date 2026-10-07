"""Comprehensive Verification Suite for Custom Scraper -> Processing -> Database Flow.

Validates:
1. Custom in-house scrapers produce canonical Job models without Apify.
2. Scraped jobs pass through relevance scoring, hard exclusions, and deduplication.
3. Jobs are correctly upserted and reconciled in PostgreSQL.
4. Multi-source sightings create JobSource records and increment source_count.
5. Existing Application tracking relationships are strictly preserved.
6. DiscoveryService orchestrates the custom scraper flow seamlessly.
7. Zero runtime dependencies on Apify.
"""

from datetime import datetime, timezone
import unittest
from uuid import uuid4

from custom_scraper import (
    IndeedScraper,
    LinkedInScraper,
    NaukriScraper,
    WellfoundScraper,
    GreenhouseScraper,
    LeverScraper,
)
from custom_scraper.adapter import to_job_agent_model
from custom_scraper.models import JobItem
from models.job import Job
from processing.deduplication import clean_job_title, deduplicate_jobs
from processing.prioritization import prioritize_jobs
from processing.relevance import calculate_relevance_score, filter_relevant_jobs
from services.discovery_service import DiscoveryService
from storage.database import get_db, init_db
from storage.models.application import Application
from storage.models.job import Job as JobModel
from storage.models.job_source import JobSource
from storage.models.user import User
from storage.repositories.application_repository import ApplicationRepository
from storage.repositories.job_repository import JobRepository


class TestCustomScraperIntegration(unittest.TestCase):
    """Integration test suite covering scraper outputs, processing, and database persistence."""

    @classmethod
    def setUpClass(cls):
        init_db()

    def test_01_no_apify_imports_in_custom_scraper(self):
        """Verifies zero apify imports in custom_scraper package."""
        import custom_scraper
        import inspect
        import sys

        self.assertNotIn("apify_client", sys.modules)

    def test_02_job_item_adapter_to_canonical_job(self):
        """Verifies custom scraper JobItem converts to canonical models.job.Job accurately."""
        job_item = JobItem(
            id="ind_test_001",
            title="Python Backend Engineer",
            company="Acme Tech",
            source="indeed",
            location="Bengaluru, Karnataka",
            is_remote=False,
            salary_raw="₹18,00,000 - ₹24,00,000 a year",
            salary_min=1800000.0,
            salary_max=2400000.0,
            salary_currency="INR",
            description="Looking for Python, FastAPI, and PostgreSQL developer.",
            discovery_url="https://in.indeed.com/viewjob?jk=ind_test_001",
            apply_url="https://in.indeed.com/apply/ind_test_001",
            posted_at="2026-09-25",
            experience_min=2,
            experience_max=4,
            experience_raw="2-4 years",
            raw_data={"test": "payload"},
        )

        job: Job = to_job_agent_model(job_item)

        self.assertIsInstance(job, Job)
        self.assertEqual(job.id, "ind_test_001")
        self.assertEqual(job.title, "Python Backend Engineer")
        self.assertEqual(job.company, "Acme Tech")
        self.assertEqual(job.source, "indeed")
        self.assertEqual(job.location, "Bengaluru, Karnataka")
        self.assertFalse(job.is_remote)
        self.assertEqual(job.salary_min, 1800000.0)
        self.assertEqual(job.salary_max, 2400000.0)
        self.assertEqual(job.experience_min, 2)
        self.assertEqual(job.experience_max, 4)
        self.assertEqual(job.raw_data, {"test": "payload"})

    def test_03_relevance_scoring_and_hard_exclusions(self):
        """Verifies relevance scoring engine calculates scores and applies hard exclusions."""
        target_job = Job(
            id="test_rel_1",
            title="Python Backend Developer",
            company="TechCorp",
            source="indeed",
            location="Bengaluru",
            description="Hands on experience with Python, FastAPI, Docker, and PostgreSQL.",
            experience_min=2,
            experience_max=4,
        )
        score, skills = calculate_relevance_score(target_job)
        self.assertGreaterEqual(score, 8.0)
        self.assertTrue(any("FastAPI" in s for s in skills) or any("Python" in s for s in skills))

        senior_disqualified = Job(
            id="test_rel_2",
            title="Engineering Manager - QA & Testing",
            company="TechCorp",
            source="naukri",
            location="Bengaluru",
            description="Lead the QA team with 8+ years experience.",
            experience_min=8,
        )
        disq_score, _ = calculate_relevance_score(senior_disqualified)
        self.assertEqual(disq_score, -100.0)

    def test_04_cross_source_deduplication(self):
        """Verifies cross-source deduplication merges duplicate listings and favors direct ATS."""
        job_indeed = Job(
            id="jk_dup_1",
            title="FastAPI Developer",
            company="Stripe",
            source="indeed",
            location="Bengaluru",
            apply_url="https://in.indeed.com/viewjob?jk=dup1&utm_source=feed",
            apply_type="AGGREGATOR",
            relevance_score=15.0,
        )
        job_ats = Job(
            id="ats_dup_1",
            title="FastAPI Developer",
            company="Stripe",
            source="greenhouse",
            location="Bengaluru",
            apply_url="https://boards.greenhouse.io/stripe/jobs/998877?gh_jid=998877",
            apply_type="DIRECT_ATS",
            ats_provider="greenhouse",
            relevance_score=15.0,
        )

        deduped = deduplicate_jobs([job_indeed, job_ats])
        self.assertEqual(len(deduped), 1)
        winner = deduped[0]
        # Should retain the direct ATS apply link
        self.assertEqual(winner.apply_type, "DIRECT_ATS")
        self.assertIn("greenhouse.io", winner.apply_url)
        self.assertGreaterEqual(winner.duplicate_count, 2)

    def test_05_database_upsert_and_multisource_sighting(self):
        """Verifies PostgreSQL upsert correctly updates sightings and maintains job sources."""
        uid = uuid4().hex[:6]
        company_name = f"InHouseTestCo_{uid}"

        with get_db() as session:
            # 1. First sighting via Naukri
            job_v1 = Job(
                id=f"nk_{uid}",
                title="Python Backend Engineer",
                company=company_name,
                source="naukri",
                location="Bengaluru, Karnataka",
                apply_url=f"https://www.naukri.com/job-listings-{uid}",
                posted_at="2026-09-28",
                relevance_score=14.0,
                priority_score=50.0,
                priority_tier="TIER 2",
            )
            created_job, is_new = JobRepository.upsert_job(session, job_v1)
            session.commit()

            self.assertTrue(is_new)
            self.assertEqual(created_job.source_count, 1)
            job_db_id = created_job.id

            # Verify initial JobSource record
            sources = session.query(JobSource).filter(JobSource.job_id == job_db_id).all()
            self.assertEqual(len(sources), 1)
            self.assertEqual(sources[0].source_name, "naukri")

            # 2. Second sighting of same job via Indeed
            job_v2 = Job(
                id=f"ind_{uid}",
                title="Python Backend Engineer",
                company=company_name,
                source="indeed",
                location="Bengaluru, Karnataka",
                apply_url=f"https://in.indeed.com/viewjob?jk={uid}",
                posted_at="2026-09-28",
                relevance_score=14.0,
                priority_score=55.0,
                priority_tier="TIER 2",
            )
            updated_job, is_new_2 = JobRepository.upsert_job(session, job_v2)
            session.commit()

            self.assertFalse(is_new_2)
            self.assertEqual(updated_job.id, job_db_id)
            self.assertEqual(updated_job.source_count, 2)
            self.assertEqual(float(updated_job.priority_score), 55.0)

            # Verify both JobSources exist
            sources_after = session.query(JobSource).filter(JobSource.job_id == job_db_id).all()
            self.assertEqual(len(sources_after), 2)
            source_names = {s.source_name for s in sources_after}
            self.assertIn("naukri", source_names)
            self.assertIn("indeed", source_names)

    def test_06_application_integrity_preserved_on_scrape_update(self):
        """Verifies existing application records and notes remain untouched when a job is re-scraped."""
        uid = uuid4().hex[:6]
        with get_db() as session:
            # 1. Create job
            job = Job(
                id=f"app_test_{uid}",
                title="Python Backend Engineer",
                company=f"AppIntegrityCo_{uid}",
                source="indeed",
                location="Bengaluru",
                relevance_score=16.0,
                priority_score=60.0,
            )
            db_job, _ = JobRepository.upsert_job(session, job)
            session.commit()

            # 2. User applies to the job
            user = session.query(User).first()
            if not user:
                user = User(name="Test Seeker", email=f"seeker_{uid}@test.local")
                session.add(user)
                session.commit()

            app = ApplicationRepository.record_application(
                session=session,
                user_id=user.id,
                job_id=db_job.id,
                notes="Submitted customized resume with FastAPI project highlights.",
                initial_status="interviewing",
            )
            session.commit()
            app_id = app.id

            # 3. Simulate re-scraping the job from another source
            job_rescraped = Job(
                id=f"re_scrape_{uid}",
                title="Python Backend Engineer",
                company=f"AppIntegrityCo_{uid}",
                source="linkedin",
                location="Bengaluru",
                relevance_score=18.0,
                priority_score=65.0,
            )
            JobRepository.upsert_job(session, job_rescraped)
            session.commit()

            # 4. Verify application remains intact with same status and notes
            app_after = session.get(Application, app_id)
            self.assertIsNotNone(app_after)
            self.assertEqual(app_after.status, "interviewing")
            self.assertEqual(app_after.notes, "Submitted customized resume with FastAPI project highlights.")
            self.assertEqual(app_after.job_id, db_job.id)

    def test_07_discovery_service_run_pipeline_cache_mode(self):
        """Verifies DiscoveryService executes complete pipeline cleanly in cache mode."""
        initial_status = DiscoveryService.get_status()
        self.assertFalse(initial_status.is_running)

        # Run pipeline with cache enabled
        DiscoveryService.run_pipeline(source="ats", location="all", use_cache=True)

        status_after = DiscoveryService.get_status()
        self.assertFalse(status_after.is_running)
        self.assertEqual(status_after.last_status, "completed")
        self.assertIsNone(status_after.last_error)
        self.assertIsNotNone(status_after.last_run_at)

    def test_08_discovery_service_parallel_execution(self):
        """Verifies DiscoveryService executes multiple sources concurrently via ThreadPoolExecutor."""
        from unittest.mock import patch

        def mock_fetcher_1(use_cache=True):
            return [
                Job(
                    id="mock_p1",
                    title="Python Backend Engineer",
                    company="AsyncTech A",
                    source="indeed",
                    location="Bangalore",
                    relevance_score=20.0,
                    priority_score=70.0,
                    discovery_url="https://example.com/job1",
                    apply_url="https://example.com/job1",
                )
            ]

        def mock_fetcher_2(use_cache=True):
            return [
                Job(
                    id="mock_p2",
                    title="Python Backend Developer",
                    company="AsyncTech B",
                    source="naukri",
                    location="Bangalore",
                    relevance_score=19.0,
                    priority_score=68.0,
                    discovery_url="https://example.com/job2",
                    apply_url="https://example.com/job2",
                )
            ]

        mock_sources = [
            ("indeed", ("indeed", "all"), mock_fetcher_1),
            ("naukri", ("naukri", "all"), mock_fetcher_2),
        ]

        with patch("services.discovery_service.CentralJobProcessor.process_jobs") as mock_proc:
            mock_proc.return_value = ([], [])
            with patch("services.discovery_service.get_db"):
                DiscoveryService.run_pipeline(source="all", location="all", use_cache=True, custom_fetchers=mock_sources)
                # Ensure it completes without error
                status = DiscoveryService.get_status()
                self.assertEqual(status.last_status, "completed")
                self.assertEqual(DiscoveryService._last_jobs_found, 2)

    def test_09_remotive_scraper_and_abroad_bucketing(self):
        """Verifies Remotive scraper parses worldwide remote jobs into canonical Job models and ABROAD bucket."""
        from unittest.mock import MagicMock, patch
        from custom_scraper import RemotiveScraper
        from custom_scraper.adapter import to_job_agent_model
        from processing.prioritization import get_location_bucket, calculate_priority_score

        sample_api_response = {
            "jobs": [
                {
                    "id": 99999,
                    "title": "Senior Python Backend Engineer",
                    "company_name": "Global Cloud Corp",
                    "candidate_required_location": "Worldwide",
                    "salary": "$90k - $120k",
                    "description": "Building FastAPI microservices. Visa sponsorship or global contractor.",
                    "url": "https://remotive.com/job/99999",
                    "publication_date": "2026-09-28T10:00:00",
                    "tags": ["python", "fastapi", "remote"],
                }
            ]
        }

        with patch("httpx.Client") as mock_client:
            mock_resp = MagicMock()
            mock_resp.json.return_value = sample_api_response
            mock_resp.raise_for_status.return_value = None
            mock_client.return_value.__enter__.return_value.get.return_value = mock_resp

            scraper = RemotiveScraper()
            result = scraper.scrape(search_term="python", results_wanted=10)

            self.assertEqual(result.total_found, 1)
            item = result.jobs[0]
            self.assertEqual(item.id, "remotive_99999")
            self.assertEqual(item.salary_min, 90000.0)
            self.assertEqual(item.salary_max, 120000.0)
            self.assertEqual(item.salary_currency, "USD")

            canonical = to_job_agent_model(item)
            canonical.source = "remotive"
            canonical.relevance_score = 22.0

            # Verify bucketing into ABROAD
            bucket = get_location_bucket(canonical)
            self.assertEqual(bucket, "ABROAD")

            # Verify priority score tags
            priority, tier = calculate_priority_score(canonical)
            self.assertIn("Comp Disclosed (Global)", canonical.matched_skills)

    def test_10_sources_registry_includes_abroad(self):
        """Verifies Remotive and Indeed International are registered in sources registry."""
        from config.sources_registry import get_all_sources, get_source_by_slug

        sources = get_all_sources()
        slugs = [s.slug for s in sources]
        self.assertIn("remotive", slugs)
        self.assertIn("indeed_abroad", slugs)

        remotive_source = get_source_by_slug("remotive")
        self.assertIsNotNone(remotive_source)
        self.assertEqual(remotive_source.name, "Remotive")
        self.assertTrue(remotive_source.enabled)

        indeed_abroad_source = get_source_by_slug("indeed_abroad")
        self.assertIsNotNone(indeed_abroad_source)
        self.assertEqual(indeed_abroad_source.name, "Indeed International")
        self.assertTrue(indeed_abroad_source.enabled)

    def test_11_category_a_worldwide_remote_scrapers(self):
        """Verifies Jobicy, We Work Remotely, and Arbeitnow scrapers parse jobs into canonical models and ABROAD bucket."""
        from unittest.mock import MagicMock, patch
        from custom_scraper import JobicyScraper, WeWorkRemotelyScraper, ArbeitnowScraper
        from custom_scraper.adapter import to_job_agent_model
        from processing.prioritization import get_location_bucket
        from config.sources_registry import get_all_sources, get_source_by_slug

        # 1. Jobicy
        jobicy_response = {
            "jobs": [
                {
                    "id": 88888,
                    "jobTitle": "Backend Python Developer",
                    "companyName": "Quora",
                    "jobGeo": "Anywhere",
                    "annualSalaryMin": 95000,
                    "annualSalaryMax": 135000,
                    "salaryCurrency": "USD",
                    "jobDescription": "Python, Django, FastAPI distributed caching.",
                    "url": "https://jobicy.com/job/88888",
                    "pubDate": "2026-09-28T12:00:00+00:00",
                    "jobIndustry": ["Software Engineering"],
                }
            ]
        }
        with patch("httpx.Client") as mock_client:
            mock_resp = MagicMock()
            mock_resp.json.return_value = jobicy_response
            mock_resp.raise_for_status.return_value = None
            mock_client.return_value.__enter__.return_value.get.return_value = mock_resp

            scraper = JobicyScraper()
            result = scraper.scrape(search_term="python", results_wanted=5)
            self.assertEqual(result.total_found, 1)
            item = result.jobs[0]
            self.assertEqual(item.company, "Quora")
            self.assertEqual(item.salary_min, 95000.0)
            self.assertEqual(item.salary_max, 135000.0)
            canon = to_job_agent_model(item)
            canon.source = "jobicy"
            self.assertEqual(get_location_bucket(canon), "ABROAD")

        # 2. We Work Remotely (WWR)
        wwr_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
            <channel>
                <item>
                    <title>Canonical: Distributed Python Systems Engineer</title>
                    <link>https://weworkremotely.com/job/canonical-1</link>
                    <guid>https://weworkremotely.com/job/canonical-1</guid>
                    <description>Working on open source cloud and Kubernetes with Python.</description>
                    <pubDate>Mon, 28 Sep 2026 10:00:00 +0000</pubDate>
                    <region>Anywhere in the World</region>
                </item>
            </channel>
        </rss>"""
        with patch("httpx.Client") as mock_client:
            mock_resp = MagicMock()
            mock_resp.text = wwr_xml
            mock_resp.raise_for_status.return_value = None
            mock_client.return_value.__enter__.return_value.get.return_value = mock_resp

            wwr_scraper = WeWorkRemotelyScraper()
            wwr_result = wwr_scraper.scrape(search_term="python", results_wanted=5)
            self.assertEqual(wwr_result.total_found, 1)
            item_wwr = wwr_result.jobs[0]
            self.assertEqual(item_wwr.company, "Canonical")
            self.assertEqual(item_wwr.title, "Distributed Python Systems Engineer")
            canon_wwr = to_job_agent_model(item_wwr)
            canon_wwr.source = "wwr"
            self.assertEqual(get_location_bucket(canon_wwr), "ABROAD")

        # 3. Arbeitnow
        arbeitnow_json = {
            "data": [
                {
                    "slug": "python-software-engineer-remote-1234",
                    "company_name": "CloudTech EU",
                    "title": "Python Backend Engineer",
                    "remote": True,
                    "url": "https://arbeitnow.com/job/1234",
                    "tags": ["Python", "FastAPI"],
                    "location": "Berlin / Remote",
                    "created_at": 1786516800,
                    "description": "FastAPI backend development.",
                }
            ]
        }
        with patch("httpx.Client") as mock_client:
            mock_resp = MagicMock()
            mock_resp.json.return_value = arbeitnow_json
            mock_resp.raise_for_status.return_value = None
            mock_client.return_value.__enter__.return_value.get.return_value = mock_resp

            an_scraper = ArbeitnowScraper()
            an_result = an_scraper.scrape(search_term="python", results_wanted=5)
            self.assertEqual(an_result.total_found, 1)
            item_an = an_result.jobs[0]
            self.assertEqual(item_an.company, "CloudTech EU")
            self.assertTrue(item_an.is_remote)
            canon_an = to_job_agent_model(item_an)
            canon_an.source = "arbeitnow"
            self.assertEqual(get_location_bucket(canon_an), "ABROAD")

        # 4. Sources Registry count
        sources = get_all_sources()
        self.assertEqual(len(sources), 31)
        self.assertIsNotNone(get_source_by_slug("jobicy"))
        self.assertIsNotNone(get_source_by_slug("wwr"))
        self.assertIsNotNone(get_source_by_slug("arbeitnow"))

    def test_12_category_b_expat_and_relocation_scrapers(self):
        """Verifies Relocate.me and LinkedIn International scrapers produce jobs in the ABROAD bucket with visa/relocation tags."""
        from unittest.mock import MagicMock, patch
        from custom_scraper import RelocateMeScraper, fetch_linkedin_abroad_jobs
        from custom_scraper.adapter import to_job_agent_model
        from processing.prioritization import get_location_bucket, calculate_priority_score
        from config.sources_registry import get_source_by_slug

        # 1. Relocate.me Mock
        sample_html = """
        <div class="jobs-list__job">
            <div class="job__info">
                <div class="job__company text4-medium"><p>Netherlands</p></div>
                <div class="job__company text4-medium"><p>Picnic</p></div>
                <div class="job__title">Software Engineer - Warehouse Systems in Amsterdam</div>
            </div>
            <a href="/netherlands/amsterdam/picnic/software-engineer-10298">Apply</a>
        </div>
        """
        with patch("httpx.Client") as mock_client:
            mock_resp = MagicMock()
            mock_resp.text = sample_html
            mock_resp.raise_for_status.return_value = None
            mock_client.return_value.__enter__.return_value.get.return_value = mock_resp

            scraper = RelocateMeScraper()
            result = scraper.scrape(search_term="python", results_wanted=5)
            self.assertEqual(result.total_found, 1)
            item = result.jobs[0]
            self.assertEqual(item.company, "Picnic")
            self.assertEqual(item.title, "Software Engineer - Warehouse Systems")
            self.assertEqual(item.location, "Amsterdam, Netherlands")

            canon = to_job_agent_model(item)
            canon.source = "relocateme"
            canon.relevance_score = 22.0
            self.assertEqual(get_location_bucket(canon), "ABROAD")

            priority, tier = calculate_priority_score(canon)
            self.assertIn("Visa Sponsor / Relocation", canon.matched_skills)

        # 2. Sources Registry Check
        relocateme_src = get_source_by_slug("relocateme")
        self.assertIsNotNone(relocateme_src)
        self.assertEqual(relocateme_src.name, "Relocate.me")
        self.assertTrue(relocateme_src.enabled)

        linkedin_src = get_source_by_slug("linkedin_abroad")
        self.assertIsNotNone(linkedin_src)
        self.assertEqual(linkedin_src.name, "LinkedIn International")
        self.assertTrue(linkedin_src.enabled)

    def test_18_yc_work_at_a_startup_scraper_and_registry(self):
        """Verifies YC Work at a Startup scraper, payload normalization, and sources registry."""
        from unittest.mock import MagicMock, patch
        from config.sources_registry import get_all_sources, get_source_by_slug
        from custom_scraper import YCWorkAtAStartupScraper, fetch_yc_jobs
        from processing.prioritization import calculate_priority_score

        # 1. Sources Registry check
        all_sources = get_all_sources()
        self.assertEqual(len(all_sources), 31)

        yc_src = get_source_by_slug("yc")
        self.assertIsNotNone(yc_src)
        self.assertEqual(yc_src.name, "Y Combinator Startups")
        self.assertEqual(yc_src.engine_type, "Startup Ecosystem Engine")
        self.assertTrue(yc_src.enabled)

        # 2. Mock scraper execution
        list_html = """
        <div id="JobsV2Page" data-page='{"props":{"jobs":[{"id": 99901}]}}'></div>
        """
        detail_html = """
        <div id="react-component-JobsShow" data-page='{"props":{"job":{"id":99901,"title":"Founding Backend Engineer","location":"Remote","skills":["Python","FastAPI","PostgreSQL"],"minExperience":2,"salaryRange":"$120k - $160k","descriptionHtml":"<p>Building high-throughput APIs in Python and FastAPI.</p>"},"company":{"name":"SuperAI Inc","teamSize":6,"batch":"W24","slug":"superai"},"applyUrl":"https://superai.com/jobs/99901"}}'></div>
        """

        with patch("httpx.Client") as mock_client:
            mock_session = MagicMock()
            mock_client.return_value.__enter__.return_value = mock_session

            def mock_get(url, *args, **kwargs):
                resp = MagicMock()
                resp.status_code = 200
                if "jobs/l/software-engineer" in str(url):
                    resp.text = list_html
                else:
                    resp.text = detail_html
                return resp

            mock_session.get.side_effect = mock_get

            scraper = YCWorkAtAStartupScraper()
            res = scraper.scrape(results_wanted=5)

            self.assertEqual(res.status, "SUCCESS")
            self.assertEqual(res.total_found, 1)
            job = res.jobs[0]
            self.assertEqual(job.id, "yc-99901")
            self.assertEqual(job.company, "SuperAI Inc")
            self.assertEqual(job.title, "Founding Backend Engineer")
            self.assertTrue(job.is_remote)
            self.assertIn("Python", job.description)
            self.assertIn("YC Batch: W24", job.description)
            self.assertEqual(job.raw_data.get("company_size"), "1-10 employees (6)")
            self.assertEqual(job.apply_url, "https://superai.com/jobs/99901")

            # Verify prioritization and boosts
            job.relevance_score = 24.0
            job.matched_skills = ["Python", "FastAPI", "PostgreSQL", "Sweet-Spot Exp (1-3 Yrs)"]
            priority, tier = calculate_priority_score(job)
            self.assertIn("Founding / Core Team", job.matched_skills)
            self.assertIn("Early-Stage Startup (1-50)", job.matched_skills)
            self.assertGreaterEqual(priority, 28.0)
            self.assertIn("TIER 1", tier)


if __name__ == "__main__":
    unittest.main()
