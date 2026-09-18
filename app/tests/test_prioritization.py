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

        self.assertEqual(get_location_bucket(j_blr), "BANGALORE")
        self.assertEqual(get_location_bucket(j_maa), "CHENNAI")
        self.assertEqual(get_location_bucket(j_hyd), "OTHER")
        self.assertEqual(get_location_bucket(j_rem), "OTHER")

    def test_location_priority_bonus(self):
        j_blr = Job(id="1", title="Backend", company="A", location="Bengaluru", relevance_score=15.0, apply_type="DIRECT_ATS")
        j_maa = Job(id="2", title="Backend", company="B", location="Chennai", relevance_score=15.0, apply_type="DIRECT_ATS")
        j_hyd = Job(id="3", title="Backend", company="C", location="Hyderabad", relevance_score=15.0, apply_type="DIRECT_ATS")

        score_blr, _ = calculate_priority_score(j_blr)  # 15 + 3 (ATS) + 3.0 (BLR) = 21.0
        score_maa, _ = calculate_priority_score(j_maa)  # 15 + 3 (ATS) + 1.5 (MAA) = 19.5
        score_hyd, _ = calculate_priority_score(j_hyd)  # 15 + 3 (ATS) + 0.5 (OTHER) = 18.5

        self.assertEqual(score_blr, 21.0)
        self.assertEqual(score_maa, 19.5)
        self.assertEqual(score_hyd, 18.5)

    def test_location_quota_selection_distribution(self):
        # Create 50 BLR jobs, 20 MAA jobs, 10 OTHER jobs
        blr_jobs = [Job(id=f"blr_{i}", title="SWE", company="Co", location="Bengaluru", relevance_score=20.0) for i in range(50)]
        maa_jobs = [Job(id=f"maa_{i}", title="SWE", company="Co", location="Chennai", relevance_score=20.0) for i in range(20)]
        other_jobs = [Job(id=f"oth_{i}", title="SWE", company="Co", location="Hyderabad", relevance_score=20.0) for i in range(10)]

        all_pool = blr_jobs + maa_jobs + other_jobs
        selected = select_by_location_quota(all_pool, target_total=50)

        self.assertEqual(len(selected), 50)
        count_blr = sum(1 for j in selected if get_location_bucket(j) == "BANGALORE")
        count_maa = sum(1 for j in selected if get_location_bucket(j) == "CHENNAI")
        count_oth = sum(1 for j in selected if get_location_bucket(j) == "OTHER")

        # Target: 40 BLR (80%), 7-8 MAA (15%), 2-3 OTHER (5%)
        self.assertEqual(count_blr, 40)
        self.assertEqual(count_maa, 7)
        self.assertEqual(count_oth, 3)

    def test_location_quota_rollover_when_secondary_has_fewer_jobs(self):
        # Pool with only 2 Chennai jobs and 1 Other job
        blr_jobs = [Job(id=f"blr_{i}", title="SWE", company="Co", location="Bengaluru", relevance_score=20.0) for i in range(50)]
        maa_jobs = [Job(id=f"maa_{i}", title="SWE", company="Co", location="Chennai", relevance_score=20.0) for i in range(2)]
        other_jobs = [Job(id=f"oth_{i}", title="SWE", company="Co", location="Hyderabad", relevance_score=20.0) for i in range(1)]

        all_pool = blr_jobs + maa_jobs + other_jobs
        selected = select_by_location_quota(all_pool, target_total=50)

        self.assertEqual(len(selected), 50)
        count_blr = sum(1 for j in selected if get_location_bucket(j) == "BANGALORE")
        count_maa = sum(1 for j in selected if get_location_bucket(j) == "CHENNAI")
        count_oth = sum(1 for j in selected if get_location_bucket(j) == "OTHER")

        self.assertEqual(count_maa, 2)
        self.assertEqual(count_oth, 1)
        self.assertEqual(count_blr, 47)  # Rolled over from remaining slots


if __name__ == "__main__":
    unittest.main()
