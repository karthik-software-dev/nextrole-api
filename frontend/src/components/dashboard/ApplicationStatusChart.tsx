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
import type { DashboardSummary } from '../../types';

interface PipelineItem {
  name: string;
  count: number;
  color: string;
  percentage: number;
}

const STAGE_CONFIG: Array<{ name: string; key: keyof DashboardSummary['application_breakdown']; color: string }> = [
  { name: 'Applied', key: 'applied', color: '#3B82F6' },
  { name: 'Under Review', key: 'under_review', color: '#8B5CF6' },
  { name: 'Interview', key: 'interviewing', color: '#10B981' },
  { name: 'Rejected', key: 'rejected', color: '#EF4444' },
  { name: 'Offer', key: 'offered', color: '#F59E0B' },
];

interface ApplicationStatusChartProps {
  data?: PipelineItem[];
  breakdown?: DashboardSummary['application_breakdown'];
}

export const ApplicationStatusChart: React.FC<ApplicationStatusChartProps> = ({ data, breakdown }) => {
  const chartData: PipelineItem[] = React.useMemo(() => {
    if (data) return data;
    const stages = STAGE_CONFIG.map((stage) => {
      const val = breakdown ? breakdown[stage.key] : 0;
      return {
        name: stage.name,
        count: val,
        color: stage.color,
        percentage: 0,
      };
    });

    const total = stages.reduce((acc, s) => acc + s.count, 0);
    return stages.map((s) => ({
      ...s,
      percentage: total > 0 ? Math.round((s.count / total) * 100) : 0,
    }));
  }, [data, breakdown]);

  const total = chartData.reduce((acc, item) => acc + item.count, 0);

  return (
    <div className="relative flex h-[315px] flex-col overflow-hidden rounded-2xl border border-slate-200/80 bg-white p-5 shadow-sm transition-[transform,box-shadow,border-color] duration-180 ease-out hover:-translate-y-0.5 hover:shadow-md dark:border-slate-800 dark:bg-[#111726]">
      {/* Header */}
      <div className="flex items-start justify-between border-b border-slate-100 pb-3 dark:border-slate-800">
        <h3 className="text-[17px] font-bold tracking-tight text-slate-900 dark:text-white">
          Application Pipeline
        </h3>
        <span className="text-[12.5px] font-medium text-slate-700 dark:text-slate-400">
          {total} total applications
        </span>
      </div>

      {/* Chart */}
      <div className="w-full flex-1 pt-3">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} margin={{ top: 20, right: 8, left: -24, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E2E8F0" opacity={0.4} />
            <XAxis
              dataKey="name"
              tickLine={false}
              axisLine={false}
              tick={{ fontSize: 12.3, fill: '#334155', fontWeight: 600, fontFamily: 'Inter, sans-serif' }}
              interval={0}
            />
            <YAxis
              tickLine={false}
              axisLine={false}
              tick={{ fontSize: 12.3, fill: '#334155', fontWeight: 600, fontFamily: 'Inter, sans-serif' }}
              allowDecimals={false}
            />
            <Tooltip
              cursor={{ fill: 'rgba(148,163,184,0.08)' }}
              content={({ active, payload }) => {
                if (active && payload && payload.length) {
                  const d = payload[0].payload as PipelineItem;
                  return (
                    <div className="rounded-lg bg-slate-900 px-3 py-2 text-xs text-white shadow-lg">
                      <p className="font-bold text-white">{d.name}</p>
                      <p className="mt-0.5 font-medium text-slate-300">
                        {d.count} {d.count === 1 ? 'application' : 'applications'} · {d.percentage}%
                      </p>
                    </div>
                  );
                }
                return null;
              }}
            />
            <Bar dataKey="count" radius={[6, 6, 0, 0]} maxBarSize={38} animationDuration={350} animationEasing="ease-out">
              {chartData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} />
              ))}
              <LabelList
                dataKey="count"
                position="top"
                style={{ fontSize: 12, fontWeight: 700, fill: '#1E293B', fontFamily: 'Inter, sans-serif' }}
              />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

export default ApplicationStatusChart;

