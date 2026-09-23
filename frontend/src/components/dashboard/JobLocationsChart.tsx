import React from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';
import type { DashboardSummary } from '../../types';

interface LocationItem {
  name: string;
  count: number;
  color: string;
  percentage: number;
}

const DEFAULT_DATA: LocationItem[] = [
  { name: 'Bangalore', count: 45, color: '#3B82F6', percentage: 60 },
  { name: 'Chennai', count: 12, color: '#10B981', percentage: 16 },
  { name: 'Remote', count: 10, color: '#F59E0B', percentage: 13 },
  { name: 'Others', count: 8, color: '#8B5CF6', percentage: 11 },
];

interface JobLocationsChartProps {
  data?: LocationItem[];
  locations?: DashboardSummary['location_breakdown'];
}

export const JobLocationsChart: React.FC<JobLocationsChartProps> = ({ data, locations }) => {
  const chartData: LocationItem[] = React.useMemo(() => {
    if (data) return data;
    if (locations) {
      const items = [
        { name: 'Bangalore', count: locations.bangalore, color: '#3B82F6' },
        { name: 'Chennai', count: locations.chennai, color: '#10B981' },
        { name: 'Remote', count: locations.remote || 0, color: '#F59E0B' },
        { name: 'Others', count: locations.other, color: '#8B5CF6' },
      ];
      const sum = items.reduce((acc, it) => acc + it.count, 0);
      if (sum > 0) {
        // Filter out zero-count entries
        const nonZero = items.filter((it) => it.count > 0);
        return nonZero.map((it) => ({
          ...it,
          percentage: Math.round((it.count / sum) * 100),
        }));
      }
    }
    return DEFAULT_DATA;
  }, [data, locations]);

  const total = chartData.reduce((acc, it) => acc + it.count, 0);

  return (
    <div className="relative flex h-[315px] flex-col overflow-hidden rounded-2xl border border-slate-200/80 bg-white p-5 shadow-sm transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md dark:border-slate-800 dark:bg-[#111726]">
      {/* Header */}
      <div className="flex items-start justify-between border-b border-slate-100 pb-3 dark:border-slate-800">
        <div>
          <h3 className="text-[17px] font-bold tracking-tight text-slate-900 dark:text-white">
            Top Job Locations
          </h3>
          <p className="mt-1 text-[12px] font-medium text-slate-500 dark:text-slate-400">
            {total} jobs across {chartData.length} regions
          </p>
        </div>
      </div>

      {/* Chart and Legend */}
      <div className="flex flex-1 items-center gap-3 pt-3">
        {/* Pie Donut */}
        <div className="relative shrink-0 w-[140px] h-[140px]">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Tooltip
                content={({ active, payload }) => {
                  if (active && payload && payload.length) {
                    const d = payload[0].payload as LocationItem;
                    return (
                      <div className="bg-slate-900 text-white text-xs px-3 py-2 rounded-lg shadow-lg">
                        <p className="font-bold text-[13px]">{d.name}</p>
                        <p className="text-slate-300 mt-0.5 font-medium">{d.count} jobs · {d.percentage}%</p>
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
                innerRadius={40}
                outerRadius={65}
                dataKey="count"
                strokeWidth={2}
                stroke="#FFFFFF"
                paddingAngle={2}
              >
                {chartData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
            </PieChart>
          </ResponsiveContainer>

          {/* Center label */}
          <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
            <span className="text-[26px] font-black tracking-tight text-slate-900 dark:text-white leading-none" style={{ fontFamily: 'Inter, sans-serif' }}>
              {total}
            </span>
            <span className="text-[10px] font-bold text-slate-500 dark:text-slate-400 mt-0.5 uppercase tracking-widest">
              Total
            </span>
          </div>
        </div>

        {/* Legend */}
        <div className="flex-1 flex flex-col justify-center space-y-2.5 min-w-0 select-none">
          {chartData.map((item) => (
            <div key={item.name} className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-2 min-w-0">
                <span className="h-3 w-3 rounded-full shrink-0" style={{ backgroundColor: item.color }} />
                <span className="text-[12px] font-semibold text-slate-700 dark:text-slate-200 truncate">
                  {item.name}
                </span>
              </div>
              <div className="flex items-center gap-1.5 shrink-0">
                <span className="text-[13px] font-extrabold text-slate-900 dark:text-white tabular-nums">
                  {item.count}
                </span>
                <span className="text-[11px] font-bold text-slate-400 dark:text-slate-500 tabular-nums w-[32px] text-right">
                  {item.percentage}%
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default JobLocationsChart;
