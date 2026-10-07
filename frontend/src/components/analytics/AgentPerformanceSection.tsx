import React from 'react';
import {
  Database,
  SlidersHorizontal,
  CopyX,
  CheckCircle2,
  Send,
  ChevronRight,
  TrendingUp,
  Filter,
} from 'lucide-react';
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import type { PipelineAnalytics, AgentPerformance, ApplyGatewayItem } from '../../types';

const GATEWAY_COLOR_MAP: Record<string, string> = {
  'Company Careers': '#3B82F6',
  'Aggregator Redirect': '#8B5CF6',
  'Direct ATS': '#10B981',
  'Direct / Other': '#94A3B8',
};

const TIER_COLOR_MAP: Record<string, string> = {
  'Tier 1': '#8B5CF6',
  'Tier 2': '#3B82F6',
  'Tier 3': '#64748B',
};

interface PipelineAnalyticsSectionProps {
  data?: PipelineAnalytics | AgentPerformance;
}

export const PipelineAnalyticsSection: React.FC<PipelineAnalyticsSectionProps> = ({ data }) => {
  const collected = data?.jobs_collected ?? 0;
  const normalized = data?.jobs_normalized ?? 0;
  const duplicates = data?.duplicates_removed ?? 0;
  const relevant = data?.relevant_jobs ?? 0;
  const actionable = data?.actionable_jobs ?? 0;
  const tierBreakdown = data?.tier_breakdown ?? [];
  const gatewaysBreakdown = data?.gateways_breakdown ?? [];
  const totalJobs = tierBreakdown.reduce((acc, t) => acc + t.count, 0) || normalized;

  // Inter-stage conversion percentages (calculated reliably from existing real source metrics)
  const collectedToNormRate =
    collected > 0 ? Math.round((normalized / collected) * 1000) / 10 : 100.0;
  const normToRelevantRate =
    normalized > 0 ? Math.round((relevant / normalized) * 1000) / 10 : 0.0;
  const relevantToActionableRate =
    relevant > 0 ? Math.round((actionable / relevant) * 1000) / 10 : 0.0;

  // 5 Stages for Section 3.1: Processing Pipeline
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
      badge: `${collectedToNormRate}% Retained`,
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
      badge: `${normToRelevantRate}% Match`,
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
      badge: `${relevantToActionableRate}% Tier 1`,
      badgeStyle: 'bg-violet-100/80 text-violet-700 dark:bg-violet-950 dark:text-violet-300',
    },
  ];

  return (
    <div className="space-y-6">
      {/* -------------------------------------------------- */}
      {/* SECTION 3.1 & 3.2 — PROCESSING PIPELINE & CONVERSION */}
      {/* -------------------------------------------------- */}
      <div className="p-5 sm:p-6 rounded-2xl border border-slate-200/80 dark:border-slate-800 bg-white dark:bg-[#111726] shadow-sm">
        <div className="border-b border-slate-100 dark:border-slate-800/80 pb-3 flex items-center justify-between">
          <h3 className="text-[17px] font-bold tracking-tight text-slate-900 dark:text-white">
            Processing Pipeline
          </h3>
          <span className="text-[12.5px] font-medium text-slate-700 dark:text-slate-400">
            5 operational stages
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
                    <div
                      className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-xl ${stage.bg} ${stage.color} ${stage.ring} shadow-xs mb-2.5`}
                    >
                      <Icon className="h-5 w-5" />
                    </div>

                    <span className="text-[16px] font-semibold text-slate-800 dark:text-slate-200 leading-tight">
                      {stage.title}
                    </span>

                    <span className="text-[28px] font-bold text-slate-900 dark:text-white leading-tight mt-1">
                      {stage.count.toLocaleString()}
                    </span>
                  </div>

                  <div className="mt-3">
                    <span
                      className={`inline-flex items-center px-2.5 py-0.5 rounded-md text-[12.5px] font-semibold ${stage.badgeStyle}`}
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

        {/* Section 3.2: Pipeline Conversion Callouts */}
        <div className="mt-6 pt-5 border-t border-slate-100 dark:border-slate-800/80">
          <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-3">
            Pipeline Conversion & Efficiency
          </h4>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3.5">
            <div className="p-3.5 rounded-xl border border-slate-200/60 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/40 flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-700 dark:text-slate-300">Deduplication Yield</span>
              <span className="text-sm font-bold text-indigo-600 dark:text-indigo-400 tabular-nums">{collectedToNormRate}%</span>
            </div>

            <div className="p-3.5 rounded-xl border border-slate-200/60 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/40 flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-700 dark:text-slate-300">Relevance Qualification</span>
              <span className="text-sm font-bold text-emerald-600 dark:text-emerald-400 tabular-nums">{normToRelevantRate}%</span>
            </div>

            <div className="p-3.5 rounded-xl border border-slate-200/60 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/40 flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-700 dark:text-slate-300">Actionable Triage</span>
              <span className="text-sm font-bold text-violet-600 dark:text-violet-400 tabular-nums">{relevantToActionableRate}%</span>
            </div>
          </div>
        </div>
      </div>

      {/* -------------------------------------------------- */}
      {/* SECTIONS 3.3 & 3.4 — INGESTION SOURCE & PRIORITY   */}
      {/* -------------------------------------------------- */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* SECTION 3.3: INGESTION SOURCE PERFORMANCE */}
        <div className="relative flex min-h-[380px] sm:min-h-0 sm:h-[315px] flex-col overflow-hidden rounded-2xl border border-slate-200/80 bg-white p-4 sm:p-5 shadow-sm transition-[transform,box-shadow,border-color] duration-180 ease-out hover:-translate-y-0.5 hover:shadow-md dark:border-slate-800 dark:bg-[#111726]">
          <div className="flex items-start justify-between border-b border-slate-100 pb-3 dark:border-slate-800">
            <h3 className="text-[17px] font-bold tracking-tight text-slate-900 dark:text-white">
              Ingestion Source Performance
            </h3>
            <span className="text-[12.5px] font-medium text-slate-700 dark:text-slate-400">
              {totalJobs} total jobs
            </span>
          </div>

          <div className="flex flex-1 flex-col sm:flex-row items-center gap-4 pt-3">
            {gatewaysBreakdown.length === 0 ? (
              <div className="flex h-full w-full items-center justify-center text-xs text-slate-400">
                No gateway breakdown available.
              </div>
            ) : (
              <>
                <div className="relative shrink-0 w-[155px] h-[155px] sm:w-[185px] sm:h-[185px] mx-auto sm:mx-0">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Tooltip
                        content={({ active, payload }) => {
                          if (active && payload && payload.length) {
                            const d = payload[0].payload as ApplyGatewayItem;
                            return (
                              <div className="rounded-lg bg-slate-900 px-3 py-2 text-xs text-white shadow-lg">
                                <p className="font-bold text-white">{d.gateway}</p>
                                <p className="mt-0.5 font-medium text-slate-300">
                                  {d.count} {d.count === 1 ? 'job' : 'jobs'} · {d.percentage}%
                                </p>
                              </div>
                            );
                          }
                          return null;
                        }}
                      />
                      <Pie
                        data={gatewaysBreakdown}
                        cx="50%"
                        cy="50%"
                        innerRadius="64%"
                        outerRadius="94%"
                        paddingAngle={3}
                        dataKey="count"
                        strokeWidth={0}
                        animationDuration={350}
                        animationEasing="ease-out"
                      >
                        {gatewaysBreakdown.map((entry, index) => (
                          <Cell
                            key={`gw-${index}`}
                            fill={
                              entry.color ||
                              GATEWAY_COLOR_MAP[entry.gateway] ||
                              '#64748B'
                            }
                          />
                        ))}
                      </Pie>
                    </PieChart>
                  </ResponsiveContainer>

                  <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                    <span className="text-[22px] sm:text-[26px] font-black tracking-tight text-slate-900 dark:text-white leading-none">
                      {totalJobs}
                    </span>
                    <span className="text-[10px] sm:text-[11px] font-semibold text-slate-700 dark:text-slate-500 mt-1 uppercase tracking-wider">
                      Total Jobs
                    </span>
                  </div>
                </div>

                <div className="w-full sm:flex-1 flex flex-col min-w-0 select-none overflow-y-auto max-h-[170px] sm:max-h-[188px] space-y-2 sm:pr-2 my-auto">
                  {gatewaysBreakdown.map((item) => (
                    <div
                      key={item.gateway}
                      className="flex h-[28px] shrink-0 items-center justify-between gap-1.5 sm:gap-2"
                    >
                      <div className="flex items-center gap-2 min-w-0">
                        <span
                          className="h-2.5 w-2.5 rounded-full shrink-0"
                          style={{
                            backgroundColor:
                              item.color ||
                              GATEWAY_COLOR_MAP[item.gateway] ||
                              '#64748B',
                          }}
                        />
                        <span className="text-[12.5px] sm:text-[13.5px] font-medium text-slate-800 dark:text-slate-200 truncate">
                          {item.gateway}
                        </span>
                      </div>
                      <div className="flex items-center gap-1 sm:gap-1.5 shrink-0">
                        <span className="text-[12.5px] sm:text-[13.5px] font-bold text-slate-800 dark:text-slate-100 tabular-nums">
                          {item.count}
                        </span>
                        <span className="text-[11.5px] sm:text-[12.5px] font-medium text-slate-600 dark:text-slate-400 tabular-nums">
                          ({item.percentage}%)
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </>
            )}
          </div>
        </div>

        {/* SECTION 3.4: PRIORITY DISTRIBUTION */}
        <div className="relative flex min-h-[380px] sm:min-h-0 sm:h-[315px] flex-col overflow-hidden rounded-2xl border border-slate-200/80 bg-white p-4 sm:p-5 shadow-sm transition-[transform,box-shadow,border-color] duration-180 ease-out hover:-translate-y-0.5 hover:shadow-md dark:border-slate-800 dark:bg-[#111726]">
          <div className="flex items-start justify-between border-b border-slate-100 pb-3 dark:border-slate-800">
            <h3 className="text-[17px] font-bold tracking-tight text-slate-900 dark:text-white">
              Jobs by Priority Tier
            </h3>
            <span className="text-[12.5px] font-medium text-slate-700 dark:text-slate-400">
              {totalJobs} total jobs
            </span>
          </div>

          <div className="flex flex-1 flex-col sm:flex-row items-center gap-4 pt-3">
            {tierBreakdown.length === 0 ? (
              <div className="flex h-full w-full items-center justify-center text-xs text-slate-400">
                No tier breakdown available.
              </div>
            ) : (
              <>
                <div className="relative shrink-0 w-[155px] h-[155px] sm:w-[185px] sm:h-[185px] mx-auto sm:mx-0">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Tooltip
                        content={({ active, payload }) => {
                          if (active && payload && payload.length) {
                            const d = payload[0].payload as (typeof tierBreakdown)[0];
                            return (
                              <div className="rounded-lg bg-slate-900 px-3 py-2 text-xs text-white shadow-lg">
                                <p className="font-bold text-white">
                                  {d.tier} · {d.label}
                                </p>
                                <p className="mt-0.5 font-medium text-slate-300">
                                  {d.count} {d.count === 1 ? 'job' : 'jobs'} · {d.percentage}%
                                </p>
                              </div>
                            );
                          }
                          return null;
                        }}
                      />
                      <Pie
                        data={tierBreakdown}
                        cx="50%"
                        cy="50%"
                        innerRadius="64%"
                        outerRadius="94%"
                        paddingAngle={3}
                        dataKey="count"
                        strokeWidth={0}
                        animationDuration={350}
                        animationEasing="ease-out"
                      >
                        {tierBreakdown.map((entry, index) => (
                          <Cell
                            key={`tier-${index}`}
                            fill={entry.color || TIER_COLOR_MAP[entry.tier] || '#64748B'}
                          />
                        ))}
                      </Pie>
                    </PieChart>
                  </ResponsiveContainer>

                  <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                    <span className="text-[22px] sm:text-[26px] font-black tracking-tight text-slate-900 dark:text-white leading-none">
                      {totalJobs}
                    </span>
                    <span className="text-[10px] sm:text-[11px] font-semibold text-slate-700 dark:text-slate-500 mt-1 uppercase tracking-wider">
                      Total Jobs
                    </span>
                  </div>
                </div>

                <div className="w-full sm:flex-1 flex flex-col min-w-0 select-none overflow-y-auto max-h-[170px] sm:max-h-[188px] space-y-2 sm:pr-2 my-auto">
                  {tierBreakdown.map((item) => (
                    <div
                      key={item.tier}
                      className="flex h-[28px] shrink-0 items-center justify-between gap-1.5 sm:gap-2"
                    >
                      <div className="flex items-center gap-2 min-w-0">
                        <span
                          className="h-2.5 w-2.5 rounded-full shrink-0"
                          style={{ backgroundColor: item.color }}
                        />
                        <span className="text-[12.5px] sm:text-[13.5px] font-medium text-slate-800 dark:text-slate-200 truncate">
                          {item.tier}{' '}
                          <span className="text-[11px] sm:text-[12px] text-slate-500 dark:text-slate-400">
                            ({item.label})
                          </span>
                        </span>
                      </div>
                      <div className="flex items-center gap-1 sm:gap-1.5 shrink-0">
                        <span className="text-[12.5px] sm:text-[13.5px] font-bold text-slate-800 dark:text-slate-100 tabular-nums">
                          {item.count}
                        </span>
                        <span className="text-[11.5px] sm:text-[12.5px] font-medium text-slate-600 dark:text-slate-400 tabular-nums">
                          ({item.percentage}%)
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export const AgentPerformanceSection = PipelineAnalyticsSection;
export default PipelineAnalyticsSection;
