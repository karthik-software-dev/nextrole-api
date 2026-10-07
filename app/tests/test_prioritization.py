import unittest
from models.job import Job
from processing.prioritization import (
    TIER_1_LABEL,
    TIER_2_LABEL,
    TIER_3_LABEL,
    calculate_priority_score,
    prioritize_jobs,
    get_location_bucket,
    select_by_location_quota,
)


class TestPrioritization(unittest.TestCase):
    def test_direct_ats_boost(self):
        job = Job(
            id="1",
            title="Backend Engineer",
            company="Co A",
            relevance_score=15.0,
            apply_type="DIRECT_ATS",
        )
        score, _ = calculate_priority_score(job)
        self.assertEqual(score, 18.0)

    def test_aggregator_penalty(self):
        job = Job(
            id="2",
            title="Backend Engineer",
            company="Co B",
            relevance_score=15.0,
            apply_type="AGGREGATOR_REDIRECT",
        )
        score, _ = calculate_priority_score(job)
        self.assertEqual(score, 13.0)

    def test_core_stack_synergy_boost(self):
        job = Job(
            id="3",
            title="Python Developer",
            company="Co C",
            relevance_score=20.0,
            apply_type="COMPANY_CAREERS",
            matched_skills=["Python", "Fastapi", "Postgresql"],
        )
        # 20.0 (base) + 2.0 (Careers) + 2.0 (FastAPI + Postgres) = 24.0
        score, tier = calculate_priority_score(job)
        self.assertEqual(score, 24.0)
        self.assertEqual(tier, TIER_1_LABEL)

    def test_tier_classification(self):
        j_tier1 = Job(id="1", title="A", company="A", relevance_score=20.0, apply_type="DIRECT_ATS")  # 23.0
        j_tier2 = Job(id="2", title="B", company="B", relevance_score=15.0, apply_type="DIRECT_ATS")  # 18.0
        j_tier3 = Job(id="3", title="C", company="C", relevance_score=12.0, apply_type="AGGREGATOR_REDIRECT")  # 10.0

        self.assertEqual(calculate_priority_score(j_tier1)[1], TIER_1_LABEL)
        self.assertEqual(calculate_priority_score(j_tier2)[1], TIER_2_LABEL)
        self.assertEqual(calculate_priority_score(j_tier3)[1], TIER_3_LABEL)

    def test_prioritize_jobs_sorting(self):
        j_low = Job(id="1", title="Low", company="Co 1", relevance_score=12.0, apply_type="AGGREGATOR_REDIRECT")
        j_high = Job(id="2", title="High", company="Co 2", relevance_score=20.0, apply_type="DIRECT_ATS")

        ordered = prioritize_jobs([j_low, j_high])
        self.assertEqual(ordered[0].id, "2")
        self.assertEqual(ordered[1].id, "1")

    def test_location_bucketing(self):
        j_blr = Job(id="1", title="Backend", company="A", location="Bengaluru, Karnataka")
        j_maa = Job(id="2", title="Backend", company="B", location="Chennai, Tamil Nadu")
        j_hyd = Job(id="3", title="Backend", company="C", location="Hyderabad, Telangana")
        j_rem = Job(id="4", title="Backend", company="D", location="Remote, India")
        j_abroad_global = Job(id="5", title="Backend", company="E", location="Worldwide Remote")
        j_abroad_visa = Job(
            id="6",
            title="Backend",
            company="F",
            location="Berlin, Germany",
            description="We offer full visa sponsorship and relocation support.",
        )
        j_foreign = Job(id="7", title="Backend", company="G", location="New York, NY")

        self.assertEqual(get_location_bucket(j_blr), "BANGALORE")
        self.assertEqual(get_location_bucket(j_maa), "CHENNAI")
        self.assertEqual(get_location_bucket(j_hyd), "OTHER")
        self.assertEqual(get_location_bucket(j_rem), "REMOTE_INDIA")
        self.assertEqual(get_location_bucket(j_abroad_global), "ABROAD")
        self.assertEqual(get_location_bucket(j_abroad_visa), "ABROAD")
        self.assertEqual(get_location_bucket(j_foreign), "FOREIGN")

    def test_location_priority_bonus(self):
        j_blr = Job(id="1", title="Backend", company="A", location="Bengaluru", relevance_score=15.0, apply_type="DIRECT_ATS")
        j_maa = Job(id="2", title="Backend", company="B", location="Chennai", relevance_score=15.0, apply_type="DIRECT_ATS")
        j_rem = Job(id="3", title="Backend", company="C", location="Remote, India", relevance_score=15.0, apply_type="DIRECT_ATS")
        j_abroad = Job(id="4", title="Backend", company="D", location="Worldwide Remote", relevance_score=15.0, apply_type="DIRECT_ATS")

        score_blr, _ = calculate_priority_score(j_blr)  # 15 + 3 (ATS) + 3.0 (BLR) = 21.0
        score_maa, _ = calculate_priority_score(j_maa)  # 15 + 3 (ATS) + 1.5 (MAA) = 19.5
        score_rem, _ = calculate_priority_score(j_rem)  # 15 + 3 (ATS) + 2.0 (REMOTE_INDIA) = 20.0
        score_abroad, _ = calculate_priority_score(j_abroad)  # 15 + 3 (ATS) + 2.0 (ABROAD) = 20.0

        self.assertEqual(score_blr, 21.0)
        self.assertEqual(score_maa, 19.5)
        self.assertEqual(score_rem, 20.0)
        self.assertEqual(score_abroad, 20.0)
        self.assertIn("Remote (India)", j_rem.matched_skills)
        self.assertIn("Global Remote", j_abroad.matched_skills)

    def test_location_quota_selection_distribution(self):
        # Create 50 BLR jobs, 20 MAA jobs, 10 REMOTE_INDIA jobs
        blr_jobs = [Job(id=f"blr_{i}", title="SWE", company="Co", location="Bengaluru", relevance_score=20.0) for i in range(50)]
        maa_jobs = [Job(id=f"maa_{i}", title="SWE", company="Co", location="Chennai", relevance_score=20.0) for i in range(20)]
        remote_jobs = [Job(id=f"rem_{i}", title="SWE", company="Co", location="Remote, India", relevance_score=20.0) for i in range(10)]

        all_pool = blr_jobs + maa_jobs + remote_jobs
        selected = select_by_location_quota(all_pool, target_total=50)

        self.assertEqual(len(selected), 50)
        count_blr = sum(1 for j in selected if get_location_bucket(j) == "BANGALORE")
        count_maa = sum(1 for j in selected if get_location_bucket(j) == "CHENNAI")
        count_rem = sum(1 for j in selected if get_location_bucket(j) == "REMOTE_INDIA")

        # Target: 40 BLR (80%), 7-8 MAA (15%), 2-3 REMOTE_INDIA (5%)
        self.assertEqual(count_blr, 40)
        self.assertEqual(count_maa, 7)
        self.assertEqual(count_rem, 3)

    def test_location_quota_rollover_when_secondary_has_fewer_jobs(self):
        # Pool with only 2 Chennai jobs and 1 Remote India job
        blr_jobs = [Job(id=f"blr_{i}", title="SWE", company="Co", location="Bengaluru", relevance_score=20.0) for i in range(50)]
        maa_jobs = [Job(id=f"maa_{i}", title="SWE", company="Co", location="Chennai", relevance_score=20.0) for i in range(2)]
        remote_jobs = [Job(id=f"rem_{i}", title="SWE", company="Co", location="Remote, India", relevance_score=20.0) for i in range(1)]

        all_pool = blr_jobs + maa_jobs + remote_jobs
        selected = select_by_location_quota(all_pool, target_total=50)

        self.assertEqual(len(selected), 50)
        count_blr = sum(1 for j in selected if get_location_bucket(j) == "BANGALORE")
        count_maa = sum(1 for j in selected if get_location_bucket(j) == "CHENNAI")
        count_rem = sum(1 for j in selected if get_location_bucket(j) == "REMOTE_INDIA")

        self.assertEqual(count_maa, 2)
        self.assertEqual(count_rem, 1)
        self.assertEqual(count_blr, 47)  # Rolled over from remaining slots

    def test_compensation_sweet_spot_and_floor(self):
        # 1. Sweet Spot: 5-15 LPA (+2.5 bonus)
        j_target = Job(
            id="target_sal",
            title="Python Developer",
            company="SweetCo",
            location="Bengaluru",
            relevance_score=15.0,
            salary_min=600000.0,
            salary_max=1200000.0,
            salary_currency="INR",
            apply_type="DIRECT_ATS",
        )
        score_target, tier_target = calculate_priority_score(j_target)
        self.assertIn("Target Comp (5-15 LPA)", j_target.matched_skills)

        # 2. Below 4 LPA floor (-4.0 penalty)
        j_low = Job(
            id="low_sal",
            title="Python Developer",
            company="LowCo",
            location="Bengaluru",
            relevance_score=15.0,
            salary_min=200000.0,
            salary_max=350000.0,
            salary_currency="INR",
            apply_type="DIRECT_ATS",
        )
        score_low, tier_low = calculate_priority_score(j_low)
        self.assertIn("Below 4 LPA Floor", j_low.matched_skills)
        self.assertLess(score_low, score_target)

        # 3. Acceptable Baseline: 4-5 LPA (+0.5 bonus)
        j_base = Job(
            id="base_sal",
            title="Python Developer",
            company="BaseCo",
            location="Bengaluru",
            relevance_score=15.0,
            salary_min=400000.0,
            salary_max=480000.0,
            salary_currency="INR",
            apply_type="DIRECT_ATS",
        )
        score_base, tier_base = calculate_priority_score(j_base)
        self.assertIn("Comp Disclosed (4-5 LPA)", j_base.matched_skills)
        self.assertGreater(score_base, score_low)
        self.assertLess(score_base, score_target)

    def test_early_stage_startup_and_founding_boost(self):
        j_founding = Job(
            id="founding_role",
            title="Founding Backend Engineer",
            company="Stealth AI",
            location="Bengaluru",
            relevance_score=20.0,
            apply_type="DIRECT_ATS",
            raw_data={"company_size_label": "1-10 employees"},
        )
        score, tier = calculate_priority_score(j_founding)
        self.assertIn("Founding / Core Team", j_founding.matched_skills)
        self.assertIn("Early-Stage Startup (1-50)", j_founding.matched_skills)
        self.assertEqual(tier, TIER_1_LABEL)


if __name__ == "__main__":
    unittest.main()

