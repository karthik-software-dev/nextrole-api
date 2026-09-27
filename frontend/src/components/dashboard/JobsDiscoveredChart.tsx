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
import type { DiscoveryTrendItem } from '../../types';

interface JobsDiscoveredChartProps {
  data?: DiscoveryTrendItem[];
}

export const JobsDiscoveredChart: React.FC<JobsDiscoveredChartProps> = ({ data }) => {
  const chartData = data && data.length > 0 ? data : [];
  const totalInPeriod = chartData.reduce((acc, item) => acc + item.count, 0);
  const latestCount = chartData.length > 0 ? chartData[chartData.length - 1].count : 0;
  const isConcentratedRecently = totalInPeriod > 0 && latestCount >= totalInPeriod * 0.75;

  return (
    <div className="relative flex h-[315px] flex-col overflow-hidden rounded-2xl border border-slate-200/80 bg-white p-5 shadow-sm transition-[transform,box-shadow,border-color] duration-180 ease-out hover:-translate-y-0.5 hover:shadow-md dark:border-slate-800 dark:bg-[#111726]">
      {/* Header */}
      <div className="flex items-start justify-between border-b border-slate-100 pb-3 dark:border-slate-800">
        <h3 className="text-[17px] font-bold tracking-tight text-slate-900 dark:text-white">
          Jobs Discovered
        </h3>
        <div className="flex items-center gap-2">
          {isConcentratedRecently && (
            <span className="hidden sm:inline-flex items-center rounded-md bg-violet-50 dark:bg-violet-950/60 px-2 py-0.5 text-[10px] font-semibold text-violet-700 dark:text-violet-300">
              Most jobs discovered today
            </span>
          )}
          <span className="text-[12.5px] font-medium text-slate-700 dark:text-slate-400">
            {totalInPeriod} total in period
          </span>
        </div>
      </div>

      {/* Chart */}
      <div className="w-full flex-1 pt-3">
        {chartData.length === 0 ? (
          <div className="flex h-full items-center justify-center text-xs text-slate-400">
            No discovery data available for this period.
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData} margin={{ top: 12, right: 12, left: -24, bottom: 0 }}>
              <defs>
                <linearGradient id="discoveryGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#8B5CF6" stopOpacity={0.35} />
                  <stop offset="95%" stopColor="#8B5CF6" stopOpacity={0.0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E2E8F0" opacity={0.4} />
              <XAxis
                dataKey="date"
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
                    const item = payload[0].payload as DiscoveryTrendItem;
                    return (
                      <div className="rounded-lg bg-slate-900 px-3 py-2 text-xs text-white shadow-lg">
                        <p className="font-semibold text-slate-200">{item.date}</p>
                        <p className="mt-0.5 text-[13px] font-bold text-violet-400">
                          {item.count} {item.count === 1 ? 'job discovered' : 'jobs discovered'}
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
                fill="url(#discoveryGradient)"
                dot={{ r: 3.5, fill: '#8B5CF6', strokeWidth: 1, stroke: '#FFFFFF' }}
                activeDot={{ r: 5, fill: '#7C3AED', strokeWidth: 2, stroke: '#FFFFFF' }}
                animationDuration={350}
                animationEasing="ease-out"
              />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
};

export default JobsDiscoveredChart;
