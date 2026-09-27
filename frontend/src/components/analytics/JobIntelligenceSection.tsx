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
import { Info } from 'lucide-react';
import type { JobIntelligence } from '../../types';

interface JobIntelligenceSectionProps {
  data?: JobIntelligence;
}

const SCORE_COLORS: Record<string, string> = {
  '90-100%': '#3B82F6', // Blue
  '80-89%': '#8B5CF6',  // Purple
  '70-79%': '#10B981',  // Emerald
  '60-69%': '#F59E0B',  // Amber
  '<60%': '#EF4444',    // Red
};

const EXP_COLORS = ['#3B82F6', '#8B5CF6', '#10B981', '#F59E0B'];
const SALARY_COLORS = ['#3B82F6', '#10B981', '#8B5CF6', '#F59E0B', '#EF4444'];
const SKILL_COLORS = [
  '#8B5CF6',
  '#3B82F6',
  '#10B981',
  '#F97316',
  '#EF4444',
  '#6366F1',
  '#64748B',
  '#475569',
];

export const JobIntelligenceSection: React.FC<JobIntelligenceSectionProps> = ({ data }) => {
  const matchScores = data?.match_scores ?? [];
  const topSkills = data?.top_skills ?? [];
  const expDistribution = data?.experience_distribution ?? [];
  const salaryDistribution = data?.salary_distribution ?? [];

  const maxSkillCount = Math.max(...topSkills.slice(0, 5).map((s) => s.count), 1);
  const totalScores = matchScores.reduce((acc, s) => acc + s.count, 0);
  const totalExp = expDistribution.reduce((acc, s) => acc + s.count, 0);
  const totalSalary = salaryDistribution.reduce((acc, s) => acc + s.count, 0);

  return (
    <div className="space-y-4">
      {/* Section Header */}
      <div>
        <div className="flex items-center gap-1.5">
          <h2 className="text-[17px] font-bold text-slate-900 dark:text-white tracking-tight">
            Job Intelligence
          </h2>
          <span title="Understand the quality and relevance of opportunities being found">
            <Info className="h-3.5 w-3.5 text-slate-400 cursor-help" />
          </span>
        </div>
        <p className="mt-1 text-[13.5px] text-slate-800 dark:text-slate-300">
          Understand the quality and relevance of opportunities being found.
        </p>
      </div>

      {/* ROW 1: PRIMARY INSIGHTS (2 Larger Cards) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Card 1: Match Score Distribution */}
        <div className="p-5 rounded-2xl border border-slate-200/80 dark:border-slate-800 bg-white dark:bg-[#111726] shadow-sm flex flex-col justify-between h-[290px]">
          <div className="flex items-start justify-between border-b border-slate-100 pb-3 dark:border-slate-800">
            <h3 className="text-[17px] font-bold tracking-tight text-slate-900 dark:text-white">
              Match Score Distribution
            </h3>
            <span className="text-[12.5px] font-medium text-slate-700 dark:text-slate-400">
              {totalScores} analyzed jobs
            </span>
          </div>

          <div className="flex-1 w-full mt-2">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={matchScores} margin={{ top: 20, right: 8, left: -24, bottom: 0 }}>
                <XAxis
                  dataKey="range_label"
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
                  cursor={{ fill: 'rgba(148, 163, 184, 0.1)' }}
                  content={({ active, payload }) => {
                    if (active && payload && payload.length) {
                      const d = payload[0].payload;
                      return (
                        <div className="rounded-lg bg-slate-900 px-3 py-2 text-xs text-white shadow-md">
                          <p className="font-semibold text-slate-200">{d.range_label}</p>
                          <p className="mt-0.5 font-bold text-indigo-400">
                            {d.count} {d.count === 1 ? 'job' : 'jobs'} ({d.percentage}%)
                          </p>
                        </div>
                      );
                    }
                    return null;
                  }}
                />
                <Bar dataKey="count" radius={[5, 5, 0, 0]} maxBarSize={48} animationDuration={350} animationEasing="ease-out">
                  <LabelList
                    dataKey="count"
                    position="top"
                    style={{ fontSize: 12, fontWeight: 700, fill: '#1E293B' }}
                  />
                  {matchScores.map((entry, index) => (
                    <Cell
                      key={`score-${index}`}
                      fill={SCORE_COLORS[entry.range_label] || '#3B82F6'}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Card 2: Top Skills in Relevant Jobs */}
        <div className="p-5 rounded-2xl border border-slate-200/80 dark:border-slate-800 bg-white dark:bg-[#111726] shadow-sm flex flex-col justify-between h-[290px]">
          <div className="flex items-start justify-between border-b border-slate-100 pb-3 dark:border-slate-800">
            <h3 className="text-[17px] font-bold tracking-tight text-slate-900 dark:text-white">
              Top Skills in Relevant Jobs
            </h3>
            <span className="text-[12.5px] font-medium text-slate-700 dark:text-slate-400">
              Top 5 skills
            </span>
          </div>

          <div className="flex-1 flex flex-col justify-between py-1.5 mt-2">
            {topSkills.length === 0 ? (
              <div className="h-full flex items-center justify-center text-xs text-slate-400">
                No skill requirements captured
              </div>
            ) : (
              topSkills.slice(0, 5).map((item, idx) => {
                const widthPct = Math.max(12, Math.round((item.count / maxSkillCount) * 100));
                const barColor = SKILL_COLORS[idx % SKILL_COLORS.length];
                return (
                  <div key={item.skill} className="flex items-center gap-3">
                    <span
                      className="w-28 truncate font-semibold text-slate-800 dark:text-slate-100 shrink-0 text-[13px]"
                      title={item.skill}
                    >
                      {item.skill}
                    </span>
                    <div className="flex-1 bg-slate-100 dark:bg-slate-800/80 rounded-full h-3.5 overflow-hidden">
                      <div
                        className="h-full rounded-full transition-all duration-500"
                        style={{ width: `${widthPct}%`, backgroundColor: barColor }}
                      />
                    </div>
                    <span className="w-7 text-right font-bold text-slate-800 dark:text-slate-100 text-[13px] shrink-0 tabular-nums">
                      {item.count}
                    </span>
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>

      {/* ROW 2: SUPPORTING DISTRIBUTIONS (2 Balanced Cards) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Card 3: Experience Level Distribution */}
        <div className="p-5 rounded-2xl border border-slate-200/80 dark:border-slate-800 bg-white dark:bg-[#111726] shadow-sm flex flex-col justify-between h-[280px]">
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
              <BarChart data={expDistribution} margin={{ top: 20, right: 8, left: -24, bottom: 0 }}>
                <XAxis
                  dataKey="level"
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
                <Bar dataKey="count" radius={[5, 5, 0, 0]} maxBarSize={48} animationDuration={350} animationEasing="ease-out">
                  <LabelList
                    dataKey="count"
                    position="top"
                    style={{ fontSize: 12, fontWeight: 700, fill: '#1E293B' }}
                  />
                  {expDistribution.map((_, index) => (
                    <Cell key={`exp-${index}`} fill={EXP_COLORS[index % EXP_COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Card 4: Salary Range Distribution (₹ LPA) */}
        <div className="p-5 rounded-2xl border border-slate-200/80 dark:border-slate-800 bg-white dark:bg-[#111726] shadow-sm flex flex-col justify-between h-[280px]">
          <div className="flex items-start justify-between border-b border-slate-100 pb-3 dark:border-slate-800">
            <h3 className="text-[17px] font-bold tracking-tight text-slate-900 dark:text-white">
              Salary Range Distribution (₹ LPA)
            </h3>
            <span className="text-[12.5px] font-medium text-slate-700 dark:text-slate-400">
              {totalSalary} disclosed salaries
            </span>
          </div>

          <div className="flex-1 w-full mt-2">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={salaryDistribution} margin={{ top: 20, right: 8, left: -24, bottom: 0 }}>
                <XAxis
                  dataKey="bracket"
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
                <Bar dataKey="count" radius={[5, 5, 0, 0]} maxBarSize={48} animationDuration={350} animationEasing="ease-out">
                  <LabelList
                    dataKey="count"
                    position="top"
                    style={{ fontSize: 12, fontWeight: 700, fill: '#1E293B' }}
                  />
                  {salaryDistribution.map((_, index) => (
                    <Cell key={`sal-${index}`} fill={SALARY_COLORS[index % SALARY_COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
};

export default JobIntelligenceSection;

