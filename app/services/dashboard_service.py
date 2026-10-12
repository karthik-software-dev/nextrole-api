from datetime import date, datetime, time, timedelta, timezone
from sqlalchemy import cast, Date, func, or_, select
from sqlalchemy.orm import Session

from schemas.dashboard import (
    ApplicationStatusBreakdownOut,
    DailyCadenceRunOut,
    DashboardSummaryOut,
    DedupEfficiencyOut,
    DiscoverySpeedBucketOut,
    DiscoverySpeedOut,
    DiscoveryTrendItemOut,
    LocationBreakdownOut,
    LocationStatItemOut,
    PipelineStatusOut,
    RecentActivityItemOut,
    SourceBreakdownItemOut,
    TopHiringCompanyOut,
)
from schemas.analytics import ExperienceDistributionOut, SalaryDistributionOut
from core.date_utils import resolve_date_range_dates
from processing.salary_parser import parse_salary_lpa
from storage.models.application import Application
from storage.models.application_history import ApplicationHistory
from storage.models.company import Company
from storage.models.job import Job
from storage.models.job_source import JobSource
from storage.repositories.job_repository import JobRepository
from storage.repositories.pipeline_repository import PipelineRepository


class DashboardService:
    """Service computing aggregated metrics and KPI statistics."""

    _summary_cache: dict[str, tuple[float, DashboardSummaryOut]] = {}
    CACHE_TTL_SECONDS = 30.0

    @classmethod
    def clear_cache(cls) -> None:
        """Clears in-memory summary cache."""
        cls._summary_cache.clear()

    @classmethod
    def get_summary(
        cls,
        session: Session,
        date_range: str = "7d",
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> DashboardSummaryOut:
        """Calculates discovery engine and application pipeline statistics."""
        import time as _py_time
        cache_key = f"{date_range}:{start_date}:{end_date}"
        now_ts = _py_time.time()
        if cache_key in cls._summary_cache:
            ts, cached_val = cls._summary_cache[cache_key]
            if now_ts - ts < cls.CACHE_TTL_SECONDS:
                return cached_val

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
        s_date, e_date, start_dt, end_dt = resolve_date_range_dates(
            date_range=date_range,
            start_date=start_date,
            end_date=end_date,
            default_days=7,
        )

        # 4. New jobs within selected period
        new_jobs = session.scalar(
            select(func.count(Job.id))
            .where(Job.first_seen_at >= start_dt, Job.first_seen_at <= end_dt)
        ) or 0
        new_tier1_jobs = session.scalar(
            select(func.count(Job.id))
            .where(
                Job.first_seen_at >= start_dt,
                Job.first_seen_at <= end_dt,
                Job.priority_tier.ilike("%tier 1%")
            )
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

        # 6. Locations breakdown for vertical bar chart (filtered by date window)
        loc_rows = session.execute(
            select(Job.location_bucket, Job.is_remote, func.count(Job.id))
            .where(Job.first_seen_at >= start_dt, Job.first_seen_at <= end_dt)
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

        # 8. Experience & Salary Distributions (filtered by date window) - query only required scalars
        jobs_in_window = session.execute(
            select(
                Job.experience_min,
                Job.experience_max,
                Job.salary_min,
                Job.salary_max,
                Job.salary_raw,
                Job.currency,
            ).where(
                Job.first_seen_at >= start_dt,
                Job.first_seen_at <= end_dt,
            )
        ).all()

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

        # 9. 5-Run Daily Cadence (Partition jobs into 5 standard runner windows)
        now_utc = datetime.now(timezone.utc)
        ist_now = now_utc + timedelta(hours=5, minutes=30)
        target_date = e_date

        target_start_dt = datetime.combine(target_date, time.min, tzinfo=timezone.utc) - timedelta(hours=6)
        target_end_dt = datetime.combine(target_date, time.max, tzinfo=timezone.utc) + timedelta(hours=6)

        job_ts_expr = func.greatest(Job.first_seen_at, Job.last_seen_at)
        day_job_times = session.execute(
            select(job_ts_expr)
            .where(
                Job.is_active.is_(True),
                or_(
                    Job.first_seen_at.between(target_start_dt, target_end_dt),
                    Job.last_seen_at.between(target_start_dt, target_end_dt),
                ),
            )
        ).scalars().all()

        effective_date = target_date
        # If target date has 0 jobs recorded (e.g. today before any runs execute),
        # fallback to the latest active discovery date within the last 7 days so real batch trends are visible
        if target_date == today and not day_job_times:
            latest_ts = session.scalar(select(func.max(job_ts_expr)))
            if latest_ts:
                recent_date = (latest_ts + timedelta(hours=5, minutes=30)).date()
                if (today - recent_date).days <= 7:
                    recent_start = datetime.combine(recent_date, time.min, tzinfo=timezone.utc) - timedelta(hours=6)
                    recent_end = datetime.combine(recent_date, time.max, tzinfo=timezone.utc) + timedelta(hours=6)
                    recent_times = session.execute(
                        select(job_ts_expr)
                        .where(
                            Job.is_active.is_(True),
                            or_(
                                Job.first_seen_at.between(recent_start, recent_end),
                                Job.last_seen_at.between(recent_start, recent_end),
                            ),
                        )
                    ).scalars().all()
                    if recent_times:
                        day_job_times = recent_times
                        effective_date = recent_date

        slot_defs = [
            {"run_number": 1, "time_slot": "09:00 AM", "label": "Morning Market Sync", "hour_max": 11, "act_hour": 9},
            {"run_number": 2, "time_slot": "12:00 PM", "label": "Mid-day Ingestion", "hour_max": 14, "act_hour": 12},
            {"run_number": 3, "time_slot": "03:00 PM", "label": "Afternoon Crawl", "hour_max": 17, "act_hour": 15},
            {"run_number": 4, "time_slot": "06:00 PM", "label": "Evening Sync", "hour_max": 20, "act_hour": 18},
            {"run_number": 5, "time_slot": "09:00 PM", "label": "Night Roundup", "hour_max": 24, "act_hour": 21},
        ]

        slot_counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        for jt in day_job_times:
            if jt:
                jt_ist = jt + timedelta(hours=5, minutes=30)
                if jt_ist.date() == effective_date:
                    h = jt_ist.hour
                    for sdef in slot_defs:
                        if h < sdef["hour_max"]:
                            slot_counts[sdef["run_number"]] += 1
                            break

        curr_ist_hour = ist_now.hour if effective_date == today else 24
        daily_cadence: list[DailyCadenceRunOut] = []
        running_cum = 0

        for sdef in slot_defs:
            rnum = sdef["run_number"]
            cnt = slot_counts[rnum]
            running_cum += cnt

            if effective_date < today:
                status = "completed"
            elif curr_ist_hour >= sdef["hour_max"]:
                status = "completed"
            elif curr_ist_hour >= sdef["act_hour"]:
                status = "active"
            else:
                status = "scheduled"

            daily_cadence.append(
                DailyCadenceRunOut(
                    run_number=rnum,
                    time_slot=sdef["time_slot"],
                    label=sdef["label"],
                    status=status,
                    jobs_collected=cnt,
                    cumulative_jobs=running_cum,
                    runner="GitHub Actions Runner",
                )
            )

        # Telemetry: query latest pipeline run from PostgreSQL
        latest_pipe_rec = PipelineRepository.get_latest_pipeline_run(session)
        latest_pipe_out = (
            PipelineStatusOut(
                id=latest_pipe_rec.id,
                pipeline_id=latest_pipe_rec.pipeline_id,
                pipeline_iid=latest_pipe_rec.pipeline_iid,
                pipeline_url=latest_pipe_rec.pipeline_url,
                source=latest_pipe_rec.source,
                status=latest_pipe_rec.status,
                triggered_by=latest_pipe_rec.triggered_by,
                jobs_collected=latest_pipe_rec.jobs_collected,
                jobs_synced=latest_pipe_rec.jobs_synced,
                duration_seconds=float(latest_pipe_rec.duration_seconds) if latest_pipe_rec.duration_seconds else None,
                started_at=latest_pipe_rec.started_at,
                completed_at=latest_pipe_rec.completed_at,
            )
            if latest_pipe_rec
            else None
        )

        # 10. Top Hiring Companies (Hiring velocity leaderboard preview)
        top_comp_rows = session.execute(
            select(
                Company.name,
                func.count(Job.id).label("job_count"),
                func.bool_or(Job.is_remote).label("has_remote")
            )
            .join(Company, Job.company_id == Company.id)
            .where(Job.first_seen_at >= start_dt, Job.first_seen_at <= end_dt)
            .group_by(Company.name)
            .order_by(func.count(Job.id).desc())
            .limit(5)
        ).all()

        top_hiring_companies: list[TopHiringCompanyOut] = []
        for cname, ccount, cremote in top_comp_rows:
            locs: list[str] = ["Remote"] if cremote else []
            top_hiring_companies.append(
                TopHiringCompanyOut(
                    name=cname,
                    job_count=ccount,
                    locations=locs,
                    is_remote=bool(cremote),
                )
            )

        # 11. Deduplication & Spam Suppression Efficiency Metrics
        active_jobs_cnt = job_stats["active_jobs"]
        dedup_row = session.execute(
            select(
                func.count(Job.id).filter(Job.source_count > 1),
                func.coalesce(func.sum(Job.source_count - 1), 0),
            )
        ).first()
        multi_source_cnt = (dedup_row[0] if dedup_row else 0) or 0
        duplicates_filtered_cnt = (dedup_row[1] if dedup_row else 0) or 0
        total_sightings_cnt = active_jobs_cnt + duplicates_filtered_cnt
        suppression_rate = (
            round((duplicates_filtered_cnt / total_sightings_cnt) * 100, 1)
            if total_sightings_cnt > 0
            else 0.0
        )
        dedup_efficiency = DedupEfficiencyOut(
            canonical_jobs=active_jobs_cnt,
            multi_source_jobs=multi_source_cnt,
            duplicates_filtered=duplicates_filtered_cnt,
            suppression_rate_pct=suppression_rate,
        )

        # 12. Discovery Speed Advantage (Lead Time from Employer Publish to Ingestion)
        src_rows = session.execute(
            select(JobSource.first_seen_at, JobSource.source_posted_at)
            .join(Job, JobSource.job_id == Job.id)
            .where(Job.first_seen_at >= start_dt, Job.first_seen_at <= end_dt)
            .limit(1000)
        ).all()

        parsed_lags: list[float] = []
        for fs, sp in src_rows:
            if fs and sp:
                try:
                    clean_str = sp.replace("Z", "+00:00")
                    posted = datetime.fromisoformat(clean_str)
                    if posted.tzinfo is None:
                        posted = posted.replace(tzinfo=timezone.utc)
                    diff_h = (fs - posted).total_seconds() / 3600.0
                    if diff_h >= 0:
                        parsed_lags.append(diff_h)
                except Exception:
                    pass

        fresh_lags = [x for x in parsed_lags if x < 24.0]
        if len(fresh_lags) > 0:
            u1_cnt = sum(1 for x in fresh_lags if x < 1.0)
            u4_cnt = sum(1 for x in fresh_lags if 1.0 <= x < 4.0)
            u12_cnt = sum(1 for x in fresh_lags if 4.0 <= x < 12.0)
            u24_cnt = sum(1 for x in fresh_lags if 12.0 <= x < 24.0)
            tot_measured = len(fresh_lags)
            avg_lat = round(sum(fresh_lags) / tot_measured, 1)
        else:
            u1_cnt = 0
            u4_cnt = 0
            u12_cnt = 0
            u24_cnt = 0
            tot_measured = 0
            avg_lat = 0.0

        under_4h_cnt = u1_cnt + u4_cnt
        captured_pct = round((under_4h_cnt / tot_measured) * 100, 1) if tot_measured > 0 else 0.0

        discovery_speed = DiscoverySpeedOut(
            captured_under_4h_pct=captured_pct,
            avg_latency_hours=avg_lat,
            total_measured_jobs=tot_measured,
            buckets=[
                DiscoverySpeedBucketOut(
                    key="under_1h",
                    label="Under 1 Hour",
                    tag="Ultra-Fresh",
                    count=u1_cnt,
                    percentage=round((u1_cnt / tot_measured) * 100, 1) if tot_measured > 0 else 0.0,
                ),
                DiscoverySpeedBucketOut(
                    key="one_to_4h",
                    label="1 - 4 Hours",
                    tag="Early Mover",
                    count=u4_cnt,
                    percentage=round((u4_cnt / tot_measured) * 100, 1) if tot_measured > 0 else 0.0,
                ),
                DiscoverySpeedBucketOut(
                    key="four_to_12h",
                    label="4 - 12 Hours",
                    tag="Same Day",
                    count=u12_cnt,
                    percentage=round((u12_cnt / tot_measured) * 100, 1) if tot_measured > 0 else 0.0,
                ),
                DiscoverySpeedBucketOut(
                    key="twelve_to_24h",
                    label="12 - 24 Hours",
                    tag="Standard",
                    count=u24_cnt,
                    percentage=round((u24_cnt / tot_measured) * 100, 1) if tot_measured > 0 else 0.0,
                ),
            ],
        )

        # 13. Sources Breakdown within window
        src_window_rows = session.execute(
            select(JobSource.source_name, func.count(JobSource.id))
            .where(JobSource.first_seen_at >= start_dt, JobSource.first_seen_at <= end_dt)
            .group_by(JobSource.source_name)
            .order_by(func.count(JobSource.id).desc())
        ).all()
        sources_breakdown = [
            SourceBreakdownItemOut(name=sname.title() if sname else "Other", count=scnt)
            for sname, scnt in src_window_rows
        ]

        summary_out = DashboardSummaryOut(
            total_jobs=job_stats["total_jobs"],
            active_jobs=job_stats["active_jobs"],
            inactive_jobs=job_stats["inactive_jobs"],
            tier1_jobs=job_stats["tier1_jobs"],
            tier2_jobs=job_stats["tier2_jobs"],
            total_companies=job_stats["total_companies"],
            total_sources=job_stats["total_sources"],
            location_breakdown=loc_breakdown,
            application_breakdown=app_breakdown,
            sources_breakdown=sources_breakdown,
            new_jobs=new_jobs,
            new_tier1_jobs=new_tier1_jobs,
            discovery_trend=discovery_trend,
            locations_breakdown=locations_breakdown,
            recent_activities=combined_activities,
            experience_distribution=experience_distribution,
            salary_distribution=salary_distribution,
            daily_cadence=daily_cadence,
            top_hiring_companies=top_hiring_companies,
            dedup_efficiency=dedup_efficiency,
            latest_pipeline=latest_pipe_out,
            discovery_speed=discovery_speed,
        )
        cls._summary_cache[cache_key] = (now_ts, summary_out)
        return summary_out
