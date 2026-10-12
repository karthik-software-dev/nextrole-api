from collections import Counter
from datetime import datetime, timedelta, timezone
import re
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from schemas.analytics import (
    AgentPerformanceOut,
    PipelineAnalyticsOut,
    AnalyticsKpiData,
    AnalyticsSummaryOut,
    ApplicationAnalyticsOut,
    ApplicationFunnelStepOut,
    ApplicationStatusItemOut,
    ApplicationTimelineItemOut,
    ApplyChannelItemOut,
    ApplyGatewayItemOut,
    ChannelYieldOut,
    ExperienceDistributionOut,
    JobIntelligenceOut,
    JobTitleStatOut,
    LocationStatItemOut,
    MatchScoreBucketOut,
    SalaryDistributionOut,
    SkillFrequencyOut,
    SourceContributionItemOut,
    TierTriageItemOut,
    TopHiringCompanyOut,
    TechStackPairStatOut,
    WorkModeStatOut,
)
from storage.models.application import Application
from storage.models.job import Job
from storage.models.job_source import JobSource
from storage.models.pipeline_run import PipelineRun


STATUS_COLOR_MAP = {
    "applied": "#3B82F6",
    "under_review": "#8B5CF6",
    "interviewing": "#10B981",
    "offered": "#F59E0B",
    "rejected": "#EF4444",
}

STATUS_DISPLAY_NAMES = {
    "applied": "Applied",
    "under_review": "Under Review",
    "interviewing": "Interview",
    "offered": "Offer",
    "rejected": "Rejected",
}

SOURCE_DISPLAY_MAP = {
    "ats": "Direct ATS",
    "indeed": "Indeed",
    "linkedin": "LinkedIn",
    "naukri": "Naukri",
    "apna": "Apna",
    "freshersworld": "Freshersworld",
    "hirist": "Hirist",
    "cutshort": "Cutshort",
    "wellfound": "Wellfound",
    "shine": "Shine",
    "internshala": "Internshala",
    "google_jobs": "Google Jobs",
}

EXCLUDED_HEURISTIC_TAGS = {
    "Full-Stack Synergy",
    "AI-Backend Synergy",
    "Sweet-Spot Exp (1-3 Yrs)",
    "Sweet-Spot Exp (1-5 Yrs)",
    "Senior Exp (4+ Yrs)",
    "Senior Range Penalty",
    "High Exp Penalty",
    "Senior Role Penalty",
    "SDE-1/2 Target Role",
    "Posted < 24h",
    "Posted < 3d",
    "Posted < 7d",
    "Target Comp (5-15 LPA)",
    "Target Comp (7-15 LPA)",
    "High Comp (15+ LPA)",
    "High Comp (12+ LPA)",
    "Comp Disclosed (4-5 LPA)",
    "Comp Disclosed (5-7 LPA)",
    "Comp Disclosed (Global)",
    "Comp Disclosed",
    "Below 4 LPA Floor",
    "Below 5 LPA Floor",
    "Global Remote",
    "Visa Sponsor / Relocation",
    "Remote (India)",
}


from core.date_utils import compute_comparative_date_windows
from processing.salary_parser import parse_salary, parse_salary_lpa
from processing.prioritization import calculate_match_percentage




class AnalyticsService:
    """Service generating comprehensive, non-fabricated metrics for Analytics (Tab 2)."""

    @classmethod
    def get_date_windows(
        cls,
        range_val: str,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> tuple[datetime, datetime, datetime, datetime]:
        """Calculates current period [start, end] and preceding comparison period [prev_start, prev_end]."""
        return compute_comparative_date_windows(
            range_val=range_val,
            start_date=start_date,
            end_date=end_date,
        )

    @classmethod
    def get_analytics_summary(
        cls,
        session: Session,
        range_val: str = "30d",
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> AnalyticsSummaryOut:
        curr_start, curr_end, prev_start, prev_end = cls.get_date_windows(
            range_val, start_date, end_date
        )

        # ------------------------------------------------------------------
        # 1. TOP KPI CARDS (Applications, Interviews, Rates with real comparison)
        # ------------------------------------------------------------------
        # Applications in current window (excluding drafts)
        curr_apps = (
            session.query(Application)
            .filter(
                Application.created_at >= curr_start,
                Application.created_at <= curr_end,
                Application.status != "drafted",
            )
            .all()
        )
        total_apps = len(curr_apps)

        prev_apps = (
            session.query(Application)
            .filter(
                Application.created_at >= prev_start,
                Application.created_at < prev_end,
                Application.status != "drafted",
            )
            .all()
        )
        total_prev_apps = len(prev_apps)

        if total_prev_apps > 0:
            apps_change_pct = round(((total_apps - total_prev_apps) / total_prev_apps) * 100, 1)
        elif total_apps > 0:
            apps_change_pct = 100.0
        else:
            apps_change_pct = 0.0

        # Interview stage applications
        curr_interviews = [a for a in curr_apps if a.status in ("interviewing", "offered")]
        prev_interviews = [a for a in prev_apps if a.status in ("interviewing", "offered")]
        interviews_count = len(curr_interviews)
        prev_interviews_count = len(prev_interviews)

        if prev_interviews_count > 0:
            interviews_change_pct = round(
                ((interviews_count - prev_interviews_count) / prev_interviews_count) * 100, 1
            )
        elif interviews_count > 0:
            interviews_change_pct = 100.0
        else:
            interviews_change_pct = 0.0

        # Response Rate (interview+offered / submitted applications)
        response_rate = (
            round((interviews_count / total_apps) * 100, 1) if total_apps > 0 else 0.0
        )
        response_rate_prev = (
            round((prev_interviews_count / total_prev_apps) * 100, 1) if total_prev_apps > 0 else 0.0
        )
        response_rate_diff_pts = round(response_rate - response_rate_prev, 1)

        # Interview Conversion (offered / interview stage applications)
        curr_offers = [a for a in curr_interviews if a.status == "offered"]
        prev_offers = [a for a in prev_interviews if a.status == "offered"]
        offers_count = len(curr_offers)
        prev_offers_count = len(prev_offers)

        interview_conversion = (
            round((offers_count / interviews_count) * 100, 1) if interviews_count > 0 else 0.0
        )
        interview_conversion_prev = (
            round((prev_offers_count / prev_interviews_count) * 100, 1)
            if prev_interviews_count > 0
            else 0.0
        )
        interview_conversion_diff_pts = round(
            interview_conversion - interview_conversion_prev, 1
        )

        curr_under_review = len([a for a in curr_apps if a.status == "under_review"])
        curr_applied = len([a for a in curr_apps if a.status == "applied"])
        curr_in_interview = len([a for a in curr_apps if a.status == "interviewing"])

        apps_subtext = f"{curr_under_review} Under Review · {curr_applied} Awaiting" if total_apps > 0 else "0 Tracked in period"
        interviews_subtext = f"{curr_in_interview} In Progress · {offers_count} Offered" if interviews_count > 0 else "0 in interview stage"
        response_rate_subtext = f"{interviews_count} positive responses from {total_apps} apps" if total_apps > 0 else "No responses yet"
        conversion_subtext = f"{offers_count} offer from {interviews_count} interview stages" if interviews_count > 0 else "No interviews to convert"

        kpis = AnalyticsKpiData(
            applications=total_apps,
            applications_prev=total_prev_apps,
            applications_change_pct=apps_change_pct,
            applications_subtext=apps_subtext,
            interviews=interviews_count,
            interviews_prev=prev_interviews_count,
            interviews_change_pct=interviews_change_pct,
            interviews_subtext=interviews_subtext,
            response_rate=response_rate,
            response_rate_prev=response_rate_prev,
            response_rate_diff_pts=response_rate_diff_pts,
            response_rate_subtext=response_rate_subtext,
            interview_conversion=interview_conversion,
            interview_conversion_prev=interview_conversion_prev,
            interview_conversion_diff_pts=interview_conversion_diff_pts,
            conversion_subtext=conversion_subtext,
        )

        # ------------------------------------------------------------------
        # 2. JOB INTELLIGENCE (Match Scores, Top Skills, Experience, Salary)
        # ------------------------------------------------------------------
        # Query jobs discovered in current period
        jobs_in_window = (
            session.query(Job)
            .filter(
                Job.first_seen_at >= curr_start,
                Job.first_seen_at <= curr_end,
            )
            .all()
        )

        total_int_jobs = len(jobs_in_window)

        # Match Scores (Normalizing priority score to 0-100% candidate match score)
        score_90_100 = 0
        score_80_89 = 0
        score_70_79 = 0
        score_60_69 = 0
        score_under_60 = 0

        for j in jobs_in_window:
            mp = calculate_match_percentage(float(j.priority_score or j.relevance_score or 0.0))
            if mp >= 90:
                score_90_100 += 1
            elif mp >= 80:
                score_80_89 += 1
            elif mp >= 70:
                score_70_79 += 1
            elif mp >= 60:
                score_60_69 += 1
            else:
                score_under_60 += 1

        def pct(c: int) -> float:
            return round((c / total_int_jobs * 100), 1) if total_int_jobs > 0 else 0.0

        match_scores = [
            MatchScoreBucketOut(range_label="90-100%", count=score_90_100, percentage=pct(score_90_100)),
            MatchScoreBucketOut(range_label="80-89%", count=score_80_89, percentage=pct(score_80_89)),
            MatchScoreBucketOut(range_label="70-79%", count=score_70_79, percentage=pct(score_70_79)),
            MatchScoreBucketOut(range_label="60-69%", count=score_60_69, percentage=pct(score_60_69)),
            MatchScoreBucketOut(range_label="<60%", count=score_under_60, percentage=pct(score_under_60)),
        ]

        # Top Skills extracted from relevant jobs requirements (Match >= 70%)
        skills_counter: Counter[str] = Counter()
        for j in jobs_in_window:
            mp = calculate_match_percentage(float(j.priority_score or j.relevance_score or 0.0))
            if mp >= 70 and j.matched_skills:
                for s in j.matched_skills:
                    if s not in EXCLUDED_HEURISTIC_TAGS:
                        skills_counter[s] += 1

        top_skills = [
            SkillFrequencyOut(skill=s, count=c)
            for s, c in skills_counter.most_common(8)
        ]

        # Experience Distribution
        # Experience Distribution (Tailored to 2-3 yr Python developer search)
        exp_1_2 = 0
        exp_2_3 = 0
        exp_3_4 = 0
        exp_4_plus = 0

        for j in jobs_in_window:
            emin = j.experience_min
            emax = j.experience_max
            if emin is not None:
                if emin <= 1 or (emax is not None and emax <= 2):
                    exp_1_2 += 1
                elif emin == 2 and (emax is None or emax <= 3):
                    exp_2_3 += 1
                elif (emin == 2 and emax == 4) or emin == 3:
                    exp_3_4 += 1
                else:
                    exp_4_plus += 1
            else:
                exp_2_3 += 1

        experience_distribution = [
            ExperienceDistributionOut(level="1-2 yrs", count=exp_1_2),
            ExperienceDistributionOut(level="2-3 yrs", count=exp_2_3),
            ExperienceDistributionOut(level="3-4 yrs", count=exp_3_4),
            ExperienceDistributionOut(level="4+ yrs", count=exp_4_plus),
        ]

        # Salary Distribution (Realistic LPA Midpoints for 2-3 yr Python Developer in India)
        sal_under_8 = 0
        sal_8_12 = 0
        sal_12_16 = 0
        sal_16_22 = 0
        sal_22_plus = 0

        for j in jobs_in_window:
            lpa = parse_salary_lpa(j)
            if lpa is not None:
                if lpa < 8.0:
                    sal_under_8 += 1
                elif lpa < 12.0:
                    sal_8_12 += 1
                elif lpa < 16.0:
                    sal_12_16 += 1
                elif lpa < 22.0:
                    sal_16_22 += 1
                else:
                    sal_22_plus += 1

        salary_distribution = [
            SalaryDistributionOut(bracket="<8 LPA", count=sal_under_8),
            SalaryDistributionOut(bracket="8-12 LPA", count=sal_8_12),
            SalaryDistributionOut(bracket="12-16 LPA", count=sal_12_16),
            SalaryDistributionOut(bracket="16-22 LPA", count=sal_16_22),
            SalaryDistributionOut(bracket="22+ LPA", count=sal_22_plus),
        ]

        # Application Channels & ATS Friction
        chan_counter: Counter[str] = Counter()
        for j in jobs_in_window:
            atype = (j.apply_type or "OTHER").upper()
            if atype == "DIRECT_ATS":
                chan_counter["Direct ATS"] += 1
            elif atype == "COMPANY_CAREERS":
                chan_counter["Company Careers Portal"] += 1
            elif atype in ("AGGREGATOR_REDIRECT", "INDEED_REDIRECT"):
                chan_counter["Aggregator Redirect"] += 1
            else:
                chan_counter["Other Channels"] += 1

        chan_desc = {
            "Direct ATS": "Fastest 1-click apply via Greenhouse, Ashby, Lever",
            "Company Careers Portal": "Direct application on employer careers site",
            "Aggregator Redirect": "Redirected via job aggregator platforms",
            "Other Channels": "External listings or custom portals",
        }

        apply_channels = [
            ApplyChannelItemOut(
                channel=c,
                count=cnt,
                percentage=round((cnt / total_int_jobs * 100), 1) if total_int_jobs > 0 else 0.0,
                description=chan_desc.get(c, ""),
            )
            for c, cnt in chan_counter.most_common()
        ]

        # Top Hiring Companies in window
        comp_counter: Counter[str] = Counter()
        for j in jobs_in_window:
            if j.company and j.company.name:
                comp_counter[j.company.name] += 1

        top_hiring_companies = [
            TopHiringCompanyOut(name=c, active_jobs=cnt)
            for c, cnt in comp_counter.most_common(5)
        ]

        # Locations in window
        loc_map: dict[str, int] = {
            "Bangalore": 0,
            "Chennai": 0,
            "Remote": 0,
            "Abroad": 0,
            "Others": 0,
        }
        for j in jobs_in_window:
            bucket = (j.location_bucket or "").upper()
            if bucket in ("ABROAD", "FOREIGN"):
                loc_map["Abroad"] += 1
            elif j.is_remote:
                loc_map["Remote"] += 1
            elif bucket == "BANGALORE":
                loc_map["Bangalore"] += 1
            elif bucket == "CHENNAI":
                loc_map["Chennai"] += 1
            else:
                loc_map["Others"] += 1

        locations = [
            LocationStatItemOut(name=k, count=v)
            for k, v in loc_map.items()
            if v > 0
        ]
        locations.sort(key=lambda x: x.count, reverse=True)

        # Top Trending Job Titles in window
        title_counter: Counter[str] = Counter()
        for j in jobs_in_window:
            raw_title = j.normalized_title or j.title
            if raw_title:
                clean_t = " ".join(word.capitalize() for word in raw_title.strip().split())
                title_counter[clean_t] += 1

        top_job_titles = [
            JobTitleStatOut(title=t, count=cnt)
            for t, cnt in title_counter.most_common(5)
        ]

        # Work Mode Distribution (3-Way: In-Office / Onsite, Remote, Hybrid)
        hybrid_count = 0
        remote_count = 0
        onsite_count = 0
        for j in jobs_in_window:
            loc = (j.location or "").lower()
            desc_start = (j.description or "").lower()[:200]
            if "hybrid" in loc or "hybrid" in desc_start:
                hybrid_count += 1
            elif j.is_remote or "remote" in loc:
                remote_count += 1
            else:
                onsite_count += 1

        onsite_pct = round((onsite_count / total_int_jobs * 100), 1) if total_int_jobs > 0 else 0.0
        remote_pct = round((remote_count / total_int_jobs * 100), 1) if total_int_jobs > 0 else 0.0
        hybrid_pct = round((hybrid_count / total_int_jobs * 100), 1) if total_int_jobs > 0 else 0.0

        work_modes = [
            WorkModeStatOut(mode="In-Office / Onsite", count=onsite_count, percentage=onsite_pct),
            WorkModeStatOut(mode="Remote", count=remote_count, percentage=remote_pct),
            WorkModeStatOut(mode="Hybrid (Flex Remote + Office)", count=hybrid_count, percentage=hybrid_pct),
        ]

        # Tech Stack Pairs (Skills frequently required alongside Python)
        pair_counter: Counter[str] = Counter()
        for j in jobs_in_window:
            skills = set(j.matched_skills or [])
            for s in skills:
                if s not in EXCLUDED_HEURISTIC_TAGS and "python" not in s.lower():
                    pair_counter[s] += 1

        tech_stack_pairs = [
            TechStackPairStatOut(
                pair=f"Python + {s}",
                skill=s,
                count=cnt,
                percentage=round((cnt / total_int_jobs * 100), 1) if total_int_jobs > 0 else 0.0,
            )
            for s, cnt in pair_counter.most_common(5)
        ]

        job_intelligence = JobIntelligenceOut(
            match_scores=match_scores,
            top_skills=top_skills,
            experience_distribution=experience_distribution,
            salary_distribution=salary_distribution,
            apply_channels=apply_channels,
            top_hiring_companies=top_hiring_companies,
            locations=locations,
            top_job_titles=top_job_titles,
            work_modes=work_modes,
            tech_stack_pairs=tech_stack_pairs,
        )

        # ------------------------------------------------------------------
        # 3. APPLICATION ANALYTICS (Timeline, Status Distribution, Funnel)
        # ------------------------------------------------------------------
        # Group applications in current window by date
        # If fewer than 2 days in curr_apps, we inspect all non-draft applications to provide a rich chart
        target_apps = curr_apps if len(curr_apps) > 0 else (
            session.query(Application).filter(Application.status != "drafted").all()
        )

        date_counts: Counter[str] = Counter()
        for a in target_apps:
            dt = a.created_at.strftime("%Y-%m-%d") if a.created_at else "Unknown"
            date_counts[dt] += 1

        sorted_dates = sorted(date_counts.keys())
        applications_over_time = [
            ApplicationTimelineItemOut(date=d, count=date_counts[d])
            for d in sorted_dates
        ]
        if not applications_over_time:
            today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            applications_over_time = [ApplicationTimelineItemOut(date=today_str, count=0)]

        # Status Distribution of target applications
        status_counter: Counter[str] = Counter()
        for a in target_apps:
            status_counter[a.status] += 1

        tot_target = len(target_apps)
        status_distribution = []
        for key in ["applied", "under_review", "interviewing", "offered", "rejected"]:
            cnt = status_counter[key]
            status_distribution.append(
                ApplicationStatusItemOut(
                    status=STATUS_DISPLAY_NAMES.get(key, key.capitalize()),
                    count=cnt,
                    percentage=round((cnt / tot_target * 100), 1) if tot_target > 0 else 0.0,
                    color=STATUS_COLOR_MAP.get(key, "#94A3B8"),
                )
            )

        # Funnel (Cohort Progression)
        # Applied (base: 100%)
        # Under Review (advanced to review/interview/offer)
        # Interview (advanced to interview/offer)
        # Offer (reached offer)
        f_applied = tot_target
        f_review = sum(
            status_counter[s] for s in ("under_review", "interviewing", "offered")
        )
        f_interview = sum(status_counter[s] for s in ("interviewing", "offered"))
        f_offer = status_counter["offered"]

        funnel = [
            ApplicationFunnelStepOut(
                stage="Applied",
                count=f_applied,
                conversion_rate=100.0,
            ),
            ApplicationFunnelStepOut(
                stage="Under Review",
                count=f_review,
                conversion_rate=round((f_review / f_applied * 100), 1) if f_applied > 0 else 0.0,
            ),
            ApplicationFunnelStepOut(
                stage="Interview",
                count=f_interview,
                conversion_rate=round((f_interview / f_review * 100), 1) if f_review > 0 else 0.0,
            ),
            ApplicationFunnelStepOut(
                stage="Offer",
                count=f_offer,
                conversion_rate=round((f_offer / f_interview * 100), 1) if f_interview > 0 else 0.0,
            ),
        ]

        # Channel Yield & Stale Applications
        channel_applied: Counter[str] = Counter()
        channel_interviews: Counter[str] = Counter()
        stale_count = 0
        seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)

        for a in curr_apps:
            portal = a.portal_type or "Direct ATS"
            channel_applied[portal] += 1
            if a.status in ("interviewing", "offered"):
                channel_interviews[portal] += 1
            if a.status in ("applied", "under_review"):
                app_time = a.applied_at or a.created_at
                if app_time and app_time < seven_days_ago:
                    stale_count += 1

        channel_yield = [
            ChannelYieldOut(
                portal=p,
                applied=cnt,
                interviews=channel_interviews[p],
                conversion_rate=round((channel_interviews[p] / cnt * 100), 1) if cnt > 0 else 0.0,
            )
            for p, cnt in channel_applied.most_common()
        ]

        application_analytics = ApplicationAnalyticsOut(
            applications_over_time=applications_over_time,
            status_distribution=status_distribution,
            funnel=funnel,
            channel_yield=channel_yield,
            stale_applications_count=stale_count,
        )

        # ------------------------------------------------------------------
        # 4. AGENT PERFORMANCE (Processing Funnel & Filtering Efficiency)
        # ------------------------------------------------------------------
        # Real scraper telemetry in window from PipelineRun
        raw_scraped_in_window = (
            session.query(func.sum(PipelineRun.jobs_collected))
            .filter(
                PipelineRun.started_at >= curr_start,
                PipelineRun.started_at <= curr_end,
            )
            .scalar()
        )
        if not raw_scraped_in_window:
            raw_scraped_in_window = session.query(func.sum(PipelineRun.jobs_collected)).scalar() or 0

        jobs_count = (
            session.query(func.count(Job.id))
            .filter(
                Job.first_seen_at >= curr_start,
                Job.first_seen_at <= curr_end,
            )
            .scalar()
            or 0
        )
        if jobs_count == 0:
            jobs_count = session.query(func.count(Job.id)).scalar() or 0

        total_collected = max(int(raw_scraped_in_window), jobs_count)
        duplicates_removed = max(0, total_collected - jobs_count)

        target_pipe_jobs = jobs_in_window if len(jobs_in_window) > 0 else session.query(Job).all()

        relevant_jobs_count = sum(
            1 for j in target_pipe_jobs
            if calculate_match_percentage(float(j.priority_score or j.relevance_score or 0.0)) >= 70
        )

        actionable_jobs_count = sum(
            1 for j in target_pipe_jobs
            if j.priority_tier and "tier 1" in j.priority_tier.lower()
        )

        filtering_efficiency_pct = (
            round((actionable_jobs_count / jobs_count * 100), 1) if jobs_count > 0 else 0.0
        )
        filter_out_pct = (
            round(((jobs_count - actionable_jobs_count) / jobs_count * 100), 1)
            if jobs_count > 0
            else 0.0
        )
        relevance_rate_pct = (
            round((relevant_jobs_count / jobs_count * 100), 1) if jobs_count > 0 else 0.0
        )
        actionable_rate_pct = (
            round((actionable_jobs_count / jobs_count * 100), 1) if jobs_count > 0 else 0.0
        )

        # Ingestion sources breakdown
        source_records = (
            session.query(JobSource.source_name, func.count(JobSource.id))
            .group_by(JobSource.source_name)
            .order_by(func.count(JobSource.id).desc())
            .all()
        )
        total_source_sightings = sum(cnt for _, cnt in source_records) or 1
        sources_breakdown = [
            SourceContributionItemOut(
                source=SOURCE_DISPLAY_MAP.get(src.lower(), src.capitalize()),
                count=cnt,
                percentage=round((cnt / total_source_sightings * 100), 1),
            )
            for src, cnt in source_records
        ]

        # Tier triage breakdown
        t1_count = sum(1 for j in target_pipe_jobs if j.priority_tier and "tier 1" in j.priority_tier.lower())
        t2_count = sum(1 for j in target_pipe_jobs if j.priority_tier and "tier 2" in j.priority_tier.lower())
        t3_count = sum(1 for j in target_pipe_jobs if j.priority_tier and "tier 3" in j.priority_tier.lower())
        tier_tot = max(jobs_count, 1)

        tier_breakdown = [
            TierTriageItemOut(
                tier="Tier 1",
                label="High Priority",
                count=t1_count,
                percentage=round((t1_count / tier_tot * 100), 1),
                color="#8B5CF6",
            ),
            TierTriageItemOut(
                tier="Tier 2",
                label="Solid Match",
                count=t2_count,
                percentage=round((t2_count / tier_tot * 100), 1),
                color="#3B82F6",
            ),
            TierTriageItemOut(
                tier="Tier 3",
                label="Standard",
                count=t3_count,
                percentage=round((t3_count / tier_tot * 100), 1),
                color="#64748B",
            ),
        ]

        dedup_ratio = round(total_collected / max(jobs_count, 1), 1)

        # Ingestion Apply Gateways breakdown
        gw_counter: Counter[str] = Counter()
        for j in target_pipe_jobs:
            atype = (j.apply_type or "OTHER").upper()
            if atype == "COMPANY_CAREERS":
                gw_counter["Company Careers"] += 1
            elif atype == "DIRECT_ATS":
                gw_counter["Direct ATS"] += 1
            elif atype in ("AGGREGATOR_REDIRECT", "INDEED_REDIRECT"):
                gw_counter["Aggregator Redirect"] += 1
            else:
                gw_counter["Direct / Other"] += 1

        gw_colors = {
            "Company Careers": "#3B82F6",
            "Aggregator Redirect": "#8B5CF6",
            "Direct ATS": "#10B981",
            "Direct / Other": "#94A3B8",
        }

        gateways_breakdown = [
            ApplyGatewayItemOut(
                gateway=gw,
                count=cnt,
                percentage=round((cnt / jobs_count * 100), 1) if jobs_count > 0 else 0.0,
                color=gw_colors.get(gw, "#64748B"),
            )
            for gw, cnt in gw_counter.most_common()
        ]

        pipeline_analytics = PipelineAnalyticsOut(
            jobs_collected=total_collected,
            jobs_normalized=jobs_count,
            duplicates_removed=duplicates_removed,
            relevant_jobs=relevant_jobs_count,
            actionable_jobs=actionable_jobs_count,
            filtering_efficiency_pct=filtering_efficiency_pct,
            filter_out_pct=filter_out_pct,
            relevance_rate_pct=relevance_rate_pct,
            actionable_rate_pct=actionable_rate_pct,
            dedup_ratio=dedup_ratio,
            sources_breakdown=sources_breakdown,
            tier_breakdown=tier_breakdown,
            gateways_breakdown=gateways_breakdown,
        )

        return AnalyticsSummaryOut(
            kpis=kpis,
            job_intelligence=job_intelligence,
            application_analytics=application_analytics,
            agent_performance=pipeline_analytics,
            pipeline_analytics=pipeline_analytics,
        )
