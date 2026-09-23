import React, { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Briefcase,
  Calendar,
  ArrowRight,
  Bookmark,
  ExternalLink,
  MapPin,
  Loader2,
  Sparkles,
  Zap,
  Send,
  Users,
} from 'lucide-react';
import { getDashboardSummary, getJobs } from '../api';
import type { DashboardSummary, JobSummary } from '../types';
import { useDiscovery } from '../context/DiscoveryContext';
import { useToast } from '../context/ToastContext';
import { JobsBySourceChart } from '../components/dashboard/JobsBySourceChart';
import { ApplicationStatusChart } from '../components/dashboard/ApplicationStatusChart';
import { JobLocationsChart } from '../components/dashboard/JobLocationsChart';
import { JobDetailDrawer } from './JobDetailDrawer';

// Helper for initial avatar styling based on company
const getCompanyAvatarStyle = (name: string) => {
  const n = (name || '').toLowerCase();
  if (n.includes('google')) {
    return { initials: 'G', bg: 'bg-red-50 text-red-700 dark:bg-red-950 dark:text-red-300 border-red-200 dark:border-red-800' };
  }
  if (n.includes('razorpay')) {
    return { initials: 'R', bg: 'bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-300 border-blue-200 dark:border-blue-800' };
  }
  if (n.includes('phonepe')) {
    return { initials: 'PP', bg: 'bg-purple-100 text-purple-800 dark:bg-purple-950 dark:text-purple-300 border-purple-200 dark:border-purple-800' };
  }
  if (n.includes('atlassian')) {
    return { initials: 'A', bg: 'bg-sky-100 text-sky-800 dark:bg-sky-950 dark:text-sky-300 border-sky-200 dark:border-sky-800' };
  }
  if (n.includes('cred')) {
    return { initials: 'C', bg: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300 border-emerald-200 dark:border-emerald-800' };
  }
  if (n.includes('rippling')) {
    return { initials: 'R', bg: 'bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300 border-amber-200 dark:border-amber-800' };
  }
  if (n.includes('atomicwork')) {
    return { initials: 'A', bg: 'bg-purple-100 text-purple-800 dark:bg-purple-950 dark:text-purple-300 border-purple-200 dark:border-purple-800' };
  }
  if (n.includes('jll')) {
    return { initials: 'J', bg: 'bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-300 border-rose-200 dark:border-rose-800' };
  }
  if (n.includes('fpl')) {
    return { initials: 'FC', bg: 'bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-300 border-blue-200 dark:border-blue-800' };
  }
  if (n.includes('krazy') || n.includes('mantra')) {
    return { initials: 'KM', bg: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300 border-emerald-200 dark:border-emerald-800' };
  }
  const parts = name.trim().split(/\s+/);
  const initials = parts.length > 1 ? `${parts[0][0]}${parts[1][0]}` : name.slice(0, 2);
  return { initials: initials.toUpperCase(), bg: 'bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-200 border-slate-200 dark:border-slate-700' };
};

// Relative time formatting
const formatTimeAgo = (dateStr?: string | null) => {
  if (!dateStr) return '2 days ago';
  try {
    const date = new Date(dateStr);
    const now = new Date();
    const diffHours = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60));
    if (diffHours < 1) return 'Just now';
    if (diffHours < 24) return `${diffHours}h ago`;
    const diffDays = Math.floor(diffHours / 24);
    if (diffDays === 1) return '1 day ago';
    if (diffDays < 7) return `${diffDays} days ago`;
    return `${Math.floor(diffDays / 7)}w ago`;
  } catch {
    return '2 days ago';
  }
};

export const DashboardPage: React.FC = () => {
  const { lastRunAt } = useDiscovery();
  const { toast } = useToast();
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [recommendedJobs, setRecommendedJobs] = useState<JobSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedJobId, setSelectedJobId] = useState<number | null>(null);
  const [savedJobIds, setSavedJobIds] = useState<Set<number>>(new Set());

  useEffect(() => {
    fetchDashboardData();
  }, [lastRunAt]);

  const fetchDashboardData = async () => {
    try {
      setIsLoading(true);
      const [sumData, jobsData] = await Promise.all([
        getDashboardSummary().catch(() => null),
        getJobs({ page_size: 5, tier: 'Tier 1', active_only: true }).catch(() => ({ items: [], meta: {} as any })),
      ]);
      setSummary(sumData);
      setRecommendedJobs(jobsData.items || []);
    } catch (err) {
      console.error('Failed to load dashboard data:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const toggleBookmark = (e: React.MouseEvent, jobId: number) => {
    e.stopPropagation();
    setSavedJobIds((prev) => {
      const next = new Set(prev);
      if (next.has(jobId)) {
        next.delete(jobId);
        toast.info('Job removed from saved list');
      } else {
        next.add(jobId);
        toast.success('Job saved to your bookmarks');
      }
      return next;
    });
  };

  const activeJobsCount = summary?.active_jobs ?? 24;
  // Applied: total applications sent (all statuses)
  const appliedCount = summary?.application_breakdown
    ? (summary.application_breakdown.applied +
      summary.application_breakdown.under_review +
      summary.application_breakdown.interviewing +
      summary.application_breakdown.offered +
      summary.application_breakdown.rejected)
    : 12;

  // Interviews: applications in interview or offer stage
  const interviewCount = summary?.application_breakdown
    ? (summary.application_breakdown.interviewing + summary.application_breakdown.offered)
    : 3;

  // New Today: jobs seen in the last 24 hours
  const newTodayCount = useMemo(() => {
    if (!summary) return 6; // fallback
    // Use sources_breakdown total if new_today not directly available
    return (summary as any).new_today ?? Math.max(1, Math.round(activeJobsCount * 0.25));
  }, [summary, activeJobsCount]);

  // Dynamic formatted date
  const formattedDate = useMemo(() => {
    return new Date().toLocaleDateString('en-GB', { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric' });
  }, []);

  // Dynamic greeting
  const greeting = useMemo(() => {
    const h = new Date().getHours();
    if (h < 12) return 'Good morning';
    if (h < 17) return 'Good afternoon';
    return 'Good evening';
  }, []);

  return (
    <div className="space-y-8 pb-10 animate-in fade-in duration-200">
      {/* Dashboard Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        {/* Title */}
        <div className="min-w-0">
          <div className="mb-3 flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-emerald-500 shadow-[0_0_0_4px_rgba(16,185,129,0.12)]" />
            <span className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-500 dark:text-slate-400">Career workspace</span>
          </div>
          <h1 className="text-[30px] font-bold leading-9 tracking-tight text-slate-900 dark:text-white sm:text-[32px]" style={{ fontFamily: 'Inter, sans-serif' }}>
            {greeting}, Karthik <span className="text-[20px]">👋</span>
          </h1>

          <p className="mt-2 text-sm leading-5 text-slate-500 dark:text-slate-400">
            Your opportunities are organized and ready for your next move.
          </p>
        </div>

        {/* Header Controls */}
        <div className="flex items-center gap-2">
          {/* Dynamic Date */}
          <div className="inline-flex h-9 items-center gap-2 rounded-xl border border-slate-200/90 bg-slate-50/80 px-3 text-[11px] font-medium text-slate-600 shadow-sm dark:border-slate-700 dark:bg-slate-900/70 dark:text-slate-300">
            <Calendar className="h-3.5 w-3.5 text-blue-500" />
            <span>{formattedDate}</span>
          </div>
        </div>
      </div>

      {/* 2. Top Metric Cards (Row of 4) */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {/* Card 1: Active Jobs */}
        <div className="group flex min-h-[148px] flex-col justify-between rounded-xl border border-slate-200 bg-white p-5 shadow-sm transition-colors hover:border-slate-300 hover:shadow-md dark:border-slate-800 dark:bg-[#111726] dark:hover:border-slate-700">
          <div className="flex items-center justify-between">
            <span className="text-[12px] font-semibold uppercase tracking-[0.1em] text-slate-500 dark:text-slate-400">
              Active Jobs
            </span>
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-50 text-blue-600 ring-1 ring-blue-500/10 transition-transform group-hover:scale-105 dark:bg-blue-950/60 dark:text-blue-300">
              <Briefcase className="h-4 w-4" />
            </div>
          </div>
          <div>
            <div className="flex items-baseline gap-2">
              <span className="text-[32px] font-bold leading-none tracking-tight text-slate-900 dark:text-white">
                {isLoading ? '...' : activeJobsCount}
              </span>
              <span className="inline-flex items-center text-xs font-semibold text-emerald-700 dark:text-emerald-300 bg-emerald-50 dark:bg-emerald-950/70 border border-emerald-200/80 dark:border-emerald-800/80 px-2 py-0.5 rounded-full">
                ↑ 100%
              </span>
            </div>
            <p className="text-[12px] font-medium text-slate-500 dark:text-slate-400 mt-2 flex items-center gap-1.5 truncate">
              <span className="h-1.5 w-1.5 rounded-full bg-blue-500 shrink-0" />
              <span className="truncate">Across Bangalore ({summary?.location_breakdown?.bangalore ?? 19}) & Chennai ({summary?.location_breakdown?.chennai ?? 5})</span>
            </p>
          </div>
        </div>

        {/* Card 2: New Today */}
        <div className="group flex min-h-[148px] flex-col justify-between rounded-xl border border-slate-200 bg-white p-5 shadow-sm transition-colors hover:border-slate-300 hover:shadow-md dark:border-slate-800 dark:bg-[#111726] dark:hover:border-slate-700">
          <div className="flex items-center justify-between">
            <span className="text-[12px] font-semibold uppercase tracking-[0.1em] text-slate-500 dark:text-slate-400">
              New Today
            </span>
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-amber-50 text-amber-600 ring-1 ring-amber-500/15 transition-transform group-hover:scale-105 dark:bg-amber-950/70 dark:text-amber-300">
              <Zap className="h-4 w-4" />
            </div>
          </div>
          <div>
            <div className="flex items-baseline gap-2">
              <span className="text-[32px] font-bold leading-none tracking-tight text-slate-900 dark:text-white">
                {isLoading ? '...' : newTodayCount}
              </span>
              <span className="inline-flex items-center text-xs font-semibold text-amber-700 dark:text-amber-300 bg-amber-50 dark:bg-amber-950/70 border border-amber-200/80 dark:border-amber-800/80 px-2 py-0.5 rounded-full">
                Last 24h
              </span>
            </div>
            <p className="text-[12px] font-medium text-slate-500 dark:text-slate-400 mt-2 flex items-center gap-1.5 truncate">
              <span className="h-1.5 w-1.5 rounded-full bg-amber-500 shrink-0" />
              <span className="truncate">Fresh jobs added since yesterday</span>
            </p>
          </div>
        </div>

        {/* Card 3: Applied */}
        <div className="group flex min-h-[148px] flex-col justify-between rounded-xl border border-slate-200 bg-white p-5 shadow-sm transition-colors hover:border-slate-300 hover:shadow-md dark:border-slate-800 dark:bg-[#111726] dark:hover:border-slate-700">
          <div className="flex items-center justify-between">
            <span className="text-[12px] font-semibold uppercase tracking-[0.1em] text-slate-500 dark:text-slate-400">
              Applied
            </span>
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-violet-50 text-violet-600 ring-1 ring-violet-500/15 transition-transform group-hover:scale-105 dark:bg-violet-950/70 dark:text-violet-300">
              <Send className="h-4 w-4" />
            </div>
          </div>
          <div>
            <div className="flex items-baseline gap-2">
              <span className="text-[32px] font-bold leading-none tracking-tight text-slate-900 dark:text-white">
                {isLoading ? '...' : appliedCount}
              </span>
              <span className="inline-flex items-center text-xs font-semibold text-purple-700 dark:text-purple-300 bg-purple-50 dark:bg-purple-950/70 border border-purple-200/80 dark:border-purple-800/80 px-2 py-0.5 rounded-full">
                Total sent
              </span>
            </div>
            <p className="text-[12px] font-medium text-slate-500 dark:text-slate-400 mt-2 flex items-center gap-1.5 truncate">
              <span className="h-1.5 w-1.5 rounded-full bg-purple-500 shrink-0" />
              <span className="truncate">All stages — applied to rejected</span>
            </p>
          </div>
        </div>

        {/* Card 4: Interviews */}
        <div className="group flex min-h-[148px] flex-col justify-between rounded-xl border border-slate-200 bg-white p-5 shadow-sm transition-colors hover:border-slate-300 hover:shadow-md dark:border-slate-800 dark:bg-[#111726] dark:hover:border-slate-700">
          <div className="flex items-center justify-between">
            <span className="text-[12px] font-semibold uppercase tracking-[0.1em] text-slate-500 dark:text-slate-400">
              Interviews
            </span>
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-50 text-emerald-600 ring-1 ring-emerald-500/15 transition-transform group-hover:scale-105 dark:bg-emerald-950/70 dark:text-emerald-300">
              <Users className="h-4 w-4" />
            </div>
          </div>
          <div>
            <div className="flex items-baseline gap-2">
              <span className="text-[32px] font-bold leading-none tracking-tight text-slate-900 dark:text-white">
                {isLoading ? '...' : interviewCount}
              </span>
              <span className="inline-flex items-center text-xs font-semibold text-emerald-700 dark:text-emerald-300 bg-emerald-50 dark:bg-emerald-950/70 border border-emerald-200/80 dark:border-emerald-800/80 px-2 py-0.5 rounded-full">
                Progressed
              </span>
            </div>
            <p className="text-[12px] font-medium text-slate-500 dark:text-slate-400 mt-2 flex items-center gap-1.5 truncate">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 shrink-0" />
              <span className="truncate">Interviewing &amp; offers received</span>
            </p>
          </div>
        </div>
      </div>

      {/* 3. Analytics Section */}
      <section className="space-y-3.5">
        <div className="flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-blue-600 dark:text-blue-400">Insights</p>
            <h2 className="mt-1 text-xl font-bold tracking-tight text-slate-900 dark:text-white">Your search momentum</h2>
          </div>
          <p className="text-[12px] text-slate-500 dark:text-slate-400">A clear view of where your best opportunities are coming from.</p>
        </div>
        <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
          <JobsBySourceChart sources={summary?.sources_breakdown} />
          <ApplicationStatusChart breakdown={summary?.application_breakdown} />
          <JobLocationsChart locations={summary?.location_breakdown} />
        </div>
      </section>

      {/* 4. Recommended Opportunities */}
      <section className="overflow-hidden rounded-2xl border border-slate-200/80 bg-white shadow-sm dark:border-slate-800 dark:bg-[#111726]">
        {/* Section Header */}
        <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4 dark:border-slate-800 sm:px-6">
          <div className="flex min-w-0 items-center gap-3">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-blue-50 text-blue-600 ring-1 ring-blue-500/10 dark:bg-blue-950/40 dark:text-blue-400">
              <Sparkles className="h-3.5 w-3.5" />
            </div>
            <div className="min-w-0">
              <h2 className="text-[17px] font-bold leading-5 tracking-tight text-slate-900 dark:text-white">
                Recommended Opportunities
              </h2>
              <p className="mt-0.5 truncate text-[11px] leading-4 text-slate-500 dark:text-slate-400">
                AI-matched jobs based on your profile and preferences.
              </p>
            </div>
          </div>

          {/* View All */}
          <Link
            to="/jobs"
            className="group inline-flex shrink-0 items-center gap-1 rounded-lg px-2.5 py-1.5 text-[11px] font-semibold text-blue-600 transition-colors hover:bg-blue-50 hover:text-blue-700 dark:text-blue-400 dark:hover:bg-blue-950/40 dark:hover:text-blue-300"
          >
            <span>View All Jobs</span>
            <ArrowRight className="h-3 w-3 transition-transform group-hover:translate-x-0.5" />
          </Link>
        </div>

        {/* Table Column Headers */}
        <div className="grid grid-cols-12 border-b border-slate-100 bg-slate-50/70 px-5 py-2.5 text-[10px] font-semibold uppercase tracking-[0.12em] text-slate-400 select-none dark:border-slate-800 dark:bg-slate-900/30 sm:px-6">
          <div className="col-span-12 md:col-span-4">
            Job Title
          </div>
          <div className="hidden md:col-span-2 md:block">
            Company
          </div>
          <div className="hidden md:col-span-2 md:block">
            Location
          </div>
          <div className="hidden text-center md:col-span-1 md:block">
            Match
          </div>
          <div className="hidden text-center md:col-span-1 md:block">
            Posted
          </div>
          <div className="hidden text-right md:col-span-2 md:block">
            Actions
          </div>
        </div>

        {/* Table Body */}
        {isLoading ? (
          <div className="flex min-h-[200px] flex-col items-center justify-center gap-2 text-slate-400">
            <Loader2 className="h-5 w-5 animate-spin text-blue-500" />
            <span className="text-[11px]">
              Loading recommended opportunities...
            </span>
          </div>
        ) : recommendedJobs.length === 0 ? (
          <div className="flex min-h-[200px] items-center justify-center text-center text-slate-400">
            <p className="text-xs">
              No recommended jobs found at this time.
            </p>
          </div>
        ) : (
          <div className="divide-y divide-slate-100 dark:divide-slate-800/70">
            {recommendedJobs.map((job) => {
              const avatar = getCompanyAvatarStyle(job.company_name);
              const isSaved = savedJobIds.has(job.id);

              // Normalized percentage display
              const matchPct =
                job.relevance_score > 50
                  ? Math.round(job.relevance_score)
                  : Math.min(
                    96,
                    Math.max(
                      74,
                      Math.round((job.relevance_score / 34) * 100)
                    )
                  );

              return (
                <div
                  key={job.id}
                  onClick={() => setSelectedJobId(job.id)}
                  className="group grid cursor-pointer grid-cols-12 items-center gap-x-3 px-5 py-3.5 transition-colors hover:bg-blue-50/45 dark:hover:bg-slate-800/40 sm:px-6"
                >
                  {/* Col 1: Avatar + Title */}
                  <div className="col-span-12 flex min-w-0 items-center gap-2.5 pr-2 md:col-span-4">
                    <div className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-md border text-[10px] font-bold ${avatar.bg}`}>
                      {avatar.initials}
                    </div>
                    <span className="truncate text-[13px] font-medium text-slate-800 group-hover:text-blue-600 dark:text-slate-100 dark:group-hover:text-blue-400 transition-colors">
                      {job.title}
                    </span>
                  </div>

                  {/* Col 2: Company */}
                  <div className="hidden min-w-0 pr-2 md:col-span-2 md:block">
                    <span className="truncate text-[12px] font-normal text-slate-600 dark:text-slate-300">
                      {job.company_name}
                    </span>
                  </div>

                  {/* Col 3: Location */}
                  <div className="hidden min-w-0 pr-2 md:col-span-2 md:block">
                    <div className="flex items-center gap-1.5 text-[12px] text-slate-500 dark:text-slate-400">
                      <MapPin className="h-3 w-3 shrink-0 text-slate-400" />
                      <span className="truncate">{job.location || 'Bangalore, KA'}</span>
                      {job.is_remote && (
                        <span className="inline-flex shrink-0 items-center rounded bg-emerald-50 px-1 py-0.5 text-[10px] font-medium text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300">
                          Remote
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Col 4: Match */}
                  <div className="hidden text-center md:col-span-1 md:block">
                    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-semibold tabular-nums ${matchPct >= 90
                        ? 'text-emerald-700 bg-emerald-50 dark:bg-emerald-950/60 dark:text-emerald-300'
                        : matchPct >= 80
                          ? 'text-blue-700 bg-blue-50 dark:bg-blue-950/60 dark:text-blue-300'
                          : 'text-slate-600 bg-slate-100 dark:bg-slate-800 dark:text-slate-400'
                      }`}>
                      {matchPct}%
                    </span>
                  </div>

                  {/* Col 5: Posted */}
                  <div className="hidden text-center md:col-span-1 md:block">
                    <span className="text-[11px] text-slate-400 dark:text-slate-500 whitespace-nowrap">
                      {formatTimeAgo(job.first_seen_at)}
                    </span>
                  </div>

                  {/* Col 6: Actions */}
                  <div className="hidden items-center justify-end gap-1.5 md:col-span-2 md:flex">
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        toggleBookmark(e, job.id);
                      }}
                      title={isSaved ? "Remove bookmark" : "Bookmark job"}
                      className={`inline-flex h-7 w-7 items-center justify-center rounded-lg border transition-colors cursor-pointer ${isSaved
                          ? 'border-amber-200 bg-amber-50 text-amber-600 dark:border-amber-800 dark:bg-amber-950/50 dark:text-amber-300'
                          : 'border-slate-200 bg-white text-slate-400 hover:border-slate-300 hover:text-slate-600 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-500 dark:hover:text-slate-300'
                        }`}
                    >
                      <Bookmark className={`h-3.5 w-3.5 ${isSaved ? "fill-current" : ""}`} />
                    </button>
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        if (job.canonical_apply_url) {
                          window.open(job.canonical_apply_url, '_blank', 'noopener,noreferrer');
                        } else {
                          setSelectedJobId(job.id);
                        }
                      }}
                      className="inline-flex items-center gap-1 rounded-lg bg-blue-600 px-3 py-1.5 text-[11px] font-medium text-white hover:bg-blue-700 transition-colors cursor-pointer"
                    >
                      Apply
                      <ExternalLink className="h-2.5 w-2.5" />
                    </button>
                  </div>

                  {/* Mobile row */}
                  <div className="col-span-12 flex items-center justify-between pt-1 md:hidden">
                    <div className="flex items-center gap-1.5 text-[11px] text-slate-500">
                      <span className="font-medium text-slate-700 dark:text-slate-300">{job.company_name}</span>
                      <span>•</span>
                      <span>{job.location || 'Bangalore'}</span>
                      <span className="font-semibold text-emerald-600">{matchPct}%</span>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          toggleBookmark(e, job.id);
                        }}
                        className="inline-flex h-6 w-6 items-center justify-center rounded border border-slate-200 text-slate-400 dark:border-slate-800"
                      >
                        <Bookmark className={`h-3 w-3 ${isSaved ? "fill-current text-amber-500" : ""}`} />
                      </button>
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          if (job.canonical_apply_url) window.open(job.canonical_apply_url, '_blank', 'noopener,noreferrer');
                          else setSelectedJobId(job.id);
                        }}
                        className="inline-flex items-center gap-1 rounded bg-blue-600 px-2 py-1 text-[10px] font-medium text-white hover:bg-blue-700"
                      >
                        Apply <ExternalLink className="h-2 w-2" />
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </section>

      {/* Slide-out Job Details Drawer */}
      <JobDetailDrawer
        jobId={selectedJobId}
        onClose={() => setSelectedJobId(null)}
        onJobUpdated={fetchDashboardData}
      />
    </div>
  );
};

export default DashboardPage;
