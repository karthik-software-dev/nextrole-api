import React from 'react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { Clock, Cpu, CheckCircle2, Loader2, ArrowUpRight } from 'lucide-react';
import type { DailyCadenceRun } from '../../types';

interface DailyCadenceChartProps {
  data?: DailyCadenceRun[];
}

export const DailyCadenceChart: React.FC<DailyCadenceChartProps> = ({ data }) => {
  const cadenceData = data && data.length > 0 ? data : [
    { run_number: 1, time_slot: '09:00 AM', label: 'Morning Sync', status: 'completed' as const, jobs_collected: 1, cumulative_jobs: 1, runner: 'GitLab 4GB Runner' },
    { run_number: 2, time_slot: '12:00 PM', label: 'Mid-day Ingestion', status: 'completed' as const, jobs_collected: 0, cumulative_jobs: 1, runner: 'GitLab 4GB Runner' },
    { run_number: 3, time_slot: '03:00 PM', label: 'Afternoon Crawl', status: 'completed' as const, jobs_collected: 0, cumulative_jobs: 1, runner: 'GitLab 4GB Runner' },
    { run_number: 4, time_slot: '06:00 PM', label: 'Evening Sync', status: 'completed' as const, jobs_collected: 0, cumulative_jobs: 1, runner: 'GitLab 4GB Runner' },
    { run_number: 5, time_slot: '09:00 PM', label: 'Night Roundup', status: 'active' as const, jobs_collected: 65, cumulative_jobs: 66, runner: 'GitLab 4GB Runner' },
  ];

  const totalCollectedToday = cadenceData.reduce((acc, r) => acc + r.jobs_collected, 0);
  const activeOrNextRun = cadenceData.find((r) => r.status === 'active') || cadenceData.find((r) => r.status === 'scheduled');

  return (
    <div className="relative flex min-h-[350px] flex-col overflow-hidden rounded-2xl border border-slate-200/80 bg-white p-5 shadow-sm transition-[transform,box-shadow,border-color] duration-180 ease-out hover:-translate-y-0.5 hover:shadow-md dark:border-slate-800 dark:bg-[#111726]">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2.5 border-b border-slate-100 pb-3.5 dark:border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-[17px] font-bold tracking-tight text-slate-900 dark:text-white">
              5-Run Daily Cadence
            </h3>
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-violet-500/10 text-violet-700 dark:text-violet-400 border border-violet-500/20">
              <Cpu className="h-3 w-3" />
              GitLab 4GB Runner
            </span>
          </div>
          <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
            Automated scheduled batch ingestion across 30+ job sources
          </p>
        </div>

        <div className="flex items-center gap-2">
          {activeOrNextRun?.status === 'active' ? (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-xl text-xs font-semibold bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-400 border border-emerald-200/80 dark:border-emerald-800/80">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
                <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
              </span>
              <span>Batch #{activeOrNextRun.run_number} Active</span>
            </span>
          ) : (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-xl text-xs font-medium bg-slate-100 dark:bg-slate-800/60 text-slate-600 dark:text-slate-300 border border-slate-200/60 dark:border-slate-700/60">
              <Clock className="h-3.5 w-3.5 text-slate-400" />
              <span>Next: {activeOrNextRun?.time_slot || '09:00 AM Tomorrow'}</span>
            </span>
          )}
        </div>
      </div>

      {/* Cadence Pills Strip */}
      <div className="mt-3.5 grid grid-cols-5 gap-1.5 sm:gap-2">
        {cadenceData.map((slot) => {
          const isDone = slot.status === 'completed';
          const isActive = slot.status === 'active';
          return (
            <div
              key={slot.run_number}
              className={`flex flex-col items-center justify-center p-2 rounded-xl border text-center transition-all ${
                isActive
                  ? 'border-indigo-500/40 bg-indigo-500/10 dark:bg-indigo-950/40 shadow-xs'
                  : isDone
                  ? 'border-slate-200/70 bg-slate-50/70 dark:border-slate-800/80 dark:bg-slate-900/40'
                  : 'border-dashed border-slate-200 dark:border-slate-800 bg-transparent opacity-60'
              }`}
            >
              <div className="flex items-center gap-1 text-[10.5px] font-bold text-slate-500 dark:text-slate-400">
                {isActive ? (
                  <Loader2 className="h-2.5 w-2.5 animate-spin text-indigo-500" />
                ) : isDone ? (
                  <CheckCircle2 className="h-2.5 w-2.5 text-emerald-500" />
                ) : (
                  <Clock className="h-2.5 w-2.5 text-slate-400" />
                )}
                <span>Run #{slot.run_number}</span>
              </div>
              <div className="mt-0.5 text-[11px] font-semibold text-slate-800 dark:text-slate-200 truncate w-full">
                {slot.time_slot}
              </div>
              <div className="mt-1 text-[11.5px] font-extrabold text-indigo-600 dark:text-indigo-400">
                {slot.jobs_collected > 0 ? `+${slot.jobs_collected}` : slot.status === 'scheduled' ? '—' : '0'}
              </div>
            </div>
          );
        })}
      </div>

      {/* Chart */}
      <div className="w-full flex-1 pt-3 min-h-[170px]">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={cadenceData} margin={{ top: 12, right: 12, left: -24, bottom: 0 }}>
            <defs>
              <linearGradient id="cadenceGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#6366F1" stopOpacity={0.35} />
                <stop offset="95%" stopColor="#6366F1" stopOpacity={0.0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E2E8F0" opacity={0.4} />
            <XAxis
              dataKey="time_slot"
              tickLine={false}
              axisLine={false}
              tick={{ fontSize: 11.5, fill: '#64748B', fontWeight: 600, fontFamily: 'Inter, sans-serif' }}
            />
            <YAxis
              tickLine={false}
              axisLine={false}
              tick={{ fontSize: 11.5, fill: '#64748B', fontWeight: 600, fontFamily: 'Inter, sans-serif' }}
              allowDecimals={false}
            />
            <Tooltip
              content={({ active, payload }) => {
                if (active && payload && payload.length) {
                  const item = payload[0].payload as DailyCadenceRun;
                  return (
                    <div className="rounded-xl border border-slate-700/60 bg-slate-900/95 backdrop-blur-md p-3 text-xs text-white shadow-xl min-w-[190px]">
                      <div className="flex items-center justify-between border-b border-slate-800 pb-1.5 mb-1.5">
                        <span className="font-bold text-slate-200">Batch #{item.run_number} ({item.time_slot})</span>
                        <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded capitalize ${
                          item.status === 'active' ? 'bg-indigo-500/20 text-indigo-300' :
                          item.status === 'completed' ? 'bg-emerald-500/20 text-emerald-300' :
                          'bg-slate-700 text-slate-300'
                        }`}>
                          {item.status}
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-400">{item.label}</p>
                      <div className="mt-2 flex items-center justify-between text-[12px]">
                        <span className="text-slate-400">Added this batch:</span>
                        <span className="font-bold text-emerald-400">+{item.jobs_collected} jobs</span>
                      </div>
                      <div className="mt-1 flex items-center justify-between text-[12px]">
                        <span className="text-slate-400">Cumulative today:</span>
                        <span className="font-bold text-indigo-400">{item.cumulative_jobs} jobs</span>
                      </div>
                    </div>
                  );
                }
                return null;
              }}
            />
            <Area
              type="monotone"
              dataKey="cumulative_jobs"
              stroke="#6366F1"
              strokeWidth={2.5}
              fillOpacity={1}
              fill="url(#cadenceGradient)"
              dot={{ r: 4, fill: '#6366F1', strokeWidth: 1.5, stroke: '#FFFFFF' }}
              activeDot={{ r: 6, fill: '#4F46E5', strokeWidth: 2, stroke: '#FFFFFF' }}
              animationDuration={350}
              animationEasing="ease-out"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Footer Info Strip */}
      <div className="mt-3 pt-2.5 border-t border-slate-100 dark:border-slate-800/80 flex items-center justify-between text-xs text-slate-500 dark:text-slate-400">
        <span className="font-medium">
          <strong className="text-indigo-600 dark:text-indigo-400 font-bold">{totalCollectedToday}</strong> jobs ingested today across 5 runs
        </span>
        <span className="flex items-center gap-1 text-[11px] text-slate-400">
          <span>Continuous sync</span>
          <ArrowUpRight className="h-3 w-3" />
        </span>
      </div>
    </div>
  );
};

export default DailyCadenceChart;
