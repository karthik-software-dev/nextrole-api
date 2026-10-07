import React from 'react';
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';

interface SourceData {
  source: string;
  count: number;
  color: string;
  percentage: number;
}

const COLOR_MAP: Record<string, string> = {
  Indeed: '#10B981',
  Naukri: '#8B5CF6',
  LinkedIn: '#3B82F6',
  Cutshort: '#6366F1',
  Hirist: '#0EA5E9',
  Wellfound: '#F97316',
  Shine: '#EAB308',
  TimesJobs: '#14B8A6',
  Internshala: '#06B6D4',
  Apna: '#22C55E',
  Freshersworld: '#A855F7',
  'Company Careers': '#38BDF8',
  Greenhouse: '#059669',
  Lever: '#0284C7',
  Workday: '#F59E0B',
  Ashby: '#EC4899',
  SmartRecruiters: '#4F46E5',
  BambooHR: '#10B981',
  Personio: '#3B82F6',
  Recruitee: '#D946EF',
  Workable: '#2563EB',
  Teamtailor: '#F43F5E',
  'Breezy HR': '#06B6D4',
  Other: '#94A3B8',
};

const PALETTE = ['#3B82F6', '#10B981', '#8B5CF6', '#F97316', '#38BDF8', '#EC4899', '#94A3B8'];

interface JobsBySourceChartProps {
  data?: SourceData[];
  sources?: Array<{ name: string; count: number }>;
}

export const JobsBySourceChart: React.FC<JobsBySourceChartProps> = ({ data, sources }) => {
  const chartData: SourceData[] = React.useMemo(() => {
    if (data) return data;
    if (sources && sources.length > 0) {
      const total = sources.reduce((acc, s) => acc + s.count, 0);
      const sorted = [...sources].sort((a, b) => b.count - a.count);
      return sorted.map((s, idx) => ({
        source: s.name,
        count: s.count,
        color: COLOR_MAP[s.name] || PALETTE[idx % PALETTE.length],
        percentage: total > 0 ? Math.round((s.count / total) * 100) : 0,
      }));
    }
    return [];
  }, [data, sources]);

  const total = chartData.reduce((acc, d) => acc + d.count, 0);

  return (
    <div className="relative flex min-h-[380px] sm:min-h-0 sm:h-[315px] flex-col overflow-hidden rounded-2xl border border-slate-200/80 bg-white p-4 sm:p-5 shadow-sm transition-[transform,box-shadow,border-color] duration-180 ease-out hover:-translate-y-0.5 hover:shadow-md dark:border-slate-800 dark:bg-[#111726]">
      {/* Header */}
      <div className="flex items-start justify-between border-b border-slate-100 pb-3 dark:border-slate-800">
        <h3 className="text-[17px] font-bold tracking-tight text-slate-900 dark:text-white">
          Jobs by Source
        </h3>
        <span className="text-[12.5px] font-medium text-slate-700 dark:text-slate-400">
          {total} total tracked jobs
        </span>
      </div>

      {/* Donut & Legend Container */}
      <div className="flex flex-1 flex-col sm:flex-row items-center gap-4 pt-3">
        {chartData.length === 0 ? (
          <div className="flex h-full w-full items-center justify-center text-xs text-slate-400">
            No source breakdown available.
          </div>
        ) : (
          <>
            {/* Donut Chart */}
            <div className="relative shrink-0 w-[155px] h-[155px] sm:w-[185px] sm:h-[185px] mx-auto sm:mx-0">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Tooltip
                    content={({ active, payload }) => {
                      if (active && payload && payload.length) {
                        const d = payload[0].payload as SourceData;
                        return (
                          <div className="rounded-lg bg-slate-900 px-3 py-2 text-xs text-white shadow-lg">
                            <p className="font-bold text-white">{d.source}</p>
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
                    data={chartData}
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
                    {chartData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                </PieChart>
              </ResponsiveContainer>

              {/* Center Total */}
              <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                <span className="text-[22px] sm:text-[26px] font-black tracking-tight text-slate-900 dark:text-white leading-none">
                  {total}
                </span>
                <span className="text-[10px] sm:text-[11px] font-semibold text-slate-700 dark:text-slate-500 mt-1 uppercase tracking-wider">
                  Total Jobs
                </span>
              </div>
            </div>

            {/* Legend: 2-column grid on mobile, vertical scrolling list on desktop */}
            <div className="w-full sm:flex-1 grid grid-cols-2 sm:flex sm:flex-col min-w-0 select-none overflow-y-auto max-h-[160px] sm:max-h-[188px] gap-x-3 gap-y-1 sm:gap-0 sm:space-y-1 sm:pr-2 my-auto">
              {chartData.map((item) => (
                <div key={item.source} className="flex h-[26px] sm:h-[28px] shrink-0 items-center justify-between gap-1.5">
                  <div className="flex items-center gap-1.5 sm:gap-2 min-w-0">
                    <span className="h-2 w-2 sm:h-2.5 sm:w-2.5 rounded-full shrink-0" style={{ backgroundColor: item.color }} />
                    <span className="text-[12px] sm:text-[13.5px] font-medium text-slate-800 dark:text-slate-200 truncate">
                      {item.source}
                    </span>
                  </div>
                  <div className="flex items-center gap-1 sm:gap-1.5 shrink-0">
                    <span className="text-[12px] sm:text-[13.5px] font-bold text-slate-800 dark:text-slate-100 tabular-nums">
                      {item.count}
                    </span>
                    <span className="text-[11px] sm:text-[12.5px] font-medium text-slate-600 dark:text-slate-400 tabular-nums">
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
  );
};

export default JobsBySourceChart;

