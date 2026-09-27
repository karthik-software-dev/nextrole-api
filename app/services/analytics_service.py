from collections import Counter
from datetime import datetime, timedelta, timezone
import re
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from schemas.analytics import (
    AgentPerformanceOut,
    AnalyticsKpiData,
    AnalyticsSummaryOut,
    ApplicationAnalyticsOut,
    ApplicationFunnelStepOut,
    ApplicationStatusItemOut,
    ApplicationTimelineItemOut,
    ExperienceDistributionOut,
    JobIntelligenceOut,
    MatchScoreBucketOut,
    SalaryDistributionOut,
    SkillFrequencyOut,
)
from storage.models.application import Application
from storage.models.job import Job
from storage.models.job_source import JobSource


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
}


def parse_salary_lpa(raw: str | None) -> float | None:
    """Parses raw salary string into midpoint Lakhs per Annum (LPA)."""
    if not raw:
        return None
    cleaned = raw.replace("\u20b9", "").replace("INR", "").replace(",", "").strip()
    numbers = [float(n) for n in re.findall(r"\b\d+(?:\.\d+)?\b", cleaned)]
    if not numbers:
        return None
    lpa_numbers = []
    for n in numbers:
        if n >= 100000:
            lpa_numbers.append(n / 100000.0)
        elif n < 200:
            lpa_numbers.append(n)
    if not lpa_numbers:
        return None
    return sum(lpa_numbers) / len(lpa_numbers)


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
        now = datetime.now(timezone.utc)

        if range_val == "today":
            curr_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            curr_end = now
            duration = curr_end - curr_start
            prev_end = curr_start
            prev_start = prev_end - timedelta(days=1)
        elif range_val == "yesterday":
            curr_end = now.replace(hour=0, minute=0, second=0, microsecond=0)
            curr_start = curr_end - timedelta(days=1)
            prev_end = curr_start
            prev_start = prev_end - timedelta(days=1)
        elif range_val == "7d":
            curr_start = now - timedelta(days=7)
            curr_end = now
            prev_end = curr_start
            prev_start = curr_start - timedelta(days=7)
        elif range_val == "month":
            curr_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            curr_end = now
            duration = curr_end - curr_start
            prev_end = curr_start
            prev_start = curr_start - duration
        elif range_val == "custom" and start_date and end_date:
            try:
                curr_start = datetime.fromisoformat(start_date).replace(tzinfo=timezone.utc)
                curr_end = datetime.fromisoformat(end_date).replace(
                    hour=23, minute=59, second=59, tzinfo=timezone.utc
                )
                duration = curr_end - curr_start
                prev_end = curr_start
                prev_start = curr_start - duration
            except Exception:
                curr_start = now - timedelta(days=30)
                curr_end = now
                prev_end = curr_start
                prev_start = curr_start - timedelta(days=30)
        else:  # Default "30d"
            curr_start = now - timedelta(days=30)
            curr_end = now
            prev_end = curr_start
            prev_start = curr_start - timedelta(days=30)

        return curr_start, curr_end, prev_start, prev_end

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
        # Query jobs discovered in current period; if none in period, fall back to active jobs
        jobs_in_window = (
            session.query(Job)
            .filter(
                Job.first_seen_at >= curr_start,
                Job.first_seen_at <= curr_end,
            )
            .all()
        )
        if not jobs_in_window:
            jobs_in_window = session.query(Job).filter(Job.is_active == True).all()

        total_int_jobs = len(jobs_in_window)

        # Match Scores
        score_90_100 = 0
        score_80_89 = 0
        score_70_79 = 0
        score_60_69 = 0
        score_under_60 = 0

        for j in jobs_in_window:
            sc = float(j.relevance_score or 0.0)
            if sc >= 90.0:
                score_90_100 += 1
            elif sc >= 80.0:
                score_80_89 += 1
            elif sc >= 70.0:
                score_70_79 += 1
            elif sc >= 60.0:
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

        # Top Skills extracted from relevant jobs requirements (relevance_score >= 70)
        skills_counter: Counter[str] = Counter()
        for j in jobs_in_window:
            if float(j.relevance_score or 0.0) >= 70.0 and j.matched_skills:
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
            lpa = parse_salary_lpa(j.salary_raw)
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

        job_intelligence = JobIntelligenceOut(
            match_scores=match_scores,
            top_skills=top_skills,
            experience_distribution=experience_distribution,
            salary_distribution=salary_distribution,
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

        application_analytics = ApplicationAnalyticsOut(
            applications_over_time=applications_over_time,
            status_distribution=status_distribution,
            funnel=funnel,
        )

        # ------------------------------------------------------------------
        # 4. AGENT PERFORMANCE (Processing Funnel & Filtering Efficiency)
        # ------------------------------------------------------------------
        # Real database counts in window
        postings_collected = (
            session.query(func.sum(Job.source_count))
            .filter(
                Job.first_seen_at >= curr_start,
                Job.first_seen_at <= curr_end,
            )
            .scalar()
        )
        if not postings_collected:
            postings_collected = session.query(func.sum(Job.source_count)).scalar() or 0

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

        total_collected = max(int(postings_collected), jobs_count)
        duplicates_removed = max(0, total_collected - jobs_count)

        relevant_jobs_count = (
            session.query(func.count(Job.id))
            .filter(
                Job.first_seen_at >= curr_start,
                Job.first_seen_at <= curr_end,
                Job.relevance_score >= 70.0,
            )
            .scalar()
            or 0
        )
        if relevant_jobs_count == 0:
            relevant_jobs_count = (
                session.query(func.count(Job.id))
                .filter(Job.relevance_score >= 70.0)
                .scalar()
                or 0
            )

        actionable_jobs_count = (
            session.query(func.count(Job.id))
            .filter(
                Job.first_seen_at >= curr_start,
                Job.first_seen_at <= curr_end,
                Job.priority_tier.in_(["Tier 1", "TIER 1"]),
            )
            .scalar()
            or 0
        )
        if actionable_jobs_count == 0:
            actionable_jobs_count = (
                session.query(func.count(Job.id))
                .filter(Job.priority_tier.in_(["Tier 1", "TIER 1"]))
                .scalar()
                or 0
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

        agent_performance = AgentPerformanceOut(
            jobs_collected=total_collected,
            jobs_normalized=jobs_count,
            duplicates_removed=duplicates_removed,
            relevant_jobs=relevant_jobs_count,
            actionable_jobs=actionable_jobs_count,
            filtering_efficiency_pct=filtering_efficiency_pct,
            filter_out_pct=filter_out_pct,
            relevance_rate_pct=relevance_rate_pct,
            actionable_rate_pct=actionable_rate_pct,
        )

        return AnalyticsSummaryOut(
            kpis=kpis,
            job_intelligence=job_intelligence,
            application_analytics=application_analytics,
            agent_performance=agent_performance,
        )
