import React from 'react';
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
  Info,
} from 'lucide-react';
import type { ApplicationAnalytics } from '../../types';

interface ApplicationAnalyticsSectionProps {
  data?: ApplicationAnalytics;
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
    <div className="space-y-4">
      {/* Section Header */}
      <div>
        <div className="flex items-center gap-1.5">
          <h2 className="text-[17px] font-bold text-slate-900 dark:text-white tracking-tight">
            Application Analytics
          </h2>
          <span title="Track your application progress and outcomes">
            <Info className="h-3.5 w-3.5 text-slate-400 cursor-help" />
          </span>
        </div>
        <p className="mt-1 text-[13.5px] text-slate-800 dark:text-slate-300">
          Track your application progress and outcomes.
        </p>
      </div>

      {/* ROW 1: Applications Over Time (7 cols) + Status Donut (5 cols) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        {/* Card 1: Applications Over Time */}
        <div className="lg:col-span-7 p-5 rounded-2xl border border-slate-200/80 dark:border-slate-800 bg-white dark:bg-[#111726] shadow-sm flex flex-col justify-between h-[300px]">
          <div className="flex items-start justify-between border-b border-slate-100 pb-3 dark:border-slate-800">
            <h3 className="text-[17px] font-bold tracking-tight text-slate-900 dark:text-white">
              Applications Over Time
            </h3>
            <span className="text-[12.5px] font-medium text-slate-700 dark:text-slate-400">
              {totalOverTime} total in period
            </span>
          </div>

          <div className="flex-1 w-full mt-2">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={overTime} margin={{ top: 12, right: 12, left: -24, bottom: 0 }}>
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
                  tick={{ fontSize: 12.3, fill: '#334155', fontWeight: 600, fontFamily: 'Inter, sans-serif' }}
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
                  tick={{ fontSize: 12.3, fill: '#334155', fontWeight: 600, fontFamily: 'Inter, sans-serif' }}
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
          </div>
        </div>

        {/* Card 2: Application Status Donut */}
        <div className="lg:col-span-5 p-5 rounded-2xl border border-slate-200/80 dark:border-slate-800 bg-white dark:bg-[#111726] shadow-sm flex flex-col justify-between h-[300px]">
          <div className="flex items-start justify-between border-b border-slate-100 pb-3 dark:border-slate-800">
            <h3 className="text-[17px] font-bold tracking-tight text-slate-900 dark:text-white">
              Application Status
            </h3>
            <span className="text-[12.5px] font-medium text-slate-700 dark:text-slate-400">
              {totalApplications} total applications
            </span>
          </div>

          <div className="flex-1 flex items-center justify-between gap-3 mt-1">
            {/* Center Donut */}
            <div className="relative w-1/2 h-[190px] flex items-center justify-center">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={statusDist}
                    dataKey="count"
                    nameKey="status"
                    cx="50%"
                    cy="50%"
                    innerRadius={50}
                    outerRadius={75}
                    paddingAngle={3}
                    animationDuration={350}
                    animationEasing="ease-out"
                  >
                    {statusDist.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
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
                </PieChart>
              </ResponsiveContainer>

              {/* Total overlay in center */}
              <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                <span className="text-[24px] font-black tracking-tight text-slate-900 dark:text-white leading-none">
                  {totalApplications}
                </span>
                <span className="text-[11px] font-semibold text-slate-700 dark:text-slate-500 mt-1 uppercase tracking-wider">
                  Applications
                </span>
              </div>
            </div>

            {/* Right Legend */}
            <div className="flex-1 flex flex-col justify-center space-y-2.5 min-w-0 select-none pr-1">
              {statusDist.map((s) => (
                <div key={s.status} className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2 min-w-0">
                    <span
                      className="h-2.5 w-2.5 rounded-full shrink-0"
                      style={{ backgroundColor: s.color }}
                    />
                    <span className="text-[13.5px] font-medium text-slate-800 dark:text-slate-200 truncate">
                      {s.status}
                    </span>
                  </div>
                  <div className="flex items-center gap-1.5 shrink-0">
                    <span className="text-[13.5px] font-bold text-slate-800 dark:text-slate-100 tabular-nums">
                      {s.count}
                    </span>
                    <span className="text-[13px] font-medium text-slate-600 dark:text-slate-400 tabular-nums">
                      ({s.percentage}%)
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* ROW 2: FULL-WIDTH APPLICATION FUNNEL */}
      {(() => {
        const appliedCount = funnel[0]?.count || (totalApplications > 0 ? totalApplications : 1);
        const offerCount = funnel.find((f) => f.stage === 'Offer')?.count || 0;
        const overallYield =
          appliedCount > 0 ? Math.round((offerCount / appliedCount) * 1000) / 10 : 0.0;

        const getConversionLabel = (idx: number, step: (typeof funnel)[0]) => {
          if (idx === 0) return '100% Submissions';
          if (idx === 1) return `${step.conversion_rate}% from Applied`;
          if (idx === 2) return `${step.conversion_rate}% from Under Review`;
          if (idx === 3) return `${step.conversion_rate}% from Interview`;
          return `${step.conversion_rate}% conversion`;
        };

        return (
          <div className="p-5 sm:p-6 rounded-2xl border border-slate-200/80 dark:border-slate-800 bg-white dark:bg-[#111726] shadow-sm">
            {/* Header: Title on Left, Single Factual Summary on Right */}
            <div className="border-b border-slate-100 dark:border-slate-800/80 pb-3 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-1.5">
              <h3 className="text-[17px] font-bold tracking-tight text-slate-900 dark:text-white">
                Application Funnel
              </h3>
              <div className="text-[13px] text-slate-700 dark:text-slate-300 font-medium flex items-center gap-1.5 flex-wrap">
                <span>{offerCount} {offerCount === 1 ? 'offer' : 'offers'} from {appliedCount} applications ·</span>
                <span className="inline-flex items-center px-2 py-0.5 rounded-md text-[11.5px] font-bold bg-emerald-50 text-emerald-700 ring-1 ring-inset ring-emerald-600/20 dark:bg-emerald-950/60 dark:text-emerald-300">
                  {overallYield}% overall conversion
                </span>
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
                        {/* Squircle Glyph */}
                        <div
                          className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-xl ${visual.bg} ${visual.color} ${visual.ring} shadow-xs mb-2.5`}
                        >
                          <Icon className="h-5 w-5" />
                        </div>

                        {/* Stage Title */}
                        <span className="text-[16px] font-semibold text-slate-800 dark:text-slate-200 leading-tight">
                          {step.stage}
                        </span>

                        {/* Large Count */}
                        <span className="text-[28px] font-bold text-slate-900 dark:text-white leading-tight mt-1">
                          {step.count}
                        </span>
                      </div>

                      {/* Clean Conversion Subtext Badge */}
                      <div className="mt-3">
                        <span
                          className={`inline-flex items-center px-2.5 py-0.5 rounded-md text-[13px] font-semibold ${visual.badgeStyle}`}
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
          </div>
        );
      })()}
    </div>
  );
};

export default ApplicationAnalyticsSection;
