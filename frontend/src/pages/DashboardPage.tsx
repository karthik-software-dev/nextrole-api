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
  MapPin,
  Banknote,
  Globe,
  Building2,
  Plane,
  Home,
  Check,
  X,
  Clock,
} from 'lucide-react';
import { getDashboardSummary, getJobs, createApplication, deleteApplicationByJobId } from '../api';
import { DATE_RANGE_OPTIONS, type DashboardSummary, type JobSummary, type DateRangePreset } from '../types';
import { useDiscovery } from '../context/DiscoveryContext';
import { useToast } from '../context/ToastContext';
import { DailyCadenceChart } from '../components/dashboard/DailyCadenceChart';
import { JobsDiscoveredChart } from '../components/dashboard/JobsDiscoveredChart';
import { ApplicationStatusChart } from '../components/dashboard/ApplicationStatusChart';
import { JobsBySourceChart } from '../components/dashboard/JobsBySourceChart';
import { JobLocationsChart } from '../components/dashboard/JobLocationsChart';
import { ExperienceDistributionChart } from '../components/dashboard/ExperienceDistributionChart';
import { SalaryDistributionChart } from '../components/dashboard/SalaryDistributionChart';
import { DiscoverySpeedCard } from '../components/dashboard/DiscoverySpeedCard';
import { RecentActivity } from '../components/dashboard/RecentActivity';
import { JobDetailDrawer } from './JobDetailDrawer';
import { TierBadge, MatchScoreBadge, ApplicationStatusBadge, RecommendedResumeBadge } from '../components/ui/Badge';
import { CompanyAvatar } from '../components/ui/CompanyAvatar';
import { playJobApplySound } from '../utils/audio';
import { formatRelativeTime } from '../utils/date';

// Sanitization guard to prevent non-salary description text blobs from rendering
const isValidSalary = (salary?: string | null): boolean => {
  if (!salary) return false;
  const s = salary.trim();
  if (s.length > 45) return false;
  if (/about|description|summary|equity|role|looking for|industry/i.test(s)) return false;
  return /\d/.test(s);
};


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

  // Close dropdown or custom date card on outside click
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dateMenuRef.current && !dateMenuRef.current.contains(e.target as Node)) {
        setIsDateMenuOpen(false);
        setShowCustomInputs(false);
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
      const recJobs = jobsData.items || [];
      setRecommendedJobs(recJobs);
      setSavedJobIds((prev) => {
        const next = new Set(prev);
        recJobs.forEach((j: JobSummary) => {
          if (j.application_status === 'drafted' || j.application_status === 'saved') {
            next.add(j.id);
          }
        });
        return next;
      });
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

  const toggleBookmark = async (e: React.MouseEvent, target: JobSummary | number) => {
    e.stopPropagation();
    const jobId = typeof target === 'number' ? target : target.id;
    const jobObj = typeof target === 'number' ? recommendedJobs.find((j) => j.id === jobId) : target;
    const jobTitle = jobObj?.title || `Job #${jobId}`;
    const isCurrentlySaved = savedJobIds.has(jobId) || jobObj?.application_status === 'drafted' || jobObj?.application_status === 'saved';

    if (isCurrentlySaved) {
      setSavedJobIds((prev) => {
        const next = new Set(prev);
        next.delete(jobId);
        try {
          localStorage.setItem('careerpilot_saved_jobs', JSON.stringify(Array.from(next)));
        } catch {}
        return next;
      });
      setRecommendedJobs((prev) =>
        prev.map((j) => (j.id === jobId && (j.application_status === 'drafted' || j.application_status === 'saved')
          ? { ...j, application_status: undefined }
          : j))
      );

      try {
        await deleteApplicationByJobId(jobId);
        toast.info(`"${jobTitle}" removed from Saved / Draft`, 2200);
      } catch (err: any) {
        console.error('Failed to un-save application:', err);
        setSavedJobIds((prev) => {
          const next = new Set(prev);
          next.add(jobId);
          try {
            localStorage.setItem('careerpilot_saved_jobs', JSON.stringify(Array.from(next)));
          } catch {}
          return next;
        });
        setRecommendedJobs((prev) =>
          prev.map((j) => (j.id === jobId ? { ...j, application_status: 'drafted' } : j))
        );
        toast.error('Failed to remove job from saved list', 2200);
      }
    } else {
      setSavedJobIds((prev) => {
        const next = new Set(prev);
        next.add(jobId);
        try {
          localStorage.setItem('careerpilot_saved_jobs', JSON.stringify(Array.from(next)));
        } catch {}
        return next;
      });
      setRecommendedJobs((prev) =>
        prev.map((j) => (j.id === jobId && !j.application_status ? { ...j, application_status: 'drafted' } : j))
      );

      try {
        await createApplication({
          job_id: jobId,
          initial_status: 'drafted',
          portal_type: jobObj?.ats_provider || 'Company Career Portal',
        });
        toast.success(`"${jobTitle}" saved to Applications CRM (Saved / Draft)`, 2500);
      } catch (err: any) {
        console.error('Failed to save application to CRM:', err);
        setSavedJobIds((prev) => {
          const next = new Set(prev);
          next.delete(jobId);
          try {
            localStorage.setItem('careerpilot_saved_jobs', JSON.stringify(Array.from(next)));
          } catch {}
          return next;
        });
        setRecommendedJobs((prev) =>
          prev.map((j) => (j.id === jobId && j.application_status === 'drafted' ? { ...j, application_status: undefined } : j))
        );
        toast.error(err.message || 'Failed to save opportunity to CRM', 2200);
      }
    }
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
    if (selectedRange === 'custom' && customStartDate && customEndDate) {
      return `${customStartDate} → ${customEndDate}`;
    }
    const found = DATE_RANGE_OPTIONS.find((opt) => opt.value === selectedRange);
    return found ? found.label : 'Last 7 Days';
  }, [selectedRange, customStartDate, customEndDate]);

  // Real KPI Metrics derived strictly from real DB records
  const activeJobsCount = summary?.active_jobs ?? 0;
  const newJobsCount = summary?.new_jobs ?? 0;
  const highMatchCount = summary?.new_tier1_jobs ?? 0;

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
    <div className="space-y-6 pb-16 sm:pb-20">
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
          {/* Date Range Dropdown & Custom Range Card Popover */}
          <div className="relative" ref={dateMenuRef}>
            <button
              type="button"
              onClick={() => {
                if (showCustomInputs) {
                  setShowCustomInputs(false);
                } else {
                  setIsDateMenuOpen(!isDateMenuOpen);
                }
              }}
              className="inline-flex h-9 items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 text-xs font-semibold text-slate-700 shadow-xs hover:bg-slate-50 dark:border-slate-800 dark:bg-[#111726] dark:text-slate-200 dark:hover:bg-slate-800/60 transition-colors cursor-pointer"
            >
              <Calendar className="h-3.5 w-3.5 text-slate-500" />
              <span>{selectedRangeLabel}</span>
              <ChevronDown className="h-3.5 w-3.5 text-slate-400" />
            </button>

            {/* Standard Preset Menu */}
            {isDateMenuOpen && (
              <div className="absolute right-0 mt-1.5 w-44 rounded-xl border border-slate-200 bg-white py-1 shadow-lg dark:border-slate-800 dark:bg-[#111726] z-30 menu-reveal">
                {DATE_RANGE_OPTIONS.map((opt) => (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => handleRangeSelect(opt.value)}
                    className={`flex w-full items-center px-3.5 py-2 text-xs text-left transition-colors cursor-pointer ${
                      selectedRange === opt.value
                        ? 'font-bold text-indigo-600 bg-indigo-50 dark:bg-indigo-950/40 dark:text-indigo-400'
                        : 'text-slate-700 hover:bg-slate-50 dark:text-slate-300 dark:hover:bg-slate-800/60'
                    }`}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            )}

            {/* Custom Range Floating Popover Card (Standard SaaS Design) */}
            {showCustomInputs && (
              <div className="absolute right-0 mt-2 w-72 sm:w-80 rounded-2xl border border-slate-200/90 dark:border-slate-800 bg-white dark:bg-[#111726] p-4 shadow-2xl shadow-slate-900/15 dark:shadow-slate-950/60 z-40 animate-in zoom-in-95 duration-150">
                <div className="flex items-center justify-between pb-3 border-b border-slate-100 dark:border-slate-800/80">
                  <div className="flex items-center gap-2">
                    <Calendar className="h-4 w-4 text-indigo-600 dark:text-indigo-400" />
                    <span className="text-[13px] font-bold text-slate-900 dark:text-white">
                      Custom Date Range
                    </span>
                  </div>
                  <button
                    type="button"
                    onClick={() => setShowCustomInputs(false)}
                    className="p-1 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors cursor-pointer"
                  >
                    <X className="h-3.5 w-3.5" />
                  </button>
                </div>

                <div className="mt-3.5 space-y-3">
                  <div>
                    <label className="block text-[11px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1">
                      Start Date
                    </label>
                    <input
                      type="date"
                      value={customStartDate}
                      onChange={(e) => setCustomStartDate(e.target.value)}
                      className="w-full rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/60 px-3 py-2 text-xs font-medium text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-colors"
                    />
                  </div>

                  <div>
                    <label className="block text-[11px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1">
                      End Date
                    </label>
                    <input
                      type="date"
                      value={customEndDate}
                      onChange={(e) => setCustomEndDate(e.target.value)}
                      className="w-full rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/60 px-3 py-2 text-xs font-medium text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-colors"
                    />
                  </div>

                  <div className="pt-2 flex items-center justify-end gap-2">
                    <button
                      type="button"
                      onClick={() => setShowCustomInputs(false)}
                      className="px-3 py-1.5 rounded-xl text-xs font-semibold text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors cursor-pointer"
                    >
                      Cancel
                    </button>
                    <button
                      type="button"
                      onClick={applyCustomRange}
                      disabled={!customStartDate || !customEndDate}
                      className="px-3.5 py-1.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-xs font-bold text-white shadow-xs transition-colors cursor-pointer"
                    >
                      Apply Range
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Refresh Button */}
          <button
            type="button"
            onClick={() => fetchDashboardData(selectedRange, customStartDate, customEndDate)}
            disabled={isRefreshing}
            className="inline-flex h-9 items-center gap-1.5 rounded-xl bg-indigo-600 px-3.5 text-xs font-semibold text-white shadow-xs hover:bg-indigo-700 disabled:opacity-75 transition-colors cursor-pointer"
          >
            <RotateCw className={`h-3.5 w-3.5 ${isRefreshing ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>


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
          <div className="flex items-center gap-3.5 sm:gap-4 min-w-0 flex-1">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-indigo-50 text-indigo-600 ring-1 ring-inset ring-indigo-600/15 shadow-xs dark:bg-indigo-950/60 dark:text-indigo-400 dark:ring-indigo-400/20">
              <Briefcase className="h-5 w-5" />
            </div>

            <div className="min-w-0 flex-1">
              <span className="text-[13.5px] font-semibold text-slate-600 dark:text-slate-400">
                Active Jobs
              </span>

              <p className="mt-1 text-[36px] sm:text-[38px] font-bold leading-none tracking-tight text-slate-900 dark:text-white">
                {isLoading ? '...' : activeJobsCount}
              </p>

              <p className="mt-2 truncate text-xs font-medium text-slate-500 dark:text-slate-400">
                {blrCount} Bangalore · {remoteCount} Remote
              </p>
            </div>
          </div>

          <ChevronRight
            className="h-4.5 w-4.5 shrink-0 text-slate-400 transition-all duration-200
                 group-hover:translate-x-1 group-hover:text-indigo-600
                 dark:group-hover:text-indigo-400 ml-2"
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
          <div className="flex items-center gap-3.5 sm:gap-4 min-w-0 flex-1">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-emerald-50 text-emerald-600 ring-1 ring-inset ring-emerald-600/15 shadow-xs dark:bg-emerald-950/60 dark:text-emerald-400 dark:ring-emerald-400/20">
              <Plus className="h-5 w-5 stroke-[2.5]" />
            </div>

            <div className="min-w-0 flex-1">
              <span className="text-[13.5px] font-semibold text-slate-600 dark:text-slate-400">
                New Jobs
              </span>

              <p className="mt-1 text-[36px] sm:text-[38px] font-bold leading-none tracking-tight text-slate-900 dark:text-white">
                {isLoading ? '...' : newJobsCount}
              </p>

              <p className="mt-2 truncate text-xs font-medium text-slate-500 dark:text-slate-400">
                {selectedRangeLabel} · {highMatchCount} High Match
              </p>
            </div>
          </div>

          <ChevronRight
            className="h-4.5 w-4.5 shrink-0 text-slate-400 transition-all duration-200
                 group-hover:translate-x-1 group-hover:text-emerald-600
                 dark:group-hover:text-emerald-400 ml-2"
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
          <div className="flex items-center gap-3.5 sm:gap-4 min-w-0 flex-1">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-violet-50 text-violet-600 ring-1 ring-inset ring-violet-600/15 shadow-xs dark:bg-violet-950/60 dark:text-violet-400 dark:ring-violet-400/20">
              <Send className="h-5 w-5" />
            </div>

            <div className="min-w-0 flex-1">
              <span className="text-[13.5px] font-semibold text-slate-600 dark:text-slate-400">
                Applications
              </span>

              <p className="mt-1 text-[36px] sm:text-[38px] font-bold leading-none tracking-tight text-slate-900 dark:text-white">
                {isLoading ? '...' : appliedTotal}
              </p>

              <p className="mt-2 truncate text-xs font-medium text-slate-500 dark:text-slate-400">
                {appliedTotal > 0 ? `${underReviewCount} Under Review · ${awaitingCount} Awaiting` : 'No active applications'}
              </p>
            </div>
          </div>

          <ChevronRight
            className="h-4.5 w-4.5 shrink-0 text-slate-400 transition-all duration-200
                 group-hover:translate-x-1 group-hover:text-violet-600
                 dark:group-hover:text-violet-400 ml-2"
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

          <div className="flex items-center gap-3.5 sm:gap-4 min-w-0 flex-1">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-amber-50 text-amber-600 ring-1 ring-inset ring-amber-600/15 shadow-xs dark:bg-amber-950/60 dark:text-amber-400 dark:ring-amber-400/20">
              <Calendar className="h-5 w-5" />
            </div>

            <div className="min-w-0 flex-1">
              <span className="text-[13.5px] font-semibold text-slate-600 dark:text-slate-400">
                Interviews
              </span>

              <p className="mt-1 text-[36px] sm:text-[38px] font-bold leading-none tracking-tight text-slate-900 dark:text-white">
                {isLoading ? '...' : interviewsTotal}
              </p>

              <p className="mt-2 truncate text-xs font-medium text-slate-500 dark:text-slate-400">
                {interviewsTotal > 0 ? `${upcomingInterviews} Upcoming · ${completedInterviews} Completed` : 'No scheduled interviews'}
              </p>
            </div>
          </div>

          <ChevronRight
            className="h-4.5 w-4.5 shrink-0 text-slate-400 transition-all duration-200
                 group-hover:translate-x-1 group-hover:text-amber-600
                 dark:group-hover:text-amber-400 ml-2"
          />
        </div>

      </div>
      {/* -------------------------------------------------- */}
      {/* SECTIONS 2 & 3 — DAILY CADENCE & DISCOVERY TREND   */}
      {/* -------------------------------------------------- */}
      <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
        {/* Feature A: 5-Run Daily Cadence Chart */}
        <DailyCadenceChart data={summary?.daily_cadence} pipeline={summary?.latest_pipeline} />

        {/* Section 2: Jobs Discovered Line Chart */}
        <JobsDiscoveredChart data={summary?.discovery_trend} />
      </div>

      {/* -------------------------------------------------- */}
      {/* SECTIONS 4 & 5 — APPLICATION FUNNEL & SOURCE BREAKDOWN */}
      {/* -------------------------------------------------- */}
      <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
        {/* Section 3: Application Pipeline Vertical Bar Chart */}
        <ApplicationStatusChart breakdown={summary?.application_breakdown} />

        {/* Section 4: Jobs by Source Donut Chart */}
        <JobsBySourceChart sources={summary?.sources_breakdown} />
      </div>

      {/* -------------------------------------------------- */}
      {/* LOCATION & EXPERIENCE DISTRIBUTION                */}
      {/* -------------------------------------------------- */}
      <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
        {/* Section 5: Jobs by Location Vertical Bar Chart */}
        <JobLocationsChart
          locations={summary?.location_breakdown}
          locationsBreakdown={summary?.locations_breakdown}
        />

        {/* Experience Level Distribution */}
        <ExperienceDistributionChart data={summary?.experience_distribution} />
      </div>

      {/* -------------------------------------------------- */}
      {/* SALARY RANGE & DISCOVERY SPEED ADVANTAGE           */}
      {/* -------------------------------------------------- */}
      <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
        {/* Salary Range Distribution (₹ LPA) */}
        <SalaryDistributionChart data={summary?.salary_distribution} />

        {/* Discovery Speed Advantage */}
        <DiscoverySpeedCard data={summary?.discovery_speed} />
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
          <div className="flex-1 p-3.5 sm:p-4 pb-4 sm:pb-5 space-y-2.5 sm:space-y-3">
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
                const isSaved = savedJobIds.has(job.id) || job.application_status === 'drafted' || job.application_status === 'saved';
                const isWfh = Boolean(
                  job.is_remote ||
                  job.location_bucket === 'REMOTE_INDIA' ||
                  job.location?.toLowerCase().includes('remote') ||
                  job.location?.toLowerCase().includes('wfh')
                );
                const isHybrid = !isWfh && Boolean(
                  job.location?.toLowerCase().includes('hybrid') ||
                  job.title?.toLowerCase().includes('hybrid')
                );
                const isAbroad = job.location_bucket === 'ABROAD';

                const displayLocation =
                  job.location ||
                  (isAbroad
                    ? 'Abroad / Relocation'
                    : isWfh
                      ? 'Remote'
                      : 'Bangalore');

                const displaySkills = (job.matched_skills || [])
                  .filter((s) => !s.includes('Synergy') && !s.includes('Penalty') && !s.includes('Role') && !s.includes('Exp'));

                return (
                  <div
                    key={job.id}
                    onClick={() => setSelectedJobId(job.id)}
                    className="p-3 sm:p-3.5 rounded-xl border border-slate-200/80 dark:border-slate-800/80 bg-slate-50/40 dark:bg-slate-900/30 hover:border-slate-300 dark:hover:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-all duration-150 ease-out cursor-pointer group shadow-2xs"
                  >
                    <div className="flex flex-col gap-1.5 sm:gap-2">
                      {/* Top Header: Avatar + Title & Company + Bookmark (Option A: Desktop Left Avatar, Mobile Top-Right Avatar + Bookmark) */}
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex items-start gap-2.5 sm:gap-3 min-w-0 flex-1">
                          <div className="hidden sm:block shrink-0 p-1 rounded-lg bg-slate-50 dark:bg-slate-800/80 border border-slate-200/60 dark:border-slate-700/60 shadow-2xs mt-0.5">
                            <CompanyAvatar name={job.company_name} size="sm" className="rounded-md" />
                          </div>

                          <div className="min-w-0 flex-1">
                            <div className="flex items-start justify-between gap-2">
                              <div className="min-w-0 flex-1">
                                <h4 className="text-[14px] sm:text-[14.5px] font-bold text-slate-900 dark:text-white leading-snug tracking-tight group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors line-clamp-2">
                                  {job.title}
                                </h4>
                                <p className="text-[12px] sm:text-[12.5px] font-semibold text-slate-700 dark:text-slate-300 mt-0.5 truncate">
                                  {job.company_name}
                                </p>
                              </div>
                            </div>

                            {/* Badges */}
                            <div className="flex items-center gap-1.5 flex-wrap pt-1">
                              <TierBadge tier={job.priority_tier} />
                              <MatchScoreBadge score={job.relevance_score} matchPercentage={job.match_percentage} />
                              <RecommendedResumeBadge job={job} size="xs" />
                              {job.application_status && (
                                <ApplicationStatusBadge status={job.application_status} size="xs" />
                              )}
                            </div>
                          </div>
                        </div>

                        {/* Desktop Actions: Bookmark + Apply Button */}
                        <div className="hidden sm:flex items-center gap-2 shrink-0 mt-0.5">
                          <button
                            type="button"
                            onClick={(e) => toggleBookmark(e, job)}
                            title={isSaved ? 'Job saved' : 'Save job'}
                            className={`p-2 rounded-lg border transition-colors cursor-pointer shrink-0 ${
                              isSaved
                                ? 'bg-amber-50 dark:bg-amber-950/40 text-amber-500 border-amber-200/80 dark:border-amber-800/80'
                                : 'border-slate-200/80 dark:border-slate-700/80 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800'
                            }`}
                          >
                            <Bookmark className={`h-4 w-4 ${isSaved ? 'fill-amber-500 text-amber-500' : ''}`} />
                          </button>

                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              playJobApplySound();
                              if (job.canonical_apply_url) {
                                window.open(job.canonical_apply_url, '_blank', 'noopener,noreferrer');
                              } else {
                                setSelectedJobId(job.id);
                              }
                            }}
                            className="inline-flex items-center justify-center gap-1.5 rounded-lg bg-indigo-600 px-3.5 py-1.5 text-[12.5px] sm:text-[13px] font-semibold text-white hover:bg-indigo-700 active:scale-95 shadow-xs transition-all cursor-pointer whitespace-nowrap"
                          >
                            <span>Apply</span>
                            <ExternalLink className="h-3.5 w-3.5" />
                          </button>
                        </div>
                      </div>

                      {/* Middle: Location · Work Mode · Experience · Disclosed Salary */}
                      <div className="flex items-center gap-2 text-xs text-slate-600 dark:text-slate-400 font-medium flex-wrap">
                        <span className="flex items-center gap-1">
                          {isAbroad ? (
                            <Plane className="h-3 w-3 text-indigo-500 shrink-0" />
                          ) : isWfh ? (
                            <Globe className="h-3 w-3 text-emerald-500 shrink-0" />
                          ) : (
                            <MapPin className="h-3 w-3 text-slate-400 shrink-0" />
                          )}
                          <span>{displayLocation}</span>
                        </span>

                        <span className="text-slate-300 dark:text-slate-700">·</span>

                        {/* Work Mode Capsule */}
                        {isWfh ? (
                          <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md text-[11px] font-medium bg-emerald-50/80 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-400 border border-emerald-200/60 dark:border-emerald-800/50">
                            <Home className="h-3 w-3 text-emerald-500 shrink-0" />
                            <span>Remote</span>
                          </span>
                        ) : isHybrid ? (
                          <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md text-[11px] font-medium bg-indigo-50/80 dark:bg-indigo-950/40 text-indigo-700 dark:text-indigo-400 border border-indigo-200/60 dark:border-indigo-800/50">
                            <Building2 className="h-3 w-3 text-indigo-500 shrink-0" />
                            <span>Hybrid</span>
                          </span>
                        ) : isAbroad ? (
                          <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md text-[11px] font-medium bg-violet-50/80 dark:bg-violet-950/40 text-violet-700 dark:text-violet-400 border border-violet-200/60 dark:border-violet-800/50">
                            <Plane className="h-3 w-3 text-violet-500 shrink-0" />
                            <span>Relocation</span>
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md text-[11px] font-medium bg-slate-100/80 dark:bg-slate-800/80 text-slate-600 dark:text-slate-400 border border-slate-200/60 dark:border-slate-700/60">
                            <Building2 className="h-3 w-3 text-slate-400 shrink-0" />
                            <span>In-office</span>
                          </span>
                        )}

                        <span className="text-slate-300 dark:text-slate-700">·</span>
                        <span className="flex items-center gap-1">
                          <Briefcase className="h-3 w-3 text-slate-400 shrink-0" />
                          <span>{job.experience_raw || (job.experience_min !== null ? `${job.experience_min}–${job.experience_max || job.experience_min + 2} Yrs` : '0–2 Yrs')}</span>
                        </span>
                        {isValidSalary(job.salary_raw) && (
                          <>
                            <span className="text-slate-300 dark:text-slate-700">·</span>
                            <span className="inline-flex items-center gap-1 font-semibold text-emerald-600 dark:text-emerald-400 text-xs">
                              <Banknote className="h-3 w-3 text-emerald-500 shrink-0" />
                              <span>{job.salary_raw}</span>
                            </span>
                          </>
                        )}
                      </div>

                      {/* Skills capsules */}
                      {displaySkills.length > 0 && (
                        <div className="flex items-center gap-1.5 flex-nowrap overflow-hidden pt-0.5 max-w-full">
                          {displaySkills.slice(0, 4).map((skill, i) => (
                            <span
                              key={i}
                              className="shrink-0 px-2 py-0.5 rounded-md bg-slate-100 dark:bg-slate-800 text-[11px] text-slate-600 dark:text-slate-300 font-medium truncate max-w-[125px]"
                            >
                              {skill}
                            </span>
                          ))}
                          {displaySkills.length > 4 && (
                            <span className="shrink-0 px-1.5 py-0.5 rounded-md bg-slate-100/70 dark:bg-slate-800/60 text-[10.5px] text-slate-400 dark:text-slate-500 font-semibold">
                              +{displaySkills.length - 4}
                            </span>
                          )}
                        </div>
                      )}

                      {/* Mobile Dedicated Bottom Action Bar (<sm only) */}
                      <div className="sm:hidden pt-2.5 mt-0.5 border-t border-slate-100 dark:border-slate-800/80 flex items-center justify-between">
                        <span className="text-[11.5px] text-slate-400 dark:text-slate-500 font-medium flex items-center gap-1">
                          <Clock className="h-3 w-3 text-slate-400 shrink-0" />
                          <span>{formatRelativeTime(job.first_seen_at || job.last_seen_at)}</span>
                        </span>

                        <div className="flex items-center gap-2">
                          <button
                            type="button"
                            onClick={(e) => toggleBookmark(e, job)}
                            title={isSaved ? 'Job saved' : 'Save job'}
                            className={`p-2.5 rounded-xl border transition-colors cursor-pointer shrink-0 ${isSaved
                                ? 'bg-amber-50 dark:bg-amber-950/40 text-amber-500 border-amber-200/80 dark:border-amber-800/80'
                                : 'border-slate-200/80 dark:border-slate-700/80 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200'
                              }`}
                          >
                            <Bookmark className={`h-4.5 w-4.5 ${isSaved ? 'fill-amber-500 text-amber-500' : ''}`} />
                          </button>
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              playJobApplySound();
                              if (job.canonical_apply_url) {
                                window.open(job.canonical_apply_url, '_blank', 'noopener,noreferrer');
                              } else {
                                setSelectedJobId(job.id);
                              }
                            }}
                            className="inline-flex items-center justify-center gap-1.5 rounded-xl bg-indigo-600 px-4 py-2 text-[13px] font-bold text-white hover:bg-indigo-700 active:scale-95 shadow-xs transition-all cursor-pointer whitespace-nowrap min-w-[88px]"
                          >
                            <span>Apply</span>
                            <ExternalLink className="h-4 w-4" />
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Section 7: Recent Activity (5 Columns) */}
        <div className="lg:col-span-5 flex flex-col">
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

export default DashboardPage