import React from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
  LabelList,
} from 'recharts';

interface SourceData {
  source: string;
  count: number;
  color: string;
}

const DEFAULT_DATA: SourceData[] = [
  { source: 'LinkedIn', count: 24, color: '#3B82F6' },
  { source: 'Naukri', count: 18, color: '#8B5CF6' },
  { source: 'Indeed', count: 12, color: '#10B981' },
  { source: 'Wellfound', count: 8, color: '#F97316' },
  { source: 'Company Sites', count: 6, color: '#38BDF8' },
];

const COLOR_MAP: Record<string, string> = {
  LinkedIn: '#3B82F6',
  Naukri: '#8B5CF6',
  Indeed: '#10B981',
  Wellfound: '#F97316',
  'Company Sites': '#38BDF8',
};

interface JobsBySourceChartProps {
  data?: SourceData[];
  sources?: Array<{ name: string; count: number }>;
}

export const JobsBySourceChart: React.FC<JobsBySourceChartProps> = ({ data, sources }) => {
  const chartData: SourceData[] = React.useMemo(() => {
    let result: SourceData[];
    if (data) {
      result = data;
    } else if (sources && sources.length > 0) {
      result = sources.map((s) => ({
        source: s.name,
        count: s.count,
        color: COLOR_MAP[s.name] || '#6366F1',
      }));
    } else {
      result = DEFAULT_DATA;
    }
    // Sort bars highest → lowest
    return [...result].sort((a, b) => b.count - a.count);
  }, [data, sources]);

  const total = chartData.reduce((acc, d) => acc + d.count, 0);

  return (
    <div className="relative flex h-[315px] flex-col overflow-hidden rounded-2xl border border-slate-200/80 bg-white p-5 shadow-sm transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md dark:border-slate-800 dark:bg-[#111726]">
      {/* Header */}
      <div className="flex items-start justify-between border-b border-slate-100 pb-3 dark:border-slate-800">
        <div>
          <h3 className="text-[17px] font-bold tracking-tight text-slate-900 dark:text-white">
            Jobs by Source
          </h3>
          <p className="mt-1 text-[12px] font-medium text-slate-500 dark:text-slate-400">
            {total} total jobs tracked
          </p>
        </div>
      </div>

      {/* Chart */}
      <div className="w-full flex-1 pt-3">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} margin={{ top: 20, right: 8, left: -22, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E2E8F0" opacity={0.5} />
            <XAxis
              dataKey="source"
              tickLine={false}
              axisLine={false}
              tick={{ fontSize: 11, fill: '#475569', fontWeight: 600, fontFamily: 'Inter, sans-serif' }}
              interval={0}
            />
            <YAxis
              tickLine={false}
              axisLine={false}
              tick={{ fontSize: 11, fill: '#64748B', fontWeight: 500, fontFamily: 'Inter, sans-serif' }}
              allowDecimals={false}
            />
            <Tooltip
              cursor={{ fill: 'rgba(148,163,184,0.08)' }}
              content={({ active, payload }) => {
                if (active && payload && payload.length) {
                  const d = payload[0].payload as SourceData;
                  return (
                    <div className="bg-slate-900 text-white text-xs px-3 py-2 rounded-lg shadow-lg">
                      <p className="font-bold text-[13px] text-white">{d.source}</p>
                      <p className="text-slate-300 mt-0.5 font-medium">{d.count} jobs · {Math.round((d.count / total) * 100)}%</p>
                    </div>
                  );
                }
                return null;
              }}
            />
            <Bar dataKey="count" radius={[5, 5, 0, 0]} maxBarSize={36}>
              {chartData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} />
              ))}
              <LabelList
                dataKey="count"
                position="top"
                style={{ fontSize: 12, fontWeight: 800, fill: '#334155', fontFamily: 'Inter, sans-serif' }}
              />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

export default JobsBySourceChart;
