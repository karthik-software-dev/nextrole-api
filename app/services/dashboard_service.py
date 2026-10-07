from datetime import date, datetime, time, timedelta, timezone
from sqlalchemy import cast, Date, func, select
from sqlalchemy.orm import Session

from schemas.dashboard import (
    ApplicationStatusBreakdownOut,
    DashboardSummaryOut,
    DiscoveryTrendItemOut,
    LocationBreakdownOut,
    LocationStatItemOut,
    RecentActivityItemOut,
)
from schemas.analytics import ExperienceDistributionOut, SalaryDistributionOut
from processing.salary_parser import parse_salary_lpa
from storage.models.application import Application
from storage.models.application_history import ApplicationHistory
from storage.models.job import Job
from storage.models.job_source import JobSource
from storage.repositories.job_repository import JobRepository


class DashboardService:
    """Service computing aggregated metrics and KPI statistics."""

    @staticmethod
    def get_summary(
        session: Session,
        date_range: str = "7d",
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> DashboardSummaryOut:
        """Calculates discovery engine and application pipeline statistics."""
        # 1. Job & Company stats
        job_stats = JobRepository.get_database_stats(session)

        # 2. Application breakdown by status
        app_counts = dict(
            session.execute(
                select(Application.status, func.count(Application.id))
                .where(Application.is_active.is_(True))
                .group_by(Application.status)
            ).all()
        )

        app_breakdown = ApplicationStatusBreakdownOut(
            drafted=app_counts.get("drafted", 0),
            applied=app_counts.get("applied", 0),
            under_review=app_counts.get("under_review", 0),
            interviewing=app_counts.get("interviewing", 0),
            offered=app_counts.get("offered", 0),
            rejected=app_counts.get("rejected", 0),
        )

        loc_breakdown = LocationBreakdownOut(
            bangalore=job_stats.get("bangalore_jobs", 0),
            chennai=job_stats.get("chennai_jobs", 0),
            remote=job_stats.get("remote_jobs", 0),
            abroad=job_stats.get("abroad_jobs", 0),
            other=job_stats.get("other_jobs", 0),
        )

        # 3. Determine date window
        today = date.today()
        if date_range == "custom" and start_date and end_date:
            try:
                s_date = date.fromisoformat(start_date)
                e_date = date.fromisoformat(end_date)
            except Exception:
                s_date = today - timedelta(days=6)
                e_date = today
            if s_date > e_date:
                s_date, e_date = e_date, s_date
        elif date_range == "today":
            s_date = today
            e_date = today
        elif date_range == "yesterday":
            s_date = today - timedelta(days=1)
            e_date = s_date
        elif date_range == "30d":
            s_date = today - timedelta(days=29)
            e_date = today
        elif date_range == "month":
            s_date = today.replace(day=1)
            e_date = today
        else:  # default "7d"
            s_date = today - timedelta(days=6)
            e_date = today

        start_dt = datetime.combine(s_date, time.min, tzinfo=timezone.utc)
        end_dt = datetime.combine(e_date, time.max, tzinfo=timezone.utc)

        # 4. New jobs within selected period
        new_jobs = session.scalar(
            select(func.count(Job.id))
            .where(Job.first_seen_at >= start_dt, Job.first_seen_at <= end_dt)
        ) or 0

        # 5. Discovery Trend across window
        daily_counts = dict(
            session.execute(
                select(cast(Job.first_seen_at, Date), func.count(Job.id))
                .where(Job.first_seen_at >= start_dt, Job.first_seen_at <= end_dt)
                .group_by(cast(Job.first_seen_at, Date))
            ).all()
        )
        num_days = max(1, (e_date - s_date).days + 1)
        if num_days > 90:
            num_days = 90
            s_date = e_date - timedelta(days=89)

        discovery_trend = [
            DiscoveryTrendItemOut(
                date=(s_date + timedelta(days=i)).strftime("%b %d"),
                count=daily_counts.get(s_date + timedelta(days=i), 0),
            )
            for i in range(num_days)
        ]

        # 6. Locations breakdown for vertical bar chart
        loc_rows = session.execute(
            select(Job.location_bucket, Job.is_remote, func.count(Job.id))
            .where(Job.is_active.is_(True))
            .group_by(Job.location_bucket, Job.is_remote)
        ).all()
        loc_map: dict[str, int] = {
            "Bangalore": 0,
            "Chennai": 0,
            "Remote": 0,
            "Abroad": 0,
            "Others": 0,
        }
        for bucket, is_rem, cnt in loc_rows:
            if bucket in ("ABROAD", "FOREIGN"):
                loc_map["Abroad"] += cnt
            elif is_rem:
                loc_map["Remote"] += cnt
            elif bucket == "BANGALORE":
                loc_map["Bangalore"] += cnt
            elif bucket == "CHENNAI":
                loc_map["Chennai"] += cnt
            else:
                loc_map["Others"] += cnt

        locations_breakdown = [
            LocationStatItemOut(name=k, count=v)
            for k, v in loc_map.items()
            if v > 0
        ]
        locations_breakdown.sort(key=lambda x: x.count, reverse=True)

        # 7. Recent activity from real records
        app_activities: list[RecentActivityItemOut] = []
        histories = session.execute(
            select(ApplicationHistory, Application, Job)
            .join(Application, ApplicationHistory.application_id == Application.id)
            .join(Job, Application.job_id == Job.id)
            .order_by(ApplicationHistory.changed_at.desc())
            .limit(4)
        ).all()

        for h, a, j in histories:
            cname = j.company.name if j.company else "Company"
            if h.new_status == "applied":
                title = f"Application submitted to {cname}"
                atype = "application"
            elif h.new_status in ("interviewing", "interview"):
                title = f"Application in interview stage at {cname}"
                atype = "interview"
            elif h.new_status in ("offered", "offer"):
                title = f"Offer received from {cname}"
                atype = "offer"
            elif h.new_status == "rejected":
                title = f"Application closed at {cname}"
                atype = "rejected"
            elif h.new_status == "under_review":
                title = f"Application under review at {cname}"
                atype = "review"
            else:
                title = f"Application for {j.title} updated to {h.new_status}"
                atype = "application"

            app_activities.append(
                RecentActivityItemOut(
                    id=f"app-{h.id}",
                    title=title,
                    timestamp=h.changed_at,
                    activity_type=atype,
                )
            )

        disc_activities: list[RecentActivityItemOut] = []
        hm_count = session.scalar(
            select(func.count(Job.id))
            .where(Job.priority_tier.ilike("%tier 1%"))
        ) or 0
        latest_job_time = session.scalar(select(func.max(Job.first_seen_at)))
        if hm_count > 0 and latest_job_time:
            disc_activities.append(
                RecentActivityItemOut(
                    id="high-match-discovery",
                    title=f"{hm_count} new high-match jobs discovered",
                    timestamp=latest_job_time,
                    activity_type="discovery",
                )
            )

        src_rows = session.execute(
            select(JobSource.source_name, func.count(JobSource.id), func.max(JobSource.first_seen_at))
            .group_by(JobSource.source_name)
            .order_by(func.count(JobSource.id).desc())
            .limit(3)
        ).all()
        for sname, scnt, stime in src_rows:
            if stime:
                s_suffix = "s" if scnt > 1 else ""
                disc_activities.append(
                    RecentActivityItemOut(
                        id=f"src-{sname}",
                        title=f"{scnt} new job{s_suffix} from {sname}",
                        timestamp=stime,
                        activity_type="source",
                    )
                )

        combined_activities = app_activities[:3] + disc_activities[:3]
        combined_activities.sort(key=lambda x: x.timestamp, reverse=True)

        # 8. Experience & Salary Distributions (filtered by date window, fallback to active jobs)
        jobs_in_window = (
            session.query(Job)
            .filter(
                Job.first_seen_at >= start_dt,
                Job.first_seen_at <= end_dt,
            )
            .all()
        )
        if not jobs_in_window:
            jobs_in_window = session.query(Job).filter(Job.is_active.is_(True)).all()

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
                elif 8.0 <= lpa < 12.0:
                    sal_8_12 += 1
                elif 12.0 <= lpa < 16.0:
                    sal_12_16 += 1
                elif 16.0 <= lpa < 22.0:
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

        return DashboardSummaryOut(
            total_jobs=job_stats["total_jobs"],
            active_jobs=job_stats["active_jobs"],
            inactive_jobs=job_stats["inactive_jobs"],
            tier1_jobs=job_stats["tier1_jobs"],
            tier2_jobs=job_stats["tier2_jobs"],
            total_companies=job_stats["total_companies"],
            total_sources=job_stats["total_sources"],
            location_breakdown=loc_breakdown,
            application_breakdown=app_breakdown,
            sources_breakdown=job_stats.get("sources_breakdown", []),
            new_jobs=new_jobs,
            discovery_trend=discovery_trend,
            locations_breakdown=locations_breakdown,
            recent_activities=combined_activities,
            experience_distribution=experience_distribution,
            salary_distribution=salary_distribution,
        )
