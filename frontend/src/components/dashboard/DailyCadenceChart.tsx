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
import { ExternalLink } from 'lucide-react';
import type { DailyCadenceRun, PipelineRunInfo } from '../../types';

interface DailyCadenceChartProps {
  data?: DailyCadenceRun[];
  pipeline?: PipelineRunInfo | null;
}

export const DailyCadenceChart: React.FC<DailyCadenceChartProps> = ({ data, pipeline }) => {
  const cadenceData = data && data.length > 0 ? data : [
    { run_number: 1, time_slot: '09:00 AM', label: 'Morning Sync', status: 'completed' as const, jobs_collected: 1, cumulative_jobs: 1, runner: 'GitLab 4GB Runner' },
    { run_number: 2, time_slot: '12:00 PM', label: 'Mid-day Ingestion', status: 'completed' as const, jobs_collected: 3, cumulative_jobs: 4, runner: 'GitLab 4GB Runner' },
    { run_number: 3, time_slot: '03:00 PM', label: 'Afternoon Crawl', status: 'completed' as const, jobs_collected: 10, cumulative_jobs: 14, runner: 'GitLab 4GB Runner' },
    { run_number: 4, time_slot: '06:00 PM', label: 'Evening Sync', status: 'completed' as const, jobs_collected: 62, cumulative_jobs: 76, runner: 'GitLab 4GB Runner' },
    { run_number: 5, time_slot: '09:00 PM', label: 'Night Roundup', status: 'completed' as const, jobs_collected: 110, cumulative_jobs: 186, runner: 'GitLab 4GB Runner' },
  ];

  const totalCollectedToday = cadenceData.reduce((acc, r) => acc + r.jobs_collected, 0);

  return (
    <div className="relative flex h-[315px] flex-col overflow-hidden rounded-2xl border border-slate-200/80 bg-white p-5 shadow-sm transition-[transform,box-shadow,border-color] duration-180 ease-out hover:-translate-y-0.5 hover:shadow-md dark:border-slate-800 dark:bg-[#111726]">
      {/* Header */}
      <div className="flex items-start justify-between border-b border-slate-100 pb-3 dark:border-slate-800">
        <div>
          <h3 className="text-[17px] font-bold tracking-tight text-slate-900 dark:text-white">
            5-Run Daily Cadence
          </h3>
        </div>

        <div className="flex items-center gap-2">
          {pipeline && (pipeline.status === 'running' || pipeline.status === 'active') ? (
            <a
              href={pipeline.pipeline_url || 'https://gitlab.com/karthik-software-dev/job-agent/-/pipelines'}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border border-emerald-500/20 hover:bg-emerald-500/20 transition-colors"
              title="View live running GitLab CI pipeline"
            >
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
                <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
              </span>
              <span>🦊 GitLab CI #{pipeline.pipeline_id || 'Running'}</span>
              <ExternalLink className="h-3 w-3" />
            </a>
          ) : pipeline?.pipeline_id ? (
            <a
              href={pipeline.pipeline_url || 'https://gitlab.com/karthik-software-dev/job-agent/-/pipelines'}
              target="_blank"
              rel="noopener noreferrer"
              className="group text-[12.5px] font-medium text-slate-600 hover:text-indigo-600 dark:text-slate-400 dark:hover:text-indigo-400 inline-flex items-center gap-1.5 transition-colors"
              title="View latest GitLab CI pipeline run"
            >
              <span>{totalCollectedToday} total ingested</span>
              <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[11px] font-semibold bg-slate-100 dark:bg-slate-800/80 text-slate-600 dark:text-slate-300 border border-slate-200/60 dark:border-slate-700/60 group-hover:border-indigo-300 dark:group-hover:border-indigo-700">
                <span>CI #{pipeline.pipeline_id}</span>
                <ExternalLink className="h-2.5 w-2.5 text-slate-400 group-hover:text-indigo-500" />
              </span>
            </a>
          ) : (
            <span className="text-[12.5px] font-medium text-slate-700 dark:text-slate-400">
              {totalCollectedToday} total ingested today
            </span>
          )}
        </div>
      </div>

      {/* Chart */}
      <div className="w-full flex-1 pt-3">
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
              tick={{ fontSize: 12.3, fill: '#334155', fontWeight: 600, fontFamily: 'Inter, sans-serif' }}
            />
            <YAxis
              tickLine={false}
              axisLine={false}
              tick={{ fontSize: 12.3, fill: '#334155', fontWeight: 600, fontFamily: 'Inter, sans-serif' }}
              allowDecimals={false}
            />
            <Tooltip
              content={({ active, payload }) => {
                if (active && payload && payload.length) {
                  const item = payload[0].payload as DailyCadenceRun;
                  return (
                    <div className="rounded-lg bg-slate-900 px-3 py-2 text-xs text-white shadow-lg">
                      <div className="flex items-center justify-between gap-3">
                        <span className="font-semibold text-slate-200">
                          Batch #{item.run_number} ({item.time_slot})
                        </span>
                        <span className={`text-[10px] font-semibold px-1.5 py-0.2 rounded capitalize ${
                          item.status === 'active' ? 'bg-indigo-500/20 text-indigo-300' :
                          item.status === 'completed' ? 'bg-emerald-500/20 text-emerald-300' :
                          'bg-slate-700 text-slate-300'
                        }`}>
                          {item.status}
                        </span>
                      </div>
                      <p className="mt-1 text-[13px] font-bold text-indigo-400">
                        +{item.jobs_collected} {item.jobs_collected === 1 ? 'job ingested' : 'jobs ingested'}
                      </p>
                      <p className="mt-0.5 text-[11px] text-slate-400">
                        {item.cumulative_jobs} cumulative jobs
                      </p>
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
              dot={{ r: 3.5, fill: '#6366F1', strokeWidth: 1, stroke: '#FFFFFF' }}
              activeDot={{ r: 5, fill: '#4F46E5', strokeWidth: 2, stroke: '#FFFFFF' }}
              animationDuration={350}
              animationEasing="ease-out"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

export default DailyCadenceChart;
