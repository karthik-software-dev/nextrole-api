import React from 'react';
import {
  Database,
  SlidersHorizontal,
  CopyX,
  CheckCircle2,
  Send,
  ChevronRight,
  Lightbulb,
  Sparkles,
  Info,
} from 'lucide-react';
import type { AgentPerformance } from '../../types';

interface AgentPerformanceSectionProps {
  data?: AgentPerformance;
}

export const AgentPerformanceSection: React.FC<AgentPerformanceSectionProps> = ({ data }) => {
  const collected = data?.jobs_collected ?? 0;
  const normalized = data?.jobs_normalized ?? 0;
  const duplicates = data?.duplicates_removed ?? 0;
  const relevant = data?.relevant_jobs ?? 0;
  const actionable = data?.actionable_jobs ?? 0;
  const efficiency = data?.filtering_efficiency_pct ?? 0.0;
  const filteredOut = data?.filter_out_pct ?? 0.0;

  // Accurately calculated rates with fallbacks
  const relevanceRate =
    data?.relevance_rate_pct ??
    (normalized > 0 ? Math.round((relevant / normalized) * 1000) / 10 : 0.0);
  const actionableRate =
    data?.actionable_rate_pct ??
    (normalized > 0 ? Math.round((actionable / normalized) * 1000) / 10 : 0.0);
  const duplicateRate =
    collected > 0 ? Math.round((duplicates / collected) * 1000) / 10 : 0.0;
  const overallYieldRate =
    collected > 0 ? Math.round((actionable / collected) * 1000) / 10 : 0.0;

  // Inter-stage conversion percentages (calculated reliably from existing counts)
  const collectedToNormRate =
    collected > 0 ? Math.round((normalized / collected) * 1000) / 10 : 100;
  const normToRelevantRate =
    normalized > 0 ? Math.round((relevant / normalized) * 1000) / 10 : 0;
  const relevantToActionableRate =
    relevant > 0 ? Math.round((actionable / relevant) * 1000) / 10 : 0;

  // 5 Stages for Section 1: Processing Pipeline (Primary location for stage counts)
  const pipelineStages = [
    {
      id: 'collected',
      title: 'Jobs Collected',
      count: collected,
      icon: Database,
      color: 'text-blue-600 dark:text-blue-400',
      bg: 'bg-blue-50 dark:bg-blue-950/60',
      ring: 'ring-1 ring-inset ring-blue-600/15 dark:ring-blue-400/20',
      border: 'border-blue-100/90 dark:border-blue-900/40',
      cardBg: 'bg-blue-50/30 dark:bg-blue-950/20',
      badge: 'Raw Sighted',
      badgeStyle: 'bg-blue-100/80 text-blue-700 dark:bg-blue-950 dark:text-blue-300',
    },
    {
      id: 'normalized',
      title: 'Normalized',
      count: normalized,
      icon: SlidersHorizontal,
      color: 'text-purple-600 dark:text-purple-400',
      bg: 'bg-purple-50 dark:bg-purple-950/60',
      ring: 'ring-1 ring-inset ring-purple-600/15 dark:ring-purple-400/20',
      border: 'border-purple-100/90 dark:border-purple-900/40',
      cardBg: 'bg-purple-50/30 dark:bg-purple-950/20',
      badge: `${Math.round(collectedToNormRate)}% Retained`,
      badgeStyle: 'bg-purple-100/80 text-purple-700 dark:bg-purple-950 dark:text-purple-300',
    },
    {
      id: 'duplicates',
      title: 'Duplicates Removed',
      count: duplicates,
      icon: CopyX,
      color: 'text-amber-600 dark:text-amber-400',
      bg: 'bg-amber-50 dark:bg-amber-950/60',
      ring: 'ring-1 ring-inset ring-amber-600/15 dark:ring-amber-400/20',
      border: 'border-amber-100/90 dark:border-amber-900/40',
      cardBg: 'bg-amber-50/30 dark:bg-amber-950/20',
      badge: `${duplicates} Merged`,
      badgeStyle: 'bg-amber-100/80 text-amber-700 dark:bg-amber-950 dark:text-amber-300',
    },
    {
      id: 'relevant',
      title: 'Relevant Jobs',
      count: relevant,
      icon: CheckCircle2,
      color: 'text-emerald-600 dark:text-emerald-400',
      bg: 'bg-emerald-50 dark:bg-emerald-950/60',
      ring: 'ring-1 ring-inset ring-emerald-600/15 dark:ring-emerald-400/20',
      border: 'border-emerald-100/90 dark:border-emerald-900/40',
      cardBg: 'bg-emerald-50/30 dark:bg-emerald-950/20',
      badge: `${Math.round(normToRelevantRate)}% Match`,
      badgeStyle: 'bg-emerald-100/80 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300',
    },
    {
      id: 'actionable',
      title: 'Actionable Jobs',
      count: actionable,
      icon: Send,
      color: 'text-violet-600 dark:text-violet-400',
      bg: 'bg-violet-50 dark:bg-violet-950/60',
      ring: 'ring-1 ring-inset ring-violet-600/15 dark:ring-violet-400/20',
      border: 'border-violet-100/90 dark:border-violet-900/40',
      cardBg: 'bg-violet-50/30 dark:bg-violet-950/20',
      badge: `${Math.round(relevantToActionableRate)}% Tier 1`,
      badgeStyle: 'bg-violet-100/80 text-violet-700 dark:bg-violet-950 dark:text-violet-300',
    },
  ];

  return (
    <div className="space-y-6">
      {/* Section Header */}
      <div>
        <div className="flex items-center gap-1.5">
          <h2 className="text-[17px] font-bold text-slate-900 dark:text-white tracking-tight">
            Agent Performance
          </h2>
          <span title="Monitor scraping efficiency, filtering precision, and deduplication standards">
            <Info className="h-3.5 w-3.5 text-slate-400 cursor-help" />
          </span>
        </div>
        <p className="mt-1 text-[13.5px] text-slate-800 dark:text-slate-300">
          Monitor scraping efficiency, filtering precision, and deduplication standards.
        </p>
      </div>

      {/* ============================================================== */}
      {/* SECTION 1: PROCESSING PIPELINE (Full Width)                    */}
      {/* ============================================================== */}
      <div className="p-5 sm:p-6 rounded-2xl border border-slate-200/80 dark:border-slate-800 bg-white dark:bg-[#111726] shadow-sm">
        {/* Header without live "Pipeline Active" badge */}
        <div className="border-b border-slate-100 dark:border-slate-800/80 pb-3 flex items-center justify-between">
          <div>
            <h3 className="text-[17px] font-bold tracking-tight text-slate-900 dark:text-white">
              Processing Pipeline
            </h3>
            <p className="text-[13.5px] text-slate-800 dark:text-slate-300">
              End-to-end ingestion, deduplication, and quality screening
            </p>
          </div>
          <span className="text-[12.5px] font-medium text-slate-700 dark:text-slate-400">
            5 processing stages
          </span>
        </div>

        {/* 5 Stages Stepper */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-2.5 sm:gap-3 pt-5">
          {pipelineStages.map((stage, idx) => {
            const Icon = stage.icon;
            const isLast = idx === pipelineStages.length - 1;

            return (
              <React.Fragment key={stage.id}>
                {/* Stage Card */}
                <div
                  className={`flex-1 w-full sm:w-auto min-h-[175px] rounded-2xl border ${stage.border} ${stage.cardBg} p-4 sm:py-5 sm:px-4 flex flex-col items-center justify-between text-center transition-all duration-200 hover:-translate-y-0.5 hover:shadow-sm`}
                >
                  <div className="flex flex-col items-center">
                    {/* Squircle Glyph */}
                    <div
                      className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-xl ${stage.bg} ${stage.color} ${stage.ring} shadow-xs mb-2.5`}
                    >
                      <Icon className="h-5 w-5" />
                    </div>

                    {/* Stage Title */}
                    <span className="text-[16px] font-semibold text-slate-800 dark:text-slate-200 leading-tight">
                      {stage.title}
                    </span>

                    {/* Large Count */}
                    <span className="text-[28px] font-bold text-slate-900 dark:text-white leading-tight mt-1">
                      {stage.count.toLocaleString()}
                    </span>
                  </div>

                  {/* Conversion / Status Badge */}
                  <div className="mt-3">
                    <span
                      className={`inline-flex items-center px-2.5 py-0.5 rounded-md text-[13px] font-semibold ${stage.badgeStyle}`}
                    >
                      {stage.badge}
                    </span>
                  </div>
                </div>

                {/* Connecting Chevron Arrow */}
                {!isLast && (
                  <div className="hidden sm:flex items-center text-slate-300 dark:text-slate-600 px-0.5 shrink-0">
                    <ChevronRight className="h-5 w-5" strokeWidth={2.2} />
                  </div>
                )}
              </React.Fragment>
            );
          })}
        </div>
      </div>

      {/* ============================================================== */}
      {/* SECTION 2: STREAMLINED METRICS & HIGHLIGHTS (Single Row)       */}
      {/* ============================================================== */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* CARD 1: FILTERING EFFICIENCY & CONVERSION RATES */}
        <div className="p-5 sm:p-6 rounded-2xl border border-slate-200/80 dark:border-slate-800 bg-white dark:bg-[#111726] shadow-sm flex flex-col justify-between min-h-[295px]">
          {/* Header */}
          <div className="border-b border-slate-100 dark:border-slate-800/80 pb-3 flex items-center justify-between">
            <div>
              <h3 className="text-[17px] font-bold tracking-tight text-slate-900 dark:text-white">
                Filtering Efficiency & Rates
              </h3>
              <p className="mt-1 text-[13.5px] text-slate-800 dark:text-slate-300">
                Conversion and screening performance metrics
              </p>
            </div>
            <span className="text-[13px] font-medium text-slate-800 dark:text-slate-400">
              {Math.round(efficiency)}% conversion
            </span>
          </div>

          {/* Body: Donut Ring on Left + 3 Progress Rows on Right */}
          <div className="flex flex-col sm:flex-row items-center gap-6 my-auto py-3">
            {/* SVG Progress Ring */}
            <div className="relative h-24 w-24 shrink-0 flex items-center justify-center">
              <svg className="h-full w-full -rotate-90" viewBox="0 0 36 36">
                <circle
                  cx="18"
                  cy="18"
                  r="15.915"
                  className="stroke-slate-100 dark:stroke-slate-800 fill-none"
                  strokeWidth="3.2"
                />
                <circle
                  cx="18"
                  cy="18"
                  r="15.915"
                  className="stroke-blue-600 dark:stroke-blue-500 fill-none transition-all duration-700"
                  strokeWidth="3.2"
                  strokeDasharray={`${efficiency}, 100`}
                  strokeLinecap="round"
                />
              </svg>
              <div className="absolute flex flex-col items-center justify-center">
                <span className="font-black text-[24px] tracking-tight text-slate-900 dark:text-white leading-none">
                  {Math.round(efficiency)}%
                </span>
                <span className="text-[12px] font-semibold text-slate-800 dark:text-slate-500 uppercase tracking-wider mt-1">
                  Yield
                </span>
              </div>
            </div>

            {/* 3 Progress Bars */}
            <div className="flex-1 w-full space-y-3">
              {/* Relevance Rate */}
              <div>
                <div className="flex items-center justify-between text-xs mb-1">
                  <div className="flex items-center gap-1.5">
                    <span className="h-2.5 w-2.5 rounded-full bg-emerald-500 shrink-0" />
                    <span className="text-[13.5px] font-medium text-slate-800 dark:text-slate-200">
                      Relevance Rate
                    </span>
                  </div>
                  <span className="text-[13px] font-semibold text-slate-900 mb-2 dark:text-white tabular-nums">
                    {relevanceRate}%
                  </span>
                </div>
                <div className="h-2 w-full rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
                  <div
                    className="h-full rounded-full bg-emerald-500 transition-all duration-500"
                    style={{ width: `${Math.min(100, relevanceRate)}%` }}
                  />
                </div>
              </div>

              {/* Actionable Rate */}
              <div>
                <div className="flex items-center justify-between text-xs mb-1">
                  <div className="flex items-center gap-1.5">
                    <span className="h-2.5 w-2.5 rounded-full bg-violet-500 shrink-0" />
                    <span className="text-[13.5px] font-medium text-slate-800 dark:text-slate-200">
                      Actionable Rate
                    </span>
                  </div>
                  <span className="text-[13px] font-semibold text-slate-900 dark:text-white tabular-nums">
                    {actionableRate}%
                  </span>
                </div>
                <div className="h-2 w-full rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
                  <div
                    className="h-full rounded-full bg-violet-500 transition-all duration-500"
                    style={{ width: `${Math.min(100, actionableRate)}%` }}
                  />
                </div>
              </div>

              {/* Duplicate Rate */}
              <div>
                <div className="flex items-center justify-between text-xs mb-1">
                  <div className="flex items-center gap-1.5">
                    <span className="h-2.5 w-2.5 rounded-full bg-amber-500 shrink-0" />
                    <span className="text-[13.5px] font-medium text-slate-800 dark:text-slate-200">
                      Duplicate Rate
                    </span>
                  </div>
                  <span className="text-[13px] font-semibold text-slate-900 dark:text-white tabular-nums">
                    {duplicateRate}%
                  </span>
                </div>
                <div className="h-2 w-full rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
                  <div
                    className="h-full rounded-full bg-amber-500 transition-all duration-500"
                    style={{ width: `${Math.min(100, duplicateRate)}%` }}
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Footer */}
          <div className="pt-3 border-t border-slate-100 dark:border-slate-800/80 flex items-center justify-between text-xs text-slate-500 dark:text-slate-400">
            <span className="font-medium text-slate-800 dark:text-slate-300 text-[13px]">Overall Pipeline Yield</span>
            <span className="font-bold text-slate-900 dark:text-white text-[13px]">
              {overallYieldRate}% <span className="font-medium text-slate-800 dark:text-slate-400">of sighted postings reach Actionable tier</span>
            </span>
          </div>
        </div>

        {/* CARD 2: AGENT HIGHLIGHTS */}
        <div className="p-5 sm:p-6 rounded-2xl border border-slate-200/80 dark:border-slate-800 bg-white dark:bg-[#111726] shadow-sm flex flex-col justify-between min-h-[295px]">
          {/* Header */}
          <div className="border-b border-slate-100 dark:border-slate-800/80 pb-3 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Sparkles className="h-4.5 w-4.5 text-indigo-500" />
              <h3 className="text-[17px] font-bold tracking-tight text-slate-900 dark:text-white">
                Agent Highlights
              </h3>
            </div>
            <span className="text-[13px] font-medium text-slate-800 dark:text-slate-400">
              Active Evaluation
            </span>
          </div>

          {/* 3 Concise 1-Line Data-Backed Insights */}
          <div className="space-y-3 my-auto py-2">
            {/* Item 1: High Relevance */}
            <div className="p-3 rounded-xl bg-emerald-50/70 dark:bg-emerald-950/30 border border-emerald-100/90 dark:border-emerald-900/40 flex items-center gap-3">
              <div className="p-1.5 rounded-lg bg-emerald-100 dark:bg-emerald-900/60 text-emerald-600 dark:text-emerald-400 shrink-0">
                <CheckCircle2 className="h-4 w-4" />
              </div>
              <div className="min-w-0">
                <p className="text-[13.5px] text-slate-800 dark:text-slate-200 font-medium leading-snug">
                  <span className="font-bold text-emerald-700 dark:text-emerald-300">{relevanceRate}%</span> of normalized jobs strongly match your profile criteria.
                </p>
              </div>
            </div>

            {/* Item 2: Selective Screening */}
            <div className="p-3 rounded-xl bg-blue-50/70 dark:bg-blue-950/30 border border-blue-100/90 dark:border-blue-900/40 flex items-center gap-3">
              <div className="p-1.5 rounded-lg bg-blue-100 dark:bg-blue-900/60 text-blue-600 dark:text-blue-400 shrink-0">
                <Lightbulb className="h-4 w-4" />
              </div>
              <div className="min-w-0">
                <p className="text-[13.5px] text-slate-800 dark:text-slate-200 font-medium leading-snug">
                  <span className="font-bold text-blue-700 dark:text-blue-300">{filteredOut}%</span> deprioritized to preserve focus strictly on Tier-1 opportunities.
                </p>
              </div>
            </div>

            {/* Item 3: Deduplication */}
            <div className="p-3 rounded-xl bg-amber-50/70 dark:bg-amber-950/30 border border-amber-100/90 dark:border-amber-900/40 flex items-center gap-3">
              <div className="p-1.5 rounded-lg bg-amber-100 dark:bg-amber-900/60 text-amber-600 dark:text-amber-400 shrink-0">
                <CopyX className="h-4 w-4" />
              </div>
              <div className="min-w-0">
                <p className="text-[13.5px] text-slate-800 dark:text-slate-200 font-medium leading-snug">
                  <span className="font-bold text-amber-700 dark:text-amber-300">{duplicates}</span> duplicate postings automatically identified and merged.
                </p>
              </div>
            </div>
          </div>

          {/* Footer */}
          <div className="pt-3 border-t border-slate-100 dark:border-slate-800/80 flex items-center justify-between text-xs text-slate-500 dark:text-slate-400">
            <span className="font-medium text-slate-800 dark:text-slate-300 text-[13px]">Intelligence Engine</span>
            <span className="font-bold text-slate-800 dark:text-slate-200 text-[13px]">
              High Precision Standard
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AgentPerformanceSection;
