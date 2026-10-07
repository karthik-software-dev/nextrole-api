import React from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
  LabelList,
} from 'recharts';
import type { ExperienceDistribution } from '../../types';

interface ExperienceDistributionChartProps {
  data?: ExperienceDistribution[];
}

const EXP_COLORS = ['#3B82F6', '#8B5CF6', '#10B981', '#F59E0B'];

export const ExperienceDistributionChart: React.FC<ExperienceDistributionChartProps> = ({ data = [] }) => {
  const expDistribution = data ?? [];
  const totalExp = expDistribution.reduce((acc, s) => acc + s.count, 0);

  return (
    <div className="p-4 sm:p-5 rounded-2xl border border-slate-200/80 dark:border-slate-800 bg-white dark:bg-[#111726] shadow-sm flex flex-col justify-between h-[280px]">
      <div className="flex items-start justify-between border-b border-slate-100 pb-3 dark:border-slate-800">
        <h3 className="text-[17px] font-bold tracking-tight text-slate-900 dark:text-white">
          Experience Level Distribution
        </h3>
        <span className="text-[12.5px] font-medium text-slate-700 dark:text-slate-400">
          {totalExp} opportunities
        </span>
      </div>

      <div className="flex-1 w-full mt-2">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={expDistribution} margin={{ top: 20, right: 8, left: -16, bottom: 0 }}>
            <XAxis
              dataKey="level"
              tickLine={false}
              axisLine={false}
              tick={{ fontSize: 11, fill: '#334155', fontWeight: 600, fontFamily: 'Inter, sans-serif' }}
            />
            <YAxis
              tickLine={false}
              axisLine={false}
              tick={{ fontSize: 11, fill: '#334155', fontWeight: 600, fontFamily: 'Inter, sans-serif' }}
              allowDecimals={false}
            />
            <Tooltip
              cursor={{ fill: 'rgba(148, 163, 184, 0.1)' }}
              content={({ active, payload }) => {
                if (active && payload && payload.length) {
                  const d = payload[0].payload;
                  return (
                    <div className="rounded-lg bg-slate-900 px-3 py-2 text-xs text-white shadow-md">
                      <p className="font-semibold text-slate-200">{d.level}</p>
                      <p className="mt-0.5 font-bold text-violet-400">{d.count} opportunities</p>
                    </div>
                  );
                }
                return null;
              }}
            />
            <Bar dataKey="count" radius={[5, 5, 0, 0]} maxBarSize={36} animationDuration={350} animationEasing="ease-out">
              <LabelList
                dataKey="count"
                position="top"
                style={{ fontSize: 11.5, fontWeight: 700, fill: '#1E293B' }}
              />
              {expDistribution.map((_, index) => (
                <Cell key={`exp-${index}`} fill={EXP_COLORS[index % EXP_COLORS.length]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

export default ExperienceDistributionChart;
