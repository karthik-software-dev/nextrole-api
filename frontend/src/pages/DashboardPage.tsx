import React, { useEffect, useMemo, useState, useRef } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  Briefcase,
  Calendar,
  ChevronRight,
  ChevronDown,
  RotateCw,
  Plus,
  Send,
  Bookmark,
  ExternalLink,
  Loader2,
  Sparkles,
} from 'lucide-react';
import { getDashboardSummary, getJobs } from '../api';
import type { DashboardSummary, JobSummary } from '../types';
import { useDiscovery } from '../context/DiscoveryContext';
import { useToast } from '../context/ToastContext';
import { JobsDiscoveredChart } from '../components/dashboard/JobsDiscoveredChart';
import { ApplicationStatusChart } from '../components/dashboard/ApplicationStatusChart';
import { JobsBySourceChart } from '../components/dashboard/JobsBySourceChart';
import { JobLocationsChart } from '../components/dashboard/JobLocationsChart';
import { RecentActivity } from '../components/dashboard/RecentActivity';
import { JobDetailDrawer } from './JobDetailDrawer';

// Helper for company initial avatar
const getCompanyAvatarStyle = (name: string) => {
  const n = (name || '').toLowerCase();
  if (n.includes('abnormal')) {
    return { initials: 'A', bg: 'bg-indigo-600 text-white' };
  }
  if (n.includes('zeta')) {
    return { initials: 'Z', bg: 'bg-slate-700 text-white dark:bg-slate-600' };
  }
  if (n.includes('google')) {
    return { initials: 'G', bg: 'bg-red-500 text-white' };
  }
  if (n.includes('razorpay')) {
    return { initials: 'R', bg: 'bg-indigo-600 text-white' };
  }
  if (n.includes('cred')) {
    return { initials: 'C', bg: 'bg-emerald-600 text-white' };
  }
  const parts = name.trim().split(/\s+/);
  const initials = parts.length > 1 ? `${parts[0][0]}${parts[1][0]}` : name.slice(0, 2);
  return { initials: initials.toUpperCase(), bg: 'bg-rose-500 text-white' };
};

const DATE_RANGE_OPTIONS = [
  { label: 'Today', value: 'today' },
  { label: 'Yesterday', value: 'yesterday' },
  { label: 'Last 7 Days', value: '7d' },
  { label: 'Last 30 Days', value: '30d' },
  { label: 'This Month', value: 'month' },
  { label: 'Custom Range', value: 'custom' },
];

export const DashboardPage: React.FC = () => {
  const navigate = useNavigate();
  const { lastRunAt, isDiscovering, discoveryStatusText } = useDiscovery();
  const { toast } = useToast();

  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [recommendedJobs, setRecommendedJobs] = useState<JobSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [selectedJobId, setSelectedJobId] = useState<number | null>(null);
  const [savedJobIds, setSavedJobIds] = useState<Set<number>>(new Set());

  // Date Range State
  const [selectedRange, setSelectedRange] = useState<string>('7d');
  const [isDateMenuOpen, setIsDateMenuOpen] = useState(false);
  const [customStartDate, setCustomStartDate] = useState<string>('');
  const [customEndDate, setCustomEndDate] = useState<string>('');
  const [showCustomInputs, setShowCustomInputs] = useState(false);
  const dateMenuRef = useRef<HTMLDivElement>(null);

  // Close dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dateMenuRef.current && !dateMenuRef.current.contains(e.target as Node)) {
        setIsDateMenuOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Fetch data on mount or when discovery finishes
  useEffect(() => {
    fetchDashboardData(selectedRange, customStartDate, customEndDate);
  }, [lastRunAt]);

  const fetchDashboardData = async (
    rangeVal: string = selectedRange,
    startD?: string,
    endD?: string
  ) => {
    try {
      setIsRefreshing(true);
      const queryParams = {
        range: rangeVal,
        ...(rangeVal === 'custom' && startD ? { start_date: startD } : {}),
        ...(rangeVal === 'custom' && endD ? { end_date: endD } : {}),
      };

      const [sumData, jobsData] = await Promise.all([
        getDashboardSummary(queryParams).catch(() => null),
        // Recommended jobs are independent of historical date filter
        getJobs({ page_size: 3, tier: 'Tier 1', active_only: true }).catch(() => ({
          items: [],
          meta: {} as any,
        })),
      ]);

      setSummary(sumData);
      setRecommendedJobs(jobsData.items || []);
    } catch (err) {
      console.error('Failed to load dashboard data:', err);
      toast.error('Failed to refresh dashboard metrics');
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  };

  const handleRangeSelect = (value: string) => {
    setSelectedRange(value);
    if (value === 'custom') {
      setShowCustomInputs(true);
      setIsDateMenuOpen(false);
    } else {
      setShowCustomInputs(false);
      setIsDateMenuOpen(false);
      fetchDashboardData(value);
    }
  };

  const applyCustomRange = () => {
    if (customStartDate && customEndDate) {
      fetchDashboardData('custom', customStartDate, customEndDate);
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

  // Dynamic greeting based on current local hour
  const greeting = useMemo(() => {
    const h = new Date().getHours();
    if (h < 12) return 'Good morning';
    if (h < 17) return 'Good afternoon';
    return 'Good evening';
  }, []);

  // Selected range display label
  const selectedRangeLabel = useMemo(() => {
    const found = DATE_RANGE_OPTIONS.find((opt) => opt.value === selectedRange);
    return found ? found.label : 'Last 7 Days';
  }, [selectedRange]);

  // Real KPI Metrics derived strictly from real DB records
  const activeJobsCount = summary?.active_jobs ?? 0;
  const newJobsCount = summary?.new_jobs ?? summary?.active_jobs ?? 0;
  const highMatchCount = summary?.tier1_jobs ?? 0;

  const appBreakdown = summary?.application_breakdown;
  const appliedTotal = appBreakdown
    ? appBreakdown.applied +
    appBreakdown.under_review +
    appBreakdown.interviewing +
    appBreakdown.offered +
    appBreakdown.rejected
    : 0;

  const underReviewCount = appBreakdown?.under_review ?? 0;
  const awaitingCount = appBreakdown?.applied ?? 0;

  const interviewsTotal = appBreakdown
    ? appBreakdown.interviewing + appBreakdown.offered
    : 0;
  const upcomingInterviews = appBreakdown?.interviewing ?? 0;
  const completedInterviews = appBreakdown?.offered ?? 0;

  const blrCount = summary?.location_breakdown?.bangalore ?? 0;
  const remoteCount = summary?.location_breakdown?.remote ?? 0;

  return (
    <div className="space-y-6 pb-12">
      {/* -------------------------------------------------- */}
      {/* HEADER                                             */}
      {/* -------------------------------------------------- */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-[28px] sm:text-[32px] font-bold tracking-tight text-slate-900 dark:text-white flex items-center gap-2">
            <span>{greeting}, Karthik!</span>
            <span role="img" aria-label="wave">👋</span>
          </h1>
          <p className="mt-1 text-[13.5px] text-slate-800 dark:text-slate-300">
            Here's what's happening with your job search.
          </p>
        </div>

        {/* Controls: Date Range Dropdown + Refresh */}
        <div className="flex items-center gap-2.5">
          {/* Date Range Dropdown */}
          <div className="relative" ref={dateMenuRef}>
            <button
              type="button"
              onClick={() => setIsDateMenuOpen(!isDateMenuOpen)}
              className="inline-flex h-9 items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 text-xs font-semibold text-slate-700 shadow-xs hover:bg-slate-50 dark:border-slate-800 dark:bg-[#111726] dark:text-slate-200 dark:hover:bg-slate-800/60 transition-colors cursor-pointer"
            >
              <Calendar className="h-3.5 w-3.5 text-slate-500" />
              <span>{selectedRangeLabel}</span>
              <ChevronDown className="h-3.5 w-3.5 text-slate-400" />
            </button>

            {isDateMenuOpen && (
              <div className="absolute right-0 mt-1.5 w-44 rounded-xl border border-slate-200 bg-white py-1 shadow-lg dark:border-slate-800 dark:bg-[#111726] z-30 menu-reveal">
                {DATE_RANGE_OPTIONS.map((opt) => (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => handleRangeSelect(opt.value)}
                    className={`flex w-full items-center px-3.5 py-2 text-xs text-left transition-colors cursor-pointer ${selectedRange === opt.value
                      ? 'font-bold text-indigo-600 bg-indigo-50 dark:bg-indigo-950/40 dark:text-indigo-400'
                      : 'text-slate-700 hover:bg-slate-50 dark:text-slate-300 dark:hover:bg-slate-800/60'
                      }`}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Refresh Button */}
          <button
            type="button"
            onClick={() => fetchDashboardData(selectedRange, customStartDate, customEndDate)}
            disabled={isRefreshing}
            className="inline-flex h-9 items-center gap-1.5 rounded-xl bg-indigo-600 px-3.5 text-[14px] font-medium text-white shadow-xs hover:bg-indigo-700 disabled:opacity-75 transition-colors cursor-pointer"
          >
            <RotateCw className={`h-3.5 w-3.5 ${isRefreshing ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Custom Range Date Pickers (Shown only when 'Custom Range' selected) */}
      {showCustomInputs && (
        <div className="flex flex-wrap items-center gap-3 rounded-xl border border-indigo-200/80 bg-indigo-50/50 p-3 text-xs dark:border-indigo-900/60 dark:bg-indigo-950/20">
          <span className="font-semibold text-slate-700 dark:text-slate-300">Custom Range:</span>
          <input
            type="date"
            value={customStartDate}
            onChange={(e) => setCustomStartDate(e.target.value)}
            className="rounded-lg border border-slate-200 bg-white px-2 py-1 text-slate-800 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200"
          />
          <span className="text-slate-400">to</span>
          <input
            type="date"
            value={customEndDate}
            onChange={(e) => setCustomEndDate(e.target.value)}
            className="rounded-lg border border-slate-200 bg-white px-2 py-1 text-slate-800 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200"
          />
          <button
            type="button"
            onClick={applyCustomRange}
            disabled={!customStartDate || !customEndDate}
            className="rounded-lg bg-indigo-600 px-3 py-1 font-semibold text-white hover:bg-indigo-700 disabled:opacity-50 cursor-pointer"
          >
            Apply
          </button>
        </div>
      )}

      {/* -------------------------------------------------- */}
      {/* REAL-TIME DISCOVERY SYNCING BANNER                 */}
      {/* -------------------------------------------------- */}
      {isDiscovering && (
        <div className="relative overflow-hidden rounded-2xl border border-indigo-200 dark:border-indigo-800/60 bg-gradient-to-r from-indigo-50/90 via-purple-50/60 to-blue-50/90 dark:from-indigo-950/40 dark:via-purple-950/30 dark:to-blue-950/40 p-4 sm:p-5 shadow-sm transition-all duration-300">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="flex items-center gap-3.5">
              <div className="relative flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-gradient-to-tr from-indigo-600 to-violet-600 text-white shadow-md shadow-indigo-500/25">
                <Loader2 className="h-5 w-5 animate-spin" />
                <span className="absolute -top-1 -right-1 flex h-3 w-3">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-500"></span>
                </span>
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-[11px] font-bold uppercase tracking-wider text-indigo-700 dark:text-indigo-400">
                    Live Scraper Pipeline Active
                  </span>
                  <span className="h-1 w-1 rounded-full bg-slate-300 dark:bg-slate-600" />
                  <span className="text-[11px] font-medium text-slate-500 dark:text-slate-400">
                    Auto-refreshing feed upon completion
                  </span>
                </div>
                <h3 className="text-sm sm:text-base font-semibold text-slate-900 dark:text-white mt-0.5">
                  {discoveryStatusText || 'Crawling job boards & syncing to database...'}
                </h3>
                <p className="text-xs text-slate-600 dark:text-slate-400 mt-0.5">
                  Querying configured portals, computing relevance score, and upserting into PostgreSQL.
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2 shrink-0 self-start sm:self-center">
              <Link
                to="/discovery"
                className="inline-flex items-center gap-1.5 rounded-xl bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 px-3.5 py-2 text-xs font-semibold text-slate-800 dark:text-slate-200 shadow-xs hover:bg-slate-50 dark:hover:bg-slate-700/80 transition-colors"
              >
                <span>Live Terminal</span>
                <ChevronRight className="h-3.5 w-3.5 text-slate-400" />
              </Link>
            </div>
          </div>
        </div>
      )}

      {/* -------------------------------------------------- */}
      {/* SECTION 1 — FOUR KPI CARDS                         */}
      {/* -------------------------------------------------- */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">

        {/* Card 1: Active Jobs */}
        <div
          onClick={() => navigate('/jobs')}
          className="group flex cursor-pointer items-center justify-between rounded-2xl border border-slate-200/80 bg-white p-5 sm:p-6
               shadow-[0_1px_3px_rgba(0,0,0,0.03),0_1px_2px_rgba(0,0,0,0.02)]
               transition-[transform,box-shadow,border-color] duration-180 ease-out
               hover:-translate-y-0.5 hover:border-slate-300
               hover:shadow-[0_8px_24px_rgba(0,0,0,0.06)]
               dark:border-slate-800 dark:bg-[#111726] dark:hover:border-slate-700 dark:hover:shadow-[0_8px_24px_rgba(0,0,0,0.25)]"
        >
          <div className="flex items-center gap-4">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-indigo-50 text-indigo-600 ring-1 ring-inset ring-indigo-600/15 shadow-xs dark:bg-indigo-950/60 dark:text-indigo-400 dark:ring-indigo-400/20">
              <Briefcase className="h-5 w-5" />
            </div>

            <div className="min-w-0">
              <span className="text-[15.5px] font-semibold text-slate-700 dark:text-slate-300">
                Active Jobs
              </span>

              <p className="mt-1 text-[38px] sm:text-[40px] font-bold leading-none tracking-tight text-slate-900 dark:text-white">
                {isLoading ? '...' : activeJobsCount}
              </p>

              <p className="mt-2 truncate text-[12.5px] font-medium text-slate-500 dark:text-slate-400">
                {blrCount} Bangalore · {remoteCount} Remote
              </p>
            </div>
          </div>

          <ChevronRight
            className="h-4.5 w-4.5 shrink-0 text-slate-400 transition-all duration-200
                 group-hover:translate-x-1 group-hover:text-indigo-600
                 dark:group-hover:text-indigo-400"
          />
        </div>


        {/* Card 2: New Jobs */}
        <div
          onClick={() => navigate('/jobs?tier=Tier+1')}
          className="group flex cursor-pointer items-center justify-between rounded-2xl border border-slate-200/80 bg-white p-5 sm:p-6
               shadow-[0_1px_3px_rgba(0,0,0,0.03),0_1px_2px_rgba(0,0,0,0.02)]
               transition-[transform,box-shadow,border-color] duration-180 ease-out
               hover:-translate-y-0.5 hover:border-slate-300
               hover:shadow-[0_8px_24px_rgba(0,0,0,0.06)]
               dark:border-slate-800 dark:bg-[#111726] dark:hover:border-slate-700 dark:hover:shadow-[0_8px_24px_rgba(0,0,0,0.25)]"
        >
          <div className="flex items-center gap-4">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-emerald-50 text-emerald-600 ring-1 ring-inset ring-emerald-600/15 shadow-xs dark:bg-emerald-950/60 dark:text-emerald-400 dark:ring-emerald-400/20">
              <Plus className="h-5 w-5 stroke-[2.5]" />
            </div>

            <div className="min-w-0">
              <span className="text-[15.5px] font-semibold text-slate-700 dark:text-slate-300">
                New Jobs
              </span>

              <p className="mt-1 text-[38px] sm:text-[40px] font-bold leading-none tracking-tight text-slate-900 dark:text-white">
                {isLoading ? '...' : newJobsCount}
              </p>

              <p className="mt-2 truncate text-[12.5px] font-medium text-slate-500 dark:text-slate-400">
                {highMatchCount} High Match
              </p>
            </div>
          </div>

          <ChevronRight
            className="h-4.5 w-4.5 shrink-0 text-slate-400 transition-all duration-200
                 group-hover:translate-x-1 group-hover:text-emerald-600
                 dark:group-hover:text-emerald-400"
          />
        </div>


        {/* Card 3: Applications */}
        <div
          onClick={() => navigate('/applications')}
          className="group flex cursor-pointer items-center justify-between rounded-2xl border border-slate-200/80 bg-white p-5 sm:p-6
               shadow-[0_1px_3px_rgba(0,0,0,0.03),0_1px_2px_rgba(0,0,0,0.02)]
               transition-[transform,box-shadow,border-color] duration-180 ease-out
               hover:-translate-y-0.5 hover:border-slate-300
               hover:shadow-[0_8px_24px_rgba(0,0,0,0.06)]
               dark:border-slate-800 dark:bg-[#111726] dark:hover:border-slate-700 dark:hover:shadow-[0_8px_24px_rgba(0,0,0,0.25)]"
        >
          <div className="flex items-center gap-4">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-violet-50 text-violet-600 ring-1 ring-inset ring-violet-600/15 shadow-xs dark:bg-violet-950/60 dark:text-violet-400 dark:ring-violet-400/20">
              <Send className="h-5 w-5" />
            </div>

            <div className="min-w-0">
              <span className="text-[15.5px] font-semibold text-slate-700 dark:text-slate-300">
                Applications
              </span>

              <p className="mt-1 text-[38px] sm:text-[40px] font-bold leading-none tracking-tight text-slate-900 dark:text-white">
                {isLoading ? '...' : appliedTotal}
              </p>

              <p className="mt-2 truncate text-[12.5px] font-medium text-slate-500 dark:text-slate-400">
                {underReviewCount} Under Review · {awaitingCount} Awaiting
              </p>
            </div>
          </div>

          <ChevronRight
            className="h-4.5 w-4.5 shrink-0 text-slate-400 transition-all duration-200
                 group-hover:translate-x-1 group-hover:text-violet-600
                 dark:group-hover:text-violet-400"
          />
        </div>


        {/* Card 4: Interviews */}
        <div
          onClick={() => navigate('/applications?status=interviewing')}
          className="group flex cursor-pointer items-center justify-between rounded-2xl border border-slate-200/80 bg-white p-5 sm:p-6
               shadow-[0_1px_3px_rgba(0,0,0,0.03),0_1px_2px_rgba(0,0,0,0.02)]
               transition-[transform,box-shadow,border-color] duration-180 ease-out
               hover:-translate-y-0.5 hover:border-slate-300
               hover:shadow-[0_8px_24px_rgba(0,0,0,0.06)]
               dark:border-slate-800 dark:bg-[#111726] dark:hover:border-slate-700 dark:hover:shadow-[0_8px_24px_rgba(0,0,0,0.25)]"
        >

          <div className="flex items-center gap-4">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-amber-50 text-amber-600 ring-1 ring-inset ring-amber-600/15 shadow-xs dark:bg-amber-950/60 dark:text-amber-400 dark:ring-amber-400/20">
              <Calendar className="h-5 w-5" />
            </div>

            <div className="min-w-0">
              <span className="text-[15.5px] font-semibold text-slate-700 dark:text-slate-300">
                Interviews
              </span>

              <p className="mt-1 text-[38px] sm:text-[40px] font-bold leading-none tracking-tight text-slate-900 dark:text-white">
                {isLoading ? '...' : interviewsTotal}
              </p>

              <p className="mt-2 truncate text-[12.5px] font-medium text-slate-500 dark:text-slate-400">
                {upcomingInterviews} Upcoming · {completedInterviews} Completed
              </p>
            </div>
          </div>

          <ChevronRight
            className="h-4.5 w-4.5 shrink-0 text-slate-400 transition-all duration-200
                 group-hover:translate-x-1 group-hover:text-amber-600
                 dark:group-hover:text-amber-400"
          />
        </div>

      </div>
      {/* -------------------------------------------------- */}
      {/* SECTIONS 2 & 3 — DISCOVERY TREND & PIPELINE        */}
      {/* -------------------------------------------------- */}
      <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
        {/* Section 2: Jobs Discovered Line Chart */}
        <JobsDiscoveredChart data={summary?.discovery_trend} />

        {/* Section 3: Application Pipeline Vertical Bar Chart */}
        <ApplicationStatusChart breakdown={summary?.application_breakdown} />
      </div>

      {/* -------------------------------------------------- */}
      {/* SECTIONS 4 & 5 — JOBS BY SOURCE & JOBS BY LOCATION */}
      {/* -------------------------------------------------- */}
      <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
        {/* Section 4: Jobs by Source Donut Chart */}
        <JobsBySourceChart sources={summary?.sources_breakdown} />

        {/* Section 5: Jobs by Location Vertical Bar Chart */}
        <JobLocationsChart
          locations={summary?.location_breakdown}
          locationsBreakdown={summary?.locations_breakdown}
        />
      </div>

      {/* -------------------------------------------------- */}
      {/* SECTIONS 6 & 7 — RECOMMENDED JOBS & RECENT ACTIVITY */}
      {/* -------------------------------------------------- */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12 pt-2">
        {/* Section 6: Recommended Jobs for You (7 Columns) */}
        <div className="lg:col-span-7 flex flex-col overflow-hidden rounded-2xl border border-slate-200/80 bg-white shadow-sm dark:border-slate-800 dark:bg-[#111726]">
          {/* Header */}
          <div className="flex items-center justify-between border-b border-slate-100 px-6 py-5 dark:border-slate-800">
            <h3 className="text-[18px] font-bold tracking-tight text-slate-900 dark:text-white">
              Recommended Jobs for You
            </h3>
            <Link
              to="/jobs"
              className="group inline-flex items-center gap-1 text-[13.5px] font-semibold text-indigo-600 hover:text-indigo-700 dark:text-indigo-400 dark:hover:text-indigo-300 transition-colors"
            >
              <span>View All</span>
              <ChevronRight className="h-3.5 w-3.5 transition-transform group-hover:translate-x-0.5" />
            </Link>
          </div>

          {/* Jobs List Body */}
          <div className="flex-1 divide-y divide-slate-100 dark:divide-slate-800/80 p-4 sm:p-5">
            {isLoading ? (
              <div className="flex min-h-[240px] flex-col items-center justify-center gap-2 text-slate-400">
                <Loader2 className="h-5 w-5 animate-spin text-indigo-500" />
                <span className="text-[13.5px]">Loading recommended opportunities...</span>
              </div>
            ) : recommendedJobs.length === 0 ? (
              <div className="flex min-h-[240px] items-center justify-center text-center text-slate-400">
                <p className="text-[13.5px]">No recommended jobs found at this time.</p>
              </div>
            ) : (
              recommendedJobs.slice(0, 3).map((job) => {
                const avatar = getCompanyAvatarStyle(job.company_name);
                const isSaved = savedJobIds.has(job.id);
                const matchPct = Math.round(job.relevance_score);

                // Top skills highlights (filter out metadata bonuses)
                const displaySkills = (job.matched_skills || [])
                  .filter((s) => !s.includes('Synergy') && !s.includes('Penalty') && !s.includes('Role') && !s.includes('Exp'))
                  .slice(0, 3);

                return (
                  <div
                    key={job.id}
                    onClick={() => setSelectedJobId(job.id)}
                    className="group flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-5 rounded-xl hover:bg-slate-50/80 dark:hover:bg-slate-800/40 transition-colors cursor-pointer"
                  >
                    {/* Left: Avatar + Details */}
                    <div className="flex items-start gap-3.5 min-w-0">
                      <div
                        className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl text-[13px] font-black shadow-xs ${avatar.bg}`}
                      >
                        {avatar.initials}
                      </div>

                      <div className="min-w-0x">
                        {/* Title & Match Badge */}
                        <div className="flex items-center gap-2 flex-wrap">
                          <h4 className="text-[14px] font-bold text-slate-900 group-hover:text-indigo-600 dark:text-white dark:group-hover:text-indigo-400 transition-colors truncate">
                            {job.title}
                          </h4>
                          <span className="inline-flex items-center rounded-full bg-emerald-50 px-2.5 py-0.5 text-[12px] font-semibold text-emerald-700 border border-emerald-200/70 shadow-xs dark:bg-emerald-950/60 dark:text-emerald-300 dark:border-emerald-800/60">
                            {matchPct}% Match
                          </span>
                        </div>

                        {/* Company · Location · Experience */}
                        <p className="mt-1.5 text-[13.5px] font-medium text-slate-800 dark:text-slate-200 truncate">
                          {job.company_name} · {job.is_remote ? 'Remote' : (job.location || job.location_bucket || 'Location not specified')} ·{' '}
                          {job.experience_raw || (job.experience_min !== null ? `${job.experience_min}–${job.experience_max ?? '+'} yrs` : 'Experience not specified')}
                        </p>

                        {/* Skill Pills with Dot */}
                        {displaySkills.length > 0 && (
                          <div className="mt-2.5 flex items-center gap-2 flex-wrap">
                            {displaySkills.map((skill) => (
                              <span
                                key={skill}
                                className="inline-flex items-center gap-1.5 rounded-md bg-slate-50/90 border border-slate-200/70 px-2.5 py-1 text-[12px] font-semibold text-slate-800 shadow-sm dark:bg-slate-800/80 dark:border-slate-700/70 dark:text-slate-200"
                              >
                                <span className="h-2 w-2 rounded-full bg-emerald-500 shrink-0" />
                                <span>{skill}</span>
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Right: Actions */}
                    <div className="flex items-center gap-2 self-end sm:self-center shrink-0">
                      <button
                        type="button"
                        onClick={(e) => toggleBookmark(e, job.id)}
                        title={isSaved ? 'Remove bookmark' : 'Bookmark job'}
                        className={`inline-flex h-9 w-9 items-center justify-center rounded-lg border active:scale-95 transition-all cursor-pointer ${isSaved
                          ? 'border-amber-500 bg-amber-100 text-amber-700 dark:border-amber-800 dark:bg-amber-950/50 dark:text-amber-300'
                          : 'border-slate-200 bg-white text-slate-400 hover:border-slate-300 hover:text-slate-600 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-500 dark:hover:text-slate-300'
                          }`}
                      >
                        <Bookmark className={`h-5 w-5 ${isSaved ? 'fill-current' : ''}`} />
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
                        className="inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 px-4 py-2 text-[13.5px] font-semibold text-white hover:bg-indigo-700 active:scale-95 shadow-xs transition-all cursor-pointer"
                      >
                        <span>Apply</span>
                      </button>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Section 7: Recent Activity (5 Columns) */}
        <div className="lg:col-span-5">
          <RecentActivity activities={summary?.recent_activities} />
        </div>
      </div>

      {/* Slide-out Job Details Drawer */}
      <JobDetailDrawer
        jobId={selectedJobId}
        onClose={() => setSelectedJobId(null)}
        onJobUpdated={() => fetchDashboardData(selectedRange, customStartDate, customEndDate)}
      />
    </div>
  );
};

export default DashboardPage;
