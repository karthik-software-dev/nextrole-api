import React, { useEffect, useMemo, useState, useRef } from 'react';
import {
  Calendar,
  ChevronDown,
  RotateCw,
  Loader2,
  AlertCircle,
  TrendingUp,
  Bot,
} from 'lucide-react';
import { getAnalyticsSummary } from '../api';
import type { AnalyticsSummary } from '../types';
import { useToast } from '../context/ToastContext';
import { AnalyticsKpiCards } from '../components/analytics/AnalyticsKpiCards';
import { JobIntelligenceSection } from '../components/analytics/JobIntelligenceSection';
import { ApplicationAnalyticsSection } from '../components/analytics/ApplicationAnalyticsSection';
import { AgentPerformanceSection } from '../components/analytics/AgentPerformanceSection';

const DATE_RANGE_OPTIONS = [
  { label: 'Today', value: 'today' },
  { label: 'Yesterday', value: 'yesterday' },
  { label: 'Last 7 Days', value: '7d' },
  { label: 'Last 30 Days', value: '30d' },
  { label: 'This Month', value: 'month' },
  { label: 'Custom Range', value: 'custom' },
];

export const AnalyticsPage: React.FC = () => {
  const { toast } = useToast();

  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Date Range State
  const [selectedRange, setSelectedRange] = useState<string>('30d');
  const [isDateMenuOpen, setIsDateMenuOpen] = useState(false);
  const [customStartDate, setCustomStartDate] = useState<string>('');
  const [customEndDate, setCustomEndDate] = useState<string>('');
  const [showCustomInputs, setShowCustomInputs] = useState(false);
  const dateMenuRef = useRef<HTMLDivElement>(null);

  // Internal Navigation Tab ('insights' | 'agent')
  const [activeTab, setActiveTab] = useState<'insights' | 'agent'>('insights');

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

  const fetchAnalytics = async (
    rangeVal: string = selectedRange,
    startD?: string,
    endD?: string
  ) => {
    try {
      setError(null);
      const params: { range?: string; start_date?: string; end_date?: string } = {
        range: rangeVal,
      };
      if (rangeVal === 'custom' && startD && endD) {
        params.start_date = startD;
        params.end_date = endD;
      }

      const res = await getAnalyticsSummary(params);
      setSummary(res);
    } catch (err) {
      console.error('Failed to load analytics summary:', err);
      setError('Unable to load analytics metrics. Please retry.');
      toast.error('Failed to load analytics data');
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    fetchAnalytics(selectedRange, customStartDate, customEndDate);
  }, [selectedRange]);

  const handleRefresh = () => {
    setIsRefreshing(true);
    fetchAnalytics(selectedRange, customStartDate, customEndDate);
  };

  const handleRangeSelect = (val: string) => {
    if (val === 'custom') {
      setShowCustomInputs(true);
      setSelectedRange('custom');
    } else {
      setShowCustomInputs(false);
      setSelectedRange(val);
      setIsDateMenuOpen(false);
    }
  };

  const handleApplyCustomRange = (e: React.FormEvent) => {
    e.preventDefault();
    if (!customStartDate || !customEndDate) {
      toast.error('Please select both start and end dates');
      return;
    }
    if (new Date(customStartDate) > new Date(customEndDate)) {
      toast.error('Start date cannot be after end date');
      return;
    }
    setIsDateMenuOpen(false);
    fetchAnalytics('custom', customStartDate, customEndDate);
  };

  const selectedRangeLabel = useMemo(() => {
    if (selectedRange === 'custom' && customStartDate && customEndDate) {
      return `${customStartDate} to ${customEndDate}`;
    }
    const found = DATE_RANGE_OPTIONS.find((opt) => opt.value === selectedRange);
    return found ? found.label : 'Last 30 Days';
  }, [selectedRange, customStartDate, customEndDate]);

  if (isLoading) {
    return (
      <div className="flex h-[60vh] flex-col items-center justify-center gap-3">
        <Loader2 className="h-8 w-8 animate-spin text-indigo-600 dark:text-indigo-400" />
        <p className="text-sm font-medium text-slate-500">Loading deep analytics...</p>
      </div>
    );
  }

  if (error && !summary) {
    return (
      <div className="flex h-[60vh] flex-col items-center justify-center gap-4 text-center">
        <div className="p-3 rounded-full bg-rose-50 dark:bg-rose-950/40 text-rose-600">
          <AlertCircle className="h-8 w-8" />
        </div>
        <div>
          <h2 className="text-lg font-bold text-slate-900 dark:text-white">Failed to load Analytics</h2>
          <p className="text-xs text-slate-500 max-w-sm mt-1">{error}</p>
        </div>
        <button
          onClick={handleRefresh}
          className="px-4 py-2 text-xs font-semibold rounded-xl bg-indigo-600 text-white hover:bg-indigo-700 transition-colors cursor-pointer"
        >
          Try Again
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6 pb-12">
      {/* -------------------------------------------------- */}
      {/* HEADER: Title, Subtitle, Date Filter, Refresh     */}
      {/* -------------------------------------------------- */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-[28px] sm:text-[32px] font-bold tracking-tight text-slate-900 dark:text-white flex items-center gap-2">
            <span>Analytics</span>
          </h1>
          <p className="mt-1 text-[13.5px] text-slate-800 dark:text-slate-300">
            Insights to track your job search performance, identify trends and improve your outcomes.
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
              <div className="absolute right-0 mt-1.5 w-48 rounded-xl border border-slate-200 bg-white py-1 shadow-lg dark:border-slate-800 dark:bg-[#111726] z-30 menu-reveal">
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

                {showCustomInputs && (
                  <form
                    onSubmit={handleApplyCustomRange}
                    className="border-t border-slate-100 dark:border-slate-800 p-3 space-y-2 mt-1"
                  >
                    <div>
                      <label className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider block mb-1">
                        Start Date
                      </label>
                      <input
                        type="date"
                        value={customStartDate}
                        onChange={(e) => setCustomStartDate(e.target.value)}
                        className="w-full text-xs rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900 px-2 py-1 text-slate-800 dark:text-slate-200 focus:outline-hidden"
                      />
                    </div>
                    <div>
                      <label className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider block mb-1">
                        End Date
                      </label>
                      <input
                        type="date"
                        value={customEndDate}
                        onChange={(e) => setCustomEndDate(e.target.value)}
                        className="w-full text-xs rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900 px-2 py-1 text-slate-800 dark:text-slate-200 focus:outline-hidden"
                      />
                    </div>
                    <button
                      type="submit"
                      className="w-full mt-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white font-semibold py-1.5 text-xs transition-colors cursor-pointer"
                    >
                      Apply Range
                    </button>
                  </form>
                )}
              </div>
            )}
          </div>

          {/* Refresh Button */}
          <button
            type="button"
            onClick={handleRefresh}
            disabled={isRefreshing}
            className="inline-flex h-9 items-center gap-1.5 rounded-xl bg-indigo-600 px-3.5 text-[14px] font-medium text-white shadow-xs hover:bg-indigo-700 disabled:opacity-75 transition-colors cursor-pointer"
            title="Refresh analytics metrics"
          >
            <RotateCw className={`h-3.5 w-3.5 ${isRefreshing ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* -------------------------------------------------- */}
      {/* INTERNAL TABS: Job & Application Insights vs Agent */}
      {/* -------------------------------------------------- */}
      <div className="border-b border-slate-200 dark:border-slate-800">
        <nav
          className="flex space-x-8 overflow-x-auto no-scrollbar"
          role="tablist"
          aria-label="Analytics categories"
        >
          <button
            type="button"
            role="tab"
            id="tab-insights"
            aria-selected={activeTab === 'insights'}
            aria-controls="panel-insights"
            onClick={() => setActiveTab('insights')}
            className={`pb-3 pt-1 px-1 border-b-2 flex items-center gap-2.5 transition-colors cursor-pointer text-[14px] whitespace-nowrap ${activeTab === 'insights'
                ? 'border-indigo-600 text-indigo-600 dark:text-indigo-400 font-bold'
                : 'border-transparent text-slate-600 hover:text-slate-900 dark:text-slate-300 dark:hover:text-white font-semibold'
              }`}
          >
            <TrendingUp className="h-4.5 w-4.5" />
            <span>Job & Application Insights</span>
          </button>

          <button
            type="button"
            role="tab"
            id="tab-agent"
            aria-selected={activeTab === 'agent'}
            aria-controls="panel-agent"
            onClick={() => setActiveTab('agent')}
            className={`pb-3 pt-1 px-1 border-b-2 flex items-center gap-2.5 transition-colors cursor-pointer text-[14px] whitespace-nowrap ${activeTab === 'agent'
                ? 'border-indigo-600 text-indigo-600 dark:text-indigo-400 font-bold'
                : 'border-transparent text-slate-600 hover:text-slate-900 dark:text-slate-300 dark:hover:text-white font-semibold'
              }`}
          >
            <Bot className="h-4.5 w-4.5" />
            <span>Agent Performance</span>
          </button>
        </nav>
      </div>

      {/* -------------------------------------------------- */}
      {/* TAB 1: JOB & APPLICATION INSIGHTS                  */}
      {/* -------------------------------------------------- */}
      {activeTab === 'insights' && (
        <div
          id="panel-insights"
          role="tabpanel"
          aria-labelledby="tab-insights"
          className="space-y-6 page-reveal"
        >
          {/* SECTION 1: TOP KPI CARDS */}
          <AnalyticsKpiCards kpis={summary?.kpis} />

          {/* SECTION 2: JOB INTELLIGENCE */}
          <JobIntelligenceSection data={summary?.job_intelligence} />

          {/* SECTION 3: APPLICATION ANALYTICS */}
          <ApplicationAnalyticsSection data={summary?.application_analytics} />
        </div>
      )}

      {/* -------------------------------------------------- */}
      {/* TAB 2: AGENT PERFORMANCE                           */}
      {/* -------------------------------------------------- */}
      {activeTab === 'agent' && (
        <div
          id="panel-agent"
          role="tabpanel"
          aria-labelledby="tab-agent"
          className="space-y-6 page-reveal"
        >
          <AgentPerformanceSection data={summary?.agent_performance} />
        </div>
      )}
    </div>
  );
};
