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

interface LocationItem {
  name: string;
  count: number;
  color: string;
  percentage: number;
}

const LOCATION_COLOR_MAP: Record<string, string> = {
  Bangalore: '#3B82F6',
  Remote: '#10B981',
  Chennai: '#8B5CF6',
  Hyderabad: '#F59E0B',
  Pune: '#EF4444',
  Others: '#94A3B8',
};

const PALETTE = ['#3B82F6', '#10B981', '#8B5CF6', '#F59E0B', '#EF4444', '#94A3B8'];

interface JobLocationsChartProps {
  data?: LocationItem[];
  locations?: DashboardSummary['location_breakdown'];
  locationsBreakdown?: DashboardSummary['locations_breakdown'];
}

export const JobLocationsChart: React.FC<JobLocationsChartProps> = ({
  data,
  locations,
  locationsBreakdown,
}) => {
  const chartData: LocationItem[] = React.useMemo(() => {
    if (data) return data;
    if (locationsBreakdown && locationsBreakdown.length > 0) {
      const nonZero = locationsBreakdown.filter((it) => it.count > 0);
      const sorted = [...nonZero].sort((a, b) => b.count - a.count);
      const sum = sorted.reduce((acc, it) => acc + it.count, 0);
      return sorted.map((it, idx) => ({
        name: it.name,
        count: it.count,
        color: LOCATION_COLOR_MAP[it.name] || PALETTE[idx % PALETTE.length],
        percentage: sum > 0 ? Math.round((it.count / sum) * 100) : 0,
      }));
    }
    if (locations) {
      const items = [
        { name: 'Bangalore', count: locations.bangalore, color: '#3B82F6' },
        { name: 'Remote', count: locations.remote || 0, color: '#10B981' },
        { name: 'Chennai', count: locations.chennai, color: '#8B5CF6' },
        { name: 'Others', count: locations.other, color: '#94A3B8' },
      ];
      const nonZero = items.filter((it) => it.count > 0);
      const sorted = [...nonZero].sort((a, b) => b.count - a.count);
      const sum = sorted.reduce((acc, it) => acc + it.count, 0);
      return sorted.map((it) => ({
        ...it,
        percentage: sum > 0 ? Math.round((it.count / sum) * 100) : 0,
      }));
    }
    return [];
  }, [data, locations, locationsBreakdown]);

  const total = chartData.reduce((acc, it) => acc + it.count, 0);

  return (
    <div className="relative flex h-[315px] flex-col overflow-hidden rounded-2xl border border-slate-200/80 bg-white p-5 shadow-sm transition-[transform,box-shadow,border-color] duration-180 ease-out hover:-translate-y-0.5 hover:shadow-md dark:border-slate-800 dark:bg-[#111726]">
      {/* Header */}
      <div className="flex items-start justify-between border-b border-slate-100 pb-3 dark:border-slate-800">
        <h3 className="text-[17px] font-bold tracking-tight text-slate-900 dark:text-white">
          Jobs by Location
        </h3>
        <span className="text-[12.5px] font-medium text-slate-700 dark:text-slate-400">
          {total} active jobs
        </span>
      </div>

      {/* Chart */}
      <div className="w-full flex-1 pt-3">
        {chartData.length === 0 ? (
          <div className="flex h-full items-center justify-center text-xs text-slate-400">
            No location breakdown available.
          </div>
        ) : (
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
                    const d = payload[0].payload as LocationItem;
                    return (
                      <div className="rounded-lg bg-slate-900 px-3 py-2 text-xs text-white shadow-lg">
                        <p className="font-bold text-white">{d.name}</p>
                        <p className="mt-0.5 font-medium text-slate-300">
                          {d.count} {d.count === 1 ? 'job' : 'jobs'} · {d.percentage}%
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
        )}
      </div>
    </div>
  );
};

export default JobLocationsChart;

