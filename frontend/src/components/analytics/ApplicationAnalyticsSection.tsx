import React from 'react';
import { Link } from 'react-router-dom';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from 'recharts';
import {
  Database,
  Clock,
  Users,
  Award,
  ChevronRight,
  Send,
} from 'lucide-react';
import type { ApplicationAnalytics } from '../../types';

interface ApplicationAnalyticsSectionProps {
  data?: ApplicationAnalytics;
  applyChannels?: unknown;
}

const STAGE_VISUALS: Record<
  string,
  {
    icon: React.ElementType;
    color: string;
    bg: string;
    ring: string;
    border: string;
    cardBg: string;
    badgeStyle: string;
  }
> = {
  Applied: {
    icon: Database,
    color: 'text-blue-600 dark:text-blue-400',
    bg: 'bg-blue-50 dark:bg-blue-950/60',
    ring: 'ring-1 ring-inset ring-blue-600/15 dark:ring-blue-400/20',
    border: 'border-blue-100/90 dark:border-blue-900/40',
    cardBg: 'bg-blue-50/30 dark:bg-blue-950/20',
    badgeStyle: 'bg-blue-100/80 text-blue-700 dark:bg-blue-950 dark:text-blue-300',
  },
  'Under Review': {
    icon: Clock,
    color: 'text-purple-600 dark:text-purple-400',
    bg: 'bg-purple-50 dark:bg-purple-950/60',
    ring: 'ring-1 ring-inset ring-purple-600/15 dark:ring-purple-400/20',
    border: 'border-purple-100/90 dark:border-purple-900/40',
    cardBg: 'bg-purple-50/30 dark:bg-purple-950/20',
    badgeStyle: 'bg-purple-100/80 text-purple-700 dark:bg-purple-950 dark:text-purple-300',
  },
  Interview: {
    icon: Users,
    color: 'text-emerald-600 dark:text-emerald-400',
    bg: 'bg-emerald-50 dark:bg-emerald-950/60',
    ring: 'ring-1 ring-inset ring-emerald-600/15 dark:ring-emerald-400/20',
    border: 'border-emerald-100/90 dark:border-emerald-900/40',
    cardBg: 'bg-emerald-50/30 dark:bg-emerald-950/20',
    badgeStyle: 'bg-emerald-100/80 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300',
  },
  Offer: {
    icon: Award,
    color: 'text-amber-600 dark:text-amber-400',
    bg: 'bg-amber-50 dark:bg-amber-950/60',
    ring: 'ring-1 ring-inset ring-amber-600/15 dark:ring-amber-400/20',
    border: 'border-amber-100/90 dark:border-amber-900/40',
    cardBg: 'bg-amber-50/30 dark:bg-amber-950/20',
    badgeStyle: 'bg-amber-100/80 text-amber-700 dark:bg-amber-950 dark:text-amber-300',
  },
};

export const ApplicationAnalyticsSection: React.FC<ApplicationAnalyticsSectionProps> = ({
  data,
}) => {
  const overTime = data?.applications_over_time ?? [];
  const statusDist = data?.status_distribution ?? [];
  const funnel = data?.funnel ?? [];

  const totalApplications = statusDist.reduce((acc, s) => acc + s.count, 0);
  const totalOverTime = overTime.reduce((acc, d) => acc + d.count, 0);

  return (
    <div className="space-y-6">
      {/* -------------------------------------------------- */}
      {/* SECTION 1.2 — APPLICATION ACTIVITY                 */}
      {/* -------------------------------------------------- */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        {/* Card 1: Applications Over Time */}
        <div className="lg:col-span-7 p-4 sm:p-5 rounded-2xl border border-slate-200/80 dark:border-slate-800 bg-white dark:bg-[#111726] shadow-sm flex flex-col justify-between h-[300px]">
          <div className="flex items-start justify-between border-b border-slate-100 pb-3 dark:border-slate-800">
            <h3 className="text-[17px] font-bold tracking-tight text-slate-900 dark:text-white">
              Applications Over Time
            </h3>
            <span className="text-[12.5px] font-medium text-slate-700 dark:text-slate-400">
              {totalOverTime} total in period
            </span>
          </div>

          <div className="flex-1 w-full mt-2">
            {totalOverTime === 0 && totalApplications === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-center p-4">
                <Send className="h-7 w-7 text-slate-300 dark:text-slate-600 mb-2" />
                <p className="text-[13px] font-semibold text-slate-700 dark:text-slate-300">
                  No applications recorded in this period
                </p>
                <p className="text-[11.5px] text-slate-500 dark:text-slate-400 max-w-xs mt-1">
                  When you apply to opportunities from your feed, submission activity will plot here.
                </p>
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={overTime} margin={{ top: 12, right: 8, left: -16, bottom: 0 }}>
                  <defs>
                    <linearGradient id="appTimeGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#8B5CF6" stopOpacity={0.25} />
                      <stop offset="95%" stopColor="#8B5CF6" stopOpacity={0.0} />
                    </linearGradient>
                  </defs>
                  <XAxis
                    dataKey="date"
                    tickLine={false}
                    axisLine={false}
                    tick={{ fontSize: 11, fill: '#64748B', fontWeight: 600, fontFamily: 'Inter, sans-serif' }}
                    tickFormatter={(val) => {
                      try {
                        const d = new Date(val);
                        return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
                      } catch {
                        return val;
                      }
                    }}
                  />
                  <YAxis
                    tickLine={false}
                    axisLine={false}
                    tick={{ fontSize: 11, fill: '#64748B', fontWeight: 600, fontFamily: 'Inter, sans-serif' }}
                    allowDecimals={false}
                  />
                  <Tooltip
                    cursor={{ stroke: '#8B5CF6', strokeWidth: 1, strokeDasharray: '3 3' }}
                    content={({ active, payload }) => {
                      if (active && payload && payload.length) {
                        const d = payload[0].payload;
                        return (
                          <div className="rounded-lg bg-slate-900 px-3 py-2 text-xs text-white shadow-md">
                            <p className="font-semibold text-slate-200">{d.date}</p>
                            <p className="mt-0.5 font-bold text-violet-400">
                              {d.count} {d.count === 1 ? 'application' : 'applications'} submitted
                            </p>
                          </div>
                        );
                      }
                      return null;
                    }}
                  />
                  <Area
                    type="monotone"
                    dataKey="count"
                    stroke="#8B5CF6"
                    strokeWidth={2.5}
                    fillOpacity={1}
                    fill="url(#appTimeGradient)"
                    dot={{ r: 4, fill: '#8B5CF6', strokeWidth: 1.5, stroke: '#fff' }}
                    activeDot={{ r: 6, fill: '#7C3AED' }}
                    animationDuration={350}
                    animationEasing="ease-out"
                  />
                </AreaChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        {/* Card 2: Application Status Donut */}
        <div className="lg:col-span-5 p-4 sm:p-5 rounded-2xl border border-slate-200/80 dark:border-slate-800 bg-white dark:bg-[#111726] shadow-sm flex flex-col justify-between min-h-[380px] sm:min-h-0 sm:h-[300px]">
          <div className="flex items-start justify-between border-b border-slate-100 pb-3 dark:border-slate-800">
            <h3 className="text-[17px] font-bold tracking-tight text-slate-900 dark:text-white">
              Application Status
            </h3>
            <span className="text-[12.5px] font-medium text-slate-700 dark:text-slate-400">
              {totalApplications} total
            </span>
          </div>

          <div className="flex-1 flex flex-col sm:flex-row items-center justify-between gap-4 mt-1">
            {/* Center Donut */}
            <div className="relative shrink-0 w-[155px] h-[155px] sm:w-1/2 sm:h-[200px] flex items-center justify-center mx-auto sm:mx-0">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={totalApplications > 0 ? statusDist : [{ status: 'No Applications', count: 1 }]}
                    dataKey="count"
                    nameKey="status"
                    cx="50%"
                    cy="50%"
                    innerRadius="64%"
                    outerRadius="94%"
                    paddingAngle={totalApplications > 0 ? 3 : 0}
                    animationDuration={350}
                    animationEasing="ease-out"
                  >
                    {totalApplications > 0 ? (
                      statusDist.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))
                    ) : (
                      <Cell fill="rgba(148, 163, 184, 0.2)" />
                    )}
                  </Pie>
                  {totalApplications > 0 && (
                    <Tooltip
                      content={({ active, payload }) => {
                        if (active && payload && payload.length) {
                          const d = payload[0].payload as (typeof statusDist)[0];
                          return (
                            <div className="rounded-lg bg-slate-900 px-3 py-2 text-xs text-white shadow-md">
                              <p className="font-semibold text-slate-200">{d.status}</p>
                              <p className="mt-0.5 font-bold text-slate-300">
                                {d.count} ({d.percentage}%)
                              </p>
                            </div>
                          );
                        }
                        return null;
                      }}
                    />
                  )}
                </PieChart>
              </ResponsiveContainer>

              {/* Total overlay in center */}
              <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                <span className="text-[22px] sm:text-[26px] font-black tracking-tight text-slate-900 dark:text-white leading-none">
                  {totalApplications}
                </span>
                <span className="text-[10px] sm:text-[11px] font-semibold text-slate-700 dark:text-slate-500 mt-1 uppercase tracking-wider">
                  Applications
                </span>
              </div>
            </div>

            {/* Right Legend: 2-column grid on mobile, vertical list on desktop */}
            <div className="w-full sm:flex-1 grid grid-cols-2 sm:flex sm:flex-col sm:justify-center gap-x-3 gap-y-1.5 sm:gap-0 sm:space-y-2.5 min-w-0 select-none pr-1">
              {statusDist.map((s) => (
                <div key={s.status} className="flex items-center justify-between gap-1.5 sm:gap-2">
                  <div className="flex items-center gap-1.5 sm:gap-2 min-w-0">
                    <span
                      className="h-2 w-2 sm:h-2.5 sm:w-2.5 rounded-full shrink-0"
                      style={{ backgroundColor: s.color }}
                    />
                    <span className="text-[12px] sm:text-[13px] font-medium text-slate-800 dark:text-slate-200 truncate">
                      {s.status}
                    </span>
                  </div>
                  <div className="flex items-center gap-1 sm:gap-1.5 shrink-0">
                    <span className="text-[12px] sm:text-[13px] font-bold text-slate-800 dark:text-slate-100 tabular-nums">
                      {s.count}
                    </span>
                    <span className="text-[11px] sm:text-[12px] font-medium text-slate-500 dark:text-slate-400 tabular-nums">
                      ({s.percentage}%)
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* -------------------------------------------------- */}
      {/* SECTION 1.3 — APPLICATION FUNNEL                   */}
      {/* -------------------------------------------------- */}
      {(() => {
        const appliedCount = funnel[0]?.count || 0;
        const offerCount = funnel.find((f) => f.stage === 'Offer')?.count || 0;
        const overallYield =
          appliedCount > 0 ? Math.round((offerCount / appliedCount) * 1000) / 10 : 0.0;

        const getConversionLabel = (idx: number, step: (typeof funnel)[0]) => {
          if (totalApplications === 0) return 'Awaiting apps';
          if (idx === 0) return '100% Submissions';
          if (idx === 1) return `${step.conversion_rate}% from Applied`;
          if (idx === 2) return `${step.conversion_rate}% from Review`;
          if (idx === 3) return `${step.conversion_rate}% from Interview`;
          return `${step.conversion_rate}% conversion`;
        };

        return (
          <div className="p-5 sm:p-6 rounded-2xl border border-slate-200/80 dark:border-slate-800 bg-white dark:bg-[#111726] shadow-sm">
            {/* Header */}
            <div className="border-b border-slate-100 dark:border-slate-800/80 pb-3 flex items-center justify-between">
              <h3 className="text-[17px] font-bold tracking-tight text-slate-900 dark:text-white">
                Application Funnel
              </h3>
              <div className="text-[12.5px] font-medium text-slate-700 dark:text-slate-400 flex items-center gap-1.5">
                {totalApplications > 0 ? (
                  <span>{overallYield}% overall conversion</span>
                ) : (
                  <span>0 applications</span>
                )}
              </div>
            </div>

            {/* 4 Stage Cards Horizontal Stepper */}
            <div className="flex flex-col sm:flex-row items-center justify-between gap-2.5 sm:gap-3 pt-5">
              {funnel.map((step, idx) => {
                const visual = STAGE_VISUALS[step.stage] || STAGE_VISUALS.Applied;
                const Icon = visual.icon;
                const isLast = idx === funnel.length - 1;
                const conversionText = getConversionLabel(idx, step);

                return (
                  <React.Fragment key={step.stage}>
                    <div
                      className={`flex-1 w-full sm:w-auto min-h-[175px] rounded-2xl border ${visual.border} ${visual.cardBg} p-4 sm:py-5 sm:px-4 flex flex-col items-center justify-between text-center transition-all duration-200 hover:-translate-y-0.5 hover:shadow-sm`}
                    >
                      <div className="flex flex-col items-center">
                        <div
                          className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-xl ${visual.bg} ${visual.color} ${visual.ring} shadow-xs mb-2.5`}
                        >
                          <Icon className="h-5 w-5" />
                        </div>

                        <span className="text-[16px] font-semibold text-slate-800 dark:text-slate-200 leading-tight">
                          {step.stage}
                        </span>

                        <span className="text-[28px] font-bold text-slate-900 dark:text-white leading-tight mt-1">
                          {step.count}
                        </span>
                      </div>

                      <div className="mt-3">
                        <span
                          className={`inline-flex items-center px-2.5 py-0.5 rounded-md text-[12.5px] font-semibold ${visual.badgeStyle}`}
                        >
                          {conversionText}
                        </span>
                      </div>
                    </div>

                    {!isLast && (
                      <div className="hidden sm:flex items-center text-slate-300 dark:text-slate-600 px-0.5 shrink-0">
                        <ChevronRight className="h-5 w-5" strokeWidth={2.2} />
                      </div>
                    )}
                  </React.Fragment>
                );
              })}
            </div>

            {totalApplications === 0 && (
              <div className="mt-5 pt-4 border-t border-slate-100 dark:border-slate-800/80 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-slate-500 dark:text-slate-400">
                <p>
                  No applications tracked yet. Start applying from the Job Feed to track submission velocity and interview conversion.
                </p>
                <Link
                  to="/jobs?tier=Tier+1"
                  className="inline-flex items-center gap-1 font-semibold text-indigo-600 dark:text-indigo-400 hover:underline shrink-0"
                >
                  <span>Explore High-Match Jobs</span>
                  <ChevronRight className="h-3.5 w-3.5" />
                </Link>
              </div>
            )}
          </div>
        );
      })()}

    </div>
  );
};

export default ApplicationAnalyticsSection;
