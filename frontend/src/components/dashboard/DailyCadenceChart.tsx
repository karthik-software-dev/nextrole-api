import React from 'react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  LabelList,
} from 'recharts';
import type { DailyCadenceRun, PipelineRunInfo } from '../../types';

interface DailyCadenceChartProps {
  data?: DailyCadenceRun[];
  pipeline?: PipelineRunInfo | null;
}

export const DailyCadenceChart: React.FC<DailyCadenceChartProps> = ({ data }) => {
  const cadenceData = data && data.length > 0 ? data : [
    { run_number: 1, time_slot: '09:00 AM', label: 'Morning Market Sync', status: 'completed' as const, jobs_collected: 8, cumulative_jobs: 8, runner: 'GitHub Actions Runner' },
    { run_number: 2, time_slot: '12:00 PM', label: 'Mid-day Ingestion', status: 'completed' as const, jobs_collected: 14, cumulative_jobs: 22, runner: 'GitHub Actions Runner' },
    { run_number: 3, time_slot: '03:00 PM', label: 'Afternoon Crawl', status: 'completed' as const, jobs_collected: 28, cumulative_jobs: 50, runner: 'GitHub Actions Runner' },
    { run_number: 4, time_slot: '06:00 PM', label: 'Evening Sync', status: 'completed' as const, jobs_collected: 75, cumulative_jobs: 125, runner: 'GitHub Actions Runner' },
    { run_number: 5, time_slot: '09:00 PM', label: 'Night Roundup', status: 'completed' as const, jobs_collected: 61, cumulative_jobs: 186, runner: 'GitHub Actions Runner' },
  ];

  const totalCollectedToday = cadenceData.reduce((acc, r) => acc + (r.jobs_collected || 0), 0);

  // Helper to determine the next scheduled run date & time
  const nextRunInfo = React.useMemo(() => {
    const now = new Date();
    const scheduledRun = cadenceData.find((r) => r.status === 'scheduled');

    if (scheduledRun) {
      const todayStr = now.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
      return `${todayStr} at ${scheduledRun.time_slot}`;
    }

    // If all runs today are completed or no scheduled runs remain, next is tomorrow 09:00 AM
    const tomorrow = new Date(now);
    tomorrow.setDate(tomorrow.getDate() + 1);
    const tomorrowStr = tomorrow.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
    return `${tomorrowStr} at 09:00 AM`;
  }, [cadenceData]);

  // Calculate dynamic upper bound for Y-axis with headroom for numeric labels
  const maxCollected = Math.max(...cadenceData.map((r) => r.jobs_collected || 0), 0);
  const yDomainMax = maxCollected > 0 ? Math.ceil((maxCollected * 1.25) / 10) * 10 : 10;

  // Custom data point numeric label renderer
  const renderPointLabel = (props: any) => {
    const { x, y, value } = props;
    if (value === undefined || value === null) return null;
    return (
      <text
        x={x}
        y={y - 10}
        textAnchor="middle"
        className="font-semibold text-[11.5px] fill-slate-800 dark:fill-slate-100"
      >
        {value}
      </text>
    );
  };

  return (
    <div className="relative flex h-[315px] flex-col overflow-hidden rounded-2xl border border-slate-200/80 bg-white p-5 shadow-sm transition-[transform,box-shadow,border-color] duration-180 ease-out hover:-translate-y-0.5 hover:shadow-md dark:border-slate-800 dark:bg-[#111726]">
      {/* Header */}
      <div className="flex items-start justify-between border-b border-slate-100 pb-3 dark:border-slate-800">
        <h3 className="text-[17px] font-bold tracking-tight text-slate-900 dark:text-white">
          5-Run Daily Cadence
        </h3>

        <span className="text-[12.5px] font-medium text-slate-700 dark:text-slate-400">
          {totalCollectedToday} jobs collected today
        </span>
      </div>

      {/* Chart */}
      <div className="w-full flex-1 pt-3">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={cadenceData} margin={{ top: 18, right: 18, left: -20, bottom: 0 }}>
            <defs>
              <linearGradient id="cadencePerRunGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#6366F1" stopOpacity={0.28} />
                <stop offset="95%" stopColor="#6366F1" stopOpacity={0.0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E2E8F0" opacity={0.45} />
            <XAxis
              dataKey="time_slot"
              tickLine={false}
              axisLine={false}
              tick={{ fontSize: 11.5, fill: '#64748B', fontWeight: 500, fontFamily: 'Inter, sans-serif' }}
              dy={6}
            />
            <YAxis
              tickLine={false}
              axisLine={false}
              tick={{ fontSize: 11.5, fill: '#64748B', fontWeight: 500, fontFamily: 'Inter, sans-serif' }}
              allowDecimals={false}
              domain={[0, yDomainMax]}
            />
            <Tooltip
              content={({ active, payload }) => {
                if (active && payload && payload.length) {
                  const item = payload[0].payload as DailyCadenceRun;
                  return (
                    <div className="rounded-xl border border-slate-200/80 bg-white/95 dark:border-slate-800 dark:bg-slate-900/95 backdrop-blur-md px-3.5 py-2.5 text-xs shadow-xl min-w-[160px]">
                      <div className="flex items-center justify-between gap-3 pb-1 border-b border-slate-100 dark:border-slate-800">
                        <span className="font-bold text-slate-800 dark:text-slate-100">
                          {item.time_slot}
                        </span>
                        <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded capitalize ${item.status === 'active' ? 'bg-indigo-500/15 text-indigo-600 dark:text-indigo-400' :
                            item.status === 'completed' ? 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400' :
                              'bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400'
                          }`}>
                          {item.status}
                        </span>
                      </div>
                      <p className="mt-1.5 text-[13px] font-bold text-indigo-600 dark:text-indigo-400">
                        {item.jobs_collected} {item.jobs_collected === 1 ? 'job discovered' : 'jobs discovered'}
                      </p>
                      <p className="mt-0.5 text-[11px] text-slate-500 dark:text-slate-400">
                        Batch #{item.run_number} &bull; {item.label}
                      </p>
                    </div>
                  );
                }
                return null;
              }}
            />
            <Area
              type="monotone"
              dataKey="jobs_collected"
              stroke="#6366F1"
              strokeWidth={2}
              fillOpacity={1}
              fill="url(#cadencePerRunGradient)"
              dot={{ r: 4, fill: '#6366F1', stroke: '#FFFFFF', strokeWidth: 1.5 }}
              activeDot={{ r: 6, fill: '#4F46E5', stroke: '#FFFFFF', strokeWidth: 2 }}
              animationDuration={350}
              animationEasing="ease-out"
            >
              <LabelList content={renderPointLabel} />
            </Area>
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Footer Meta */}
      <div className="flex items-center justify-end pt-2.5">
        <span className="text-[12px] font-medium text-slate-700 dark:text-slate-300">
          Next run: {nextRunInfo}
        </span>
      </div>
    </div>
  );
};

export default DailyCadenceChart;
