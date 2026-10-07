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
import type { SalaryDistribution } from '../../types';

interface SalaryDistributionChartProps {
  data?: SalaryDistribution[];
}

const SALARY_COLORS = ['#3B82F6', '#10B981', '#8B5CF6', '#F59E0B', '#EF4444'];

export const SalaryDistributionChart: React.FC<SalaryDistributionChartProps> = ({ data = [] }) => {
  const [isMobile, setIsMobile] = React.useState(() => typeof window !== 'undefined' && window.innerWidth < 640);

  React.useEffect(() => {
    const handleResize = () => setIsMobile(window.innerWidth < 640);
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const salaryDistribution = data ?? [];
  const totalSalary = salaryDistribution.reduce((acc, s) => acc + s.count, 0);

  const formatBracketLabel = (bracket: string): string => {
    if (!isMobile) return bracket;
    return bracket.replace(' LPA', 'L');
  };

  return (
    <div className="p-4 sm:p-5 rounded-2xl border border-slate-200/80 dark:border-slate-800 bg-white dark:bg-[#111726] shadow-sm flex flex-col justify-between h-[295px] sm:h-[280px]">
      <div className="flex items-start justify-between border-b border-slate-100 pb-3 dark:border-slate-800">
        <h3 className="text-[17px] font-bold tracking-tight text-slate-900 dark:text-white">
          Salary Range Distribution (₹ LPA)
        </h3>
        <span className="text-[12.5px] font-medium text-slate-700 dark:text-slate-400">
          {totalSalary} disclosed salaries
        </span>
      </div>

      <div className="flex-1 w-full mt-2 flex flex-col justify-center">
        {totalSalary === 0 ? (
          <div className="flex h-full flex-col items-center justify-center text-center p-4">
            <p className="text-[14px] font-semibold text-slate-700 dark:text-slate-300">
              Salary data unavailable
            </p>
            <p className="mt-1 text-[12px] text-slate-400 max-w-xs">
              Listings in this period did not disclose compensation brackets.
            </p>
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={salaryDistribution} margin={{ top: 20, right: 8, left: -16, bottom: isMobile ? 18 : 0 }}>
              <XAxis
                dataKey="bracket"
                tickLine={false}
                axisLine={false}
                interval={0}
                tickFormatter={formatBracketLabel}
                angle={isMobile ? -25 : 0}
                textAnchor={isMobile ? 'end' : 'middle'}
                height={isMobile ? 32 : 24}
                tick={{ fontSize: isMobile ? 10 : 11, fill: '#334155', fontWeight: 600, fontFamily: 'Inter, sans-serif' }}
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
                        <p className="font-semibold text-slate-200">{d.bracket}</p>
                        <p className="mt-0.5 font-bold text-emerald-400">{d.count} jobs in bracket</p>
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
                {salaryDistribution.map((_, index) => (
                  <Cell key={`sal-${index}`} fill={SALARY_COLORS[index % SALARY_COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
};

export default SalaryDistributionChart;
