import React from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';
import type { DashboardSummary } from '../../types';

interface StatusItem {
  name: string;
  value: number;
  color: string;
  percentage: number;
}

const DEFAULT_DATA: StatusItem[] = [
  { name: 'Applied', value: 5, color: '#3B82F6', percentage: 42 },
  { name: 'Under Review', value: 3, color: '#8B5CF6', percentage: 25 },
  { name: 'Interviewing', value: 2, color: '#F59E0B', percentage: 17 },
  { name: 'Offered', value: 1, color: '#10B981', percentage: 8 },
  { name: 'Rejected', value: 1, color: '#F43F5E', percentage: 8 },
];

interface ApplicationStatusChartProps {
  data?: StatusItem[];
  breakdown?: DashboardSummary['application_breakdown'];
}

export const ApplicationStatusChart: React.FC<ApplicationStatusChartProps> = ({ data, breakdown }) => {
  const chartData: StatusItem[] = React.useMemo(() => {
    if (data) return data;
    if (breakdown) {
      const stages = [
        { name: 'Applied', value: breakdown.applied, color: '#3B82F6' },
        { name: 'Under Review', value: breakdown.under_review, color: '#8B5CF6' },
        { name: 'Interviewing', value: breakdown.interviewing, color: '#F59E0B' },
        { name: 'Offered', value: breakdown.offered, color: '#10B981' },
        { name: 'Rejected', value: breakdown.rejected, color: '#F43F5E' },
      ];
      const sum = stages.reduce((acc, s) => acc + s.value, 0);
      if (sum > 0) {
        return stages.map((s) => ({
          ...s,
          percentage: Math.round((s.value / sum) * 100),
        }));
      }
    }
    return DEFAULT_DATA;
  }, [data, breakdown]);

  const total = chartData.reduce((acc, item) => acc + item.value, 0);
  const activeCount = chartData
    .filter((d) => ['Applied', 'Under Review', 'Interviewing'].includes(d.name))
    .reduce((acc, d) => acc + d.value, 0);

  return (
    <div className="relative flex h-[315px] flex-col overflow-hidden rounded-2xl border border-slate-200/80 bg-white p-5 shadow-sm transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md dark:border-slate-800 dark:bg-[#111726]">
      {/* Header */}
      <div className="flex items-start justify-between border-b border-slate-100 pb-3 dark:border-slate-800">
        <div>
          <h3 className="text-[17px] font-bold tracking-tight text-slate-900 dark:text-white">
            Application Status
          </h3>
          <p className="mt-1 text-[12px] font-medium text-slate-500 dark:text-slate-400">
            {activeCount} active · {total} total
          </p>
        </div>
      </div>

      {/* Donut & Legend Container */}
      <div className="flex flex-1 items-center gap-3 pt-3">
        {/* Donut Chart */}
        <div className="relative shrink-0 w-[140px] h-[140px]">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Tooltip
                content={({ active, payload }) => {
                  if (active && payload && payload.length) {
                    const d = payload[0].payload as StatusItem;
                    return (
                      <div className="bg-slate-900 text-white text-xs px-3 py-2 rounded-lg shadow-lg">
                        <p className="font-bold text-[13px]">{d.name}</p>
                        <p className="text-slate-300 mt-0.5 font-medium">{d.value} applications · {d.percentage}%</p>
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
                innerRadius={44}
                outerRadius={65}
                paddingAngle={3}
                dataKey="value"
                strokeWidth={0}
              >
                {chartData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
            </PieChart>
          </ResponsiveContainer>

          {/* Center Total */}
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
                  {item.value}
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

export default ApplicationStatusChart;
