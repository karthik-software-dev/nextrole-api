import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  BarChart,
  Bar,
  PieChart,
  Pie,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
  LabelList,
} from 'recharts';
import {
  Briefcase,
  CheckCircle2,
  Zap,
  Target,
  ChevronRight,
  Globe,
  Building2,
  Laptop,
  Code2,
} from 'lucide-react';
import type { JobIntelligence, PipelineAnalytics, JobTitleStat, WorkModeStat, TechStackPairStat } from '../../types';

interface JobDiscoverySectionProps {
  data?: JobIntelligence;
  pipelineData?: PipelineAnalytics;
}

const SCORE_COLORS: Record<string, string> = {
  '90-100%': '#3B82F6', // Blue
  '80-89%': '#8B5CF6',  // Purple
  '70-79%': '#10B981',  // Emerald
  '60-69%': '#F59E0B',  // Amber
  '<60%': '#EF4444',    // Red
};

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

const PAIR_COLORS = [
  '#6366F1', // Indigo
  '#3B82F6', // Blue
  '#10B981', // Emerald
  '#8B5CF6', // Purple
  '#F59E0B', // Amber
];

const ROLE_COLORS = [
  '#6366F1', // Indigo
  '#8B5CF6', // Purple
  '#3B82F6', // Blue
  '#0EA5E9', // Sky
  '#10B981', // Emerald
];

const formatRoleLabel = (title: string, isMobile: boolean = false): string => {
  if (isMobile) {
    if (/python/i.test(title)) return 'Python';
    if (/full\s*stack/i.test(title)) return 'Full Stack';
    if (/frontend/i.test(title)) return 'Frontend';
    if (/backend/i.test(title)) return 'Backend';
    if (/devops/i.test(title)) return 'DevOps';
    if (/data/i.test(title)) return 'Data';
    if (/cloud/i.test(title)) return 'Cloud';
    const cleaned = title.replace(/Developer|Engineer|Architect/gi, '').trim();
    return cleaned.length > 10 ? `${cleaned.slice(0, 9)}…` : cleaned || title;
  }
  const simplified = title
    .replace(/Developer/i, 'Dev')
    .replace(/Engineer/i, 'Eng')
    .replace(/Python Backend Dev/i, 'Python Backend')
    .trim();
  return simplified.length > 14 ? `${simplified.slice(0, 13)}…` : simplified;
};

export const JobDiscoverySection: React.FC<JobDiscoverySectionProps> = ({
  data,
  pipelineData,
}) => {
  const navigate = useNavigate();
  const [isMobile, setIsMobile] = React.useState(() => typeof window !== 'undefined' && window.innerWidth < 640);

  React.useEffect(() => {
    const handleResize = () => setIsMobile(window.innerWidth < 640);
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const [hoveredStackPair, setHoveredStackPair] = React.useState<TechStackPairStat | null>(null);
  const matchScores = data?.match_scores ?? [];
  const topSkills = data?.top_skills ?? [];
  const topCompanies = data?.top_hiring_companies ?? [];
  const topTitles = data?.top_job_titles ?? [];
  const workModes = data?.work_modes ?? [];
  const techStackPairs = data?.tech_stack_pairs ?? [];
  const totalWorkModeRoles = workModes.reduce((acc, wm) => acc + wm.count, 0);

  // Discovery Overview Calculations
  const jobsDiscovered =
    pipelineData?.jobs_normalized ||
    matchScores.reduce((acc, s) => acc + s.count, 0) ||
    0;
  const relevantJobs = pipelineData?.relevant_jobs || 0;
  const actionableJobs = pipelineData?.actionable_jobs || 0;

  // High Match Jobs: 80%+ match (sum of 90-100% and 80-89% buckets)
  const highMatchJobs = matchScores
    .filter((s) => s.range_label === '90-100%' || s.range_label === '80-89%')
    .reduce((acc, s) => acc + s.count, 0);

  const totalScores = matchScores.reduce((acc, s) => acc + s.count, 0);
  const maxSkillCount = Math.max(...topSkills.slice(0, 7).map((s) => s.count), 1);

  const discoveryKpis = [
    {
      id: 'jobs-analyzed',
      title: 'Jobs Analyzed',
      value: jobsDiscovered,
      subtext: 'Normalized unique opportunities',
      icon: Briefcase,
      color: 'text-indigo-600 dark:text-indigo-400',
      bg: 'bg-indigo-50 dark:bg-indigo-950/60',
      ring: 'ring-1 ring-inset ring-indigo-600/15 dark:ring-indigo-400/20',
    },
    {
      id: 'relevant-jobs',
      title: 'Relevant Jobs',
      value: relevantJobs,
      subtext: `${jobsDiscovered > 0 ? Math.round((relevantJobs / jobsDiscovered) * 100) : 0}% meet target tech stack`,
      icon: CheckCircle2,
      color: 'text-emerald-600 dark:text-emerald-400',
      bg: 'bg-emerald-50 dark:bg-emerald-950/60',
      ring: 'ring-1 ring-inset ring-emerald-600/15 dark:ring-emerald-400/20',
    },
    {
      id: 'high-match-jobs',
      title: 'High-Match Jobs',
      value: highMatchJobs,
      subtext: `${jobsDiscovered > 0 ? Math.round((highMatchJobs / jobsDiscovered) * 100) : 0}% scored ≥ 80% relevance`,
      icon: Zap,
      color: 'text-amber-600 dark:text-amber-400',
      bg: 'bg-amber-50 dark:bg-amber-950/60',
      ring: 'ring-1 ring-inset ring-amber-600/15 dark:ring-amber-400/20',
    },
    {
      id: 'actionable-jobs',
      title: 'Actionable Jobs',
      value: actionableJobs,
      subtext: 'Tier 1 top priority opportunities',
      icon: Target,
      color: 'text-violet-600 dark:text-violet-400',
      bg: 'bg-violet-50 dark:bg-violet-950/60',
      ring: 'ring-1 ring-inset ring-violet-600/15 dark:ring-violet-400/20',
    },
  ];

  return (
    <div className="space-y-6">
      {/* -------------------------------------------------- */}
      {/* SECTION 2.1 — DISCOVERY OVERVIEW (4 KPI Cards)     */}
      {/* -------------------------------------------------- */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {discoveryKpis.map((kpi) => {
          const Icon = kpi.icon;
          return (
            <div
              key={kpi.id}
              className="flex items-center justify-between rounded-2xl border border-slate-200/80 bg-white p-[18px] shadow-sm dark:border-slate-800 dark:bg-[#111726]"
            >
              <div className="flex items-center gap-4 min-w-0">
                <div
                  className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-xl ${kpi.bg} ${kpi.color} ${kpi.ring} shadow-xs`}
                >
                  <Icon className="h-[18px] w-[18px]" />
                </div>
                <div className="min-w-0">
                  <span className="text-[13.5px] font-semibold text-slate-600 dark:text-slate-400 block truncate">
                    {kpi.title}
                  </span>
                  <p className="mt-1 text-[36px] font-bold leading-none tracking-tight text-slate-900 dark:text-white">
                    {kpi.value}
                  </p>
                  <p className="mt-1.5 truncate text-[12px] font-medium text-slate-500 dark:text-slate-400">
                    {kpi.subtext}
                  </p>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* -------------------------------------------------- */}
      {/* ROW 1: MATCH QUALITY & TOP IN-DEMAND SKILLS        */}
      {/* -------------------------------------------------- */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Card 1: Match Score Distribution */}
        <div className="p-4 sm:p-5 rounded-2xl border border-slate-200/80 dark:border-slate-800 bg-white dark:bg-[#111726] shadow-sm flex flex-col justify-between h-[315px]">
          <div className="flex items-start justify-between border-b border-slate-100 pb-3 dark:border-slate-800">
            <h3 className="text-[17px] font-bold tracking-tight text-slate-900 dark:text-white">
              Match Score Distribution
            </h3>
            <span className="text-[12.5px] font-medium text-slate-700 dark:text-slate-400">
              {totalScores} analyzed jobs
            </span>
          </div>

          <div className="flex-1 w-full mt-3">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={matchScores} margin={{ top: 20, right: 8, left: -16, bottom: isMobile ? 18 : 0 }}>
                <XAxis
                  dataKey="range_label"
                  tickLine={false}
                  axisLine={false}
                  interval={0}
                  angle={isMobile ? -25 : 0}
                  textAnchor={isMobile ? 'end' : 'middle'}
                  height={isMobile ? 32 : 24}
                  tick={{ fontSize: isMobile ? 10 : 11, fill: '#64748B', fontWeight: 600, fontFamily: 'Inter, sans-serif' }}
                />
                <YAxis
                  tickLine={false}
                  axisLine={false}
                  tick={{ fontSize: 11, fill: '#64748B', fontWeight: 600, fontFamily: 'Inter, sans-serif' }}
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
                <Bar dataKey="count" radius={[5, 5, 0, 0]} maxBarSize={36} animationDuration={350} animationEasing="ease-out">
                  <LabelList
                    dataKey="count"
                    position="top"
                    style={{ fontSize: 11.5, fontWeight: 700, fill: '#334155' }}
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
        <div className="p-4 sm:p-5 rounded-2xl border border-slate-200/80 dark:border-slate-800 bg-white dark:bg-[#111726] shadow-sm flex flex-col justify-between h-[315px]">
          <div className="flex items-start justify-between border-b border-slate-100 pb-3 dark:border-slate-800">
            <h3 className="text-[17px] font-bold tracking-tight text-slate-900 dark:text-white">
              Top In-Demand Skills
            </h3>
            <span className="text-[12.5px] font-medium text-slate-700 dark:text-slate-400">
              Top {topSkills.length} skills
            </span>
          </div>

          <div className="flex-1 flex flex-col justify-between py-1 mt-2">
            {topSkills.length === 0 ? (
              <div className="h-full flex items-center justify-center text-xs text-slate-400">
                No skill requirements captured
              </div>
            ) : (
              topSkills.slice(0, 7).map((item, idx) => {
                const widthPct = Math.max(12, Math.round((item.count / maxSkillCount) * 100));
                const barColor = SKILL_COLORS[idx % SKILL_COLORS.length];
                return (
                  <div key={item.skill} className="flex items-center gap-2.5 sm:gap-3">
                    <span
                      className="w-24 sm:w-28 truncate font-semibold text-slate-800 dark:text-slate-100 shrink-0 text-[12px] sm:text-[13px]"
                      title={item.skill}
                    >
                      {item.skill}
                    </span>
                    <div className="flex-1 bg-slate-100 dark:bg-slate-800/80 rounded-full h-2.5 overflow-hidden">
                      <div
                        className="h-full rounded-full transition-all duration-500"
                        style={{ width: `${widthPct}%`, backgroundColor: barColor }}
                      />
                    </div>
                    <span className="w-6 sm:w-7 text-right font-bold text-slate-800 dark:text-slate-100 text-[12px] sm:text-[13px] shrink-0 tabular-nums">
                      {item.count}
                    </span>
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>

      {/* -------------------------------------------------- */}
      {/* ROW 2: HIRING COMPANIES & TRENDING ROLES           */}
      {/* -------------------------------------------------- */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Card 1: Top Hiring Companies */}
        <div className="relative flex min-h-[345px] sm:min-h-0 sm:h-[315px] flex-col overflow-hidden rounded-2xl border border-slate-200/80 bg-white p-4 sm:p-5 shadow-sm transition-[transform,box-shadow,border-color] duration-180 ease-out hover:-translate-y-0.5 hover:shadow-md dark:border-slate-800 dark:bg-[#111726]">
          <div className="flex items-start justify-between border-b border-slate-100 pb-3 dark:border-slate-800">
            <h3 className="text-[17px] font-bold tracking-tight text-slate-900 dark:text-white">
              Top Hiring Companies
            </h3>
            <Link
              to="/companies"
              className="text-[12.5px] font-semibold text-indigo-600 hover:text-indigo-700 dark:text-indigo-400"
            >
              View All
            </Link>
          </div>

          <div className="flex-1 divide-y divide-slate-100 dark:divide-slate-800/80 py-0.5 mt-0.5 overflow-y-auto pr-1">
            {topCompanies.length === 0 ? (
              <div className="h-full flex items-center justify-center text-xs text-slate-400">
                No company data available
              </div>
            ) : (
              topCompanies.slice(0, 5).map((comp) => (
                <div
                  key={comp.name}
                  className="flex items-center justify-between py-1 sm:py-1.5 hover:bg-slate-50/60 dark:hover:bg-slate-800/30 px-2 rounded-xl transition-colors"
                >
                  <div className="flex items-center gap-2.5 min-w-0">
                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400 font-bold text-xs ring-1 ring-inset ring-indigo-600/15">
                      {comp.name.slice(0, 2).toUpperCase()}
                    </div>
                    <span className="font-semibold text-slate-800 dark:text-slate-100 text-[13.5px] truncate">
                      {comp.name}
                    </span>
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    <span className="inline-flex items-center px-2 py-0.5 rounded-md text-[11.5px] font-bold bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300">
                      {comp.active_jobs} open {comp.active_jobs === 1 ? 'job' : 'jobs'}
                    </span>
                    <Link
                      to={`/jobs?search=${encodeURIComponent(comp.name)}`}
                      className="p-1 rounded-lg text-slate-400 hover:text-indigo-600 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
                      title={`View jobs at ${comp.name}`}
                    >
                      <ChevronRight className="h-4 w-4" />
                    </Link>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Card 2: Top Job Titles / Roles (Vertical Bar Chart) */}
        <div className="relative flex h-[315px] flex-col overflow-hidden rounded-2xl border border-slate-200/80 bg-white p-4 sm:p-5 shadow-sm transition-[transform,box-shadow,border-color] duration-180 ease-out hover:-translate-y-0.5 hover:shadow-md dark:border-slate-800 dark:bg-[#111726]">
          <div className="flex items-start justify-between border-b border-slate-100 pb-3 dark:border-slate-800">
            <h3 className="text-[17px] font-bold tracking-tight text-slate-900 dark:text-white">
              Top Trending Roles
            </h3>
            <span className="text-[12.5px] font-medium text-slate-700 dark:text-slate-400">
              Top {topTitles.length} roles
            </span>
          </div>

          <div className="flex-1 w-full mt-3">
            {topTitles.length === 0 ? (
              <div className="h-full flex items-center justify-center text-xs text-slate-400">
                No role data available
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={topTitles.slice(0, 5)}
                  margin={{ top: 20, right: 8, left: -16, bottom: isMobile ? 22 : 0 }}
                >
                  <XAxis
                    dataKey="title"
                    tickLine={false}
                    axisLine={false}
                    tickFormatter={(val: string) => formatRoleLabel(val, isMobile)}
                    interval={0}
                    angle={isMobile ? -30 : 0}
                    textAnchor={isMobile ? 'end' : 'middle'}
                    height={isMobile ? 42 : 24}
                    tick={{ fontSize: isMobile ? 9.5 : 10.5, fill: '#64748B', fontWeight: 600, fontFamily: 'Inter, sans-serif' }}
                  />
                  <YAxis
                    tickLine={false}
                    axisLine={false}
                    tick={{ fontSize: 11, fill: '#64748B', fontWeight: 600, fontFamily: 'Inter, sans-serif' }}
                    allowDecimals={false}
                  />
                  <Tooltip
                    cursor={{ fill: 'rgba(148, 163, 184, 0.1)' }}
                    content={({ active, payload }) => {
                      if (active && payload && payload.length) {
                        const d = payload[0].payload as JobTitleStat;
                        return (
                          <div className="rounded-lg bg-slate-900 px-3 py-2 text-xs text-white shadow-lg">
                            <p className="font-bold text-white">{d.title}</p>
                            <p className="mt-0.5 font-medium text-slate-300">
                              {d.count} {d.count === 1 ? 'open role' : 'open roles'}
                            </p>
                            <p className="mt-1 text-[11px] text-indigo-400 font-medium">Click to view open jobs &rarr;</p>
                          </div>
                        );
                      }
                      return null;
                    }}
                  />
                  <Bar
                    dataKey="count"
                    radius={[5, 5, 0, 0]}
                    maxBarSize={36}
                    animationDuration={350}
                    animationEasing="ease-out"
                    className="cursor-pointer"
                    onClick={(entry) => {
                      if (entry && (entry as unknown as JobTitleStat).title) {
                        navigate(`/jobs?search=${encodeURIComponent((entry as unknown as JobTitleStat).title)}`);
                      }
                    }}
                  >
                    <LabelList
                      dataKey="count"
                      position="top"
                      style={{ fontSize: 11.5, fontWeight: 700, fill: '#334155' }}
                    />
                    {topTitles.slice(0, 5).map((entry, index) => (
                      <Cell
                        key={`title-cell-${index}`}
                        fill={ROLE_COLORS[index % ROLE_COLORS.length]}
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>
      </div>

      {/* -------------------------------------------------- */}
      {/* ROW 3: WORK MODE & TECH STACK PAIRS                */}
      {/* -------------------------------------------------- */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Card 3: Work Mode Breakdown (Donut Chart) */}
        <div className="relative flex min-h-[380px] sm:min-h-0 sm:h-[315px] flex-col overflow-hidden rounded-2xl border border-slate-200/80 bg-white p-4 sm:p-5 shadow-sm transition-[transform,box-shadow,border-color] duration-180 ease-out hover:-translate-y-0.5 hover:shadow-md dark:border-slate-800 dark:bg-[#111726]">
          <div className="flex items-start justify-between border-b border-slate-100 pb-3 dark:border-slate-800">
            <h3 className="text-[17px] font-bold tracking-tight text-slate-900 dark:text-white">
              Work Mode
            </h3>
            <span className="text-[12.5px] font-medium text-slate-700 dark:text-slate-400">
              {totalWorkModeRoles || jobsDiscovered} total roles
            </span>
          </div>

          <div className="flex flex-1 flex-col sm:flex-row items-center gap-4 pt-3">
            {workModes.length === 0 ? (
              <div className="flex h-full w-full items-center justify-center text-xs text-slate-400">
                No work mode data available.
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
                            const d = payload[0].payload as WorkModeStat;
                            return (
                              <div className="rounded-lg bg-slate-900 px-3 py-2 text-xs text-white shadow-lg">
                                <p className="font-bold text-white">{d.mode}</p>
                                <p className="mt-0.5 font-medium text-slate-300">
                                  {d.count} {d.count === 1 ? 'role' : 'roles'} · {d.percentage}%
                                </p>
                              </div>
                            );
                          }
                          return null;
                        }}
                      />
                      <Pie
                        data={workModes}
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
                        {workModes.map((entry, index) => {
                          const lower = entry.mode.toLowerCase();
                          const color =
                            lower.includes('remote') && !lower.includes('hybrid')
                              ? '#10B981'
                              : lower.includes('hybrid')
                              ? '#8B5CF6'
                              : '#6366F1';
                          return <Cell key={`wm-${index}`} fill={color} />;
                        })}
                      </Pie>
                    </PieChart>
                  </ResponsiveContainer>

                  {/* Center Total */}
                  <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                    <span className="text-[22px] sm:text-[26px] font-black tracking-tight text-slate-900 dark:text-white leading-none">
                      {totalWorkModeRoles || jobsDiscovered}
                    </span>
                    <span className="text-[10px] sm:text-[11px] font-semibold text-slate-700 dark:text-slate-500 mt-1 uppercase tracking-wider">
                      Total Roles
                    </span>
                  </div>
                </div>

                {/* Right Legend: Listed one by one */}
                <div className="w-full sm:flex-1 flex flex-col space-y-2 sm:space-y-3 min-w-0 select-none pr-1 sm:pr-2 my-auto">
                  {workModes.map((item) => {
                    const lower = item.mode.toLowerCase();
                    const color =
                      lower.includes('remote') && !lower.includes('hybrid')
                        ? '#10B981'
                        : lower.includes('hybrid')
                        ? '#8B5CF6'
                        : '#6366F1';
                    return (
                      <div
                        key={item.mode}
                        className="flex h-[28px] sm:h-[32px] shrink-0 items-center justify-between gap-1.5 sm:gap-2"
                      >
                        <div className="flex items-center gap-1.5 sm:gap-2 min-w-0">
                          <span
                            className="h-2 w-2 sm:h-2.5 sm:w-2.5 rounded-full shrink-0"
                            style={{ backgroundColor: color }}
                          />
                          <span className="text-[12px] sm:text-[13.5px] font-medium text-slate-800 dark:text-slate-200 truncate">
                            {item.mode}
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
                    );
                  })}
                </div>
              </>
            )}
          </div>
        </div>

        {/* Card 4: Tech Stack Pairs (Apple Ring Style) */}
        <div className="relative flex min-h-[380px] sm:min-h-0 sm:h-[315px] flex-col overflow-hidden rounded-2xl border border-slate-200/80 bg-white p-4 sm:p-5 shadow-sm transition-[transform,box-shadow,border-color] duration-180 ease-out hover:-translate-y-0.5 hover:shadow-md dark:border-slate-800 dark:bg-[#111726]">
          <div className="flex items-start justify-between border-b border-slate-100 pb-3 dark:border-slate-800">
            <h3 className="text-[17px] font-bold tracking-tight text-slate-900 dark:text-white">
              Tech Stack Pairs
            </h3>
            <span className="text-[12.5px] font-medium text-slate-700 dark:text-slate-400">
              Top {techStackPairs.length} combinations
            </span>
          </div>

          <div className="flex flex-1 flex-col sm:flex-row items-center gap-4 pt-3">
            {techStackPairs.length === 0 ? (
              <div className="flex h-full w-full items-center justify-center text-xs text-slate-400">
                No stack pair data available.
              </div>
            ) : (
              <>
                {/* Apple Activity Style Concentric Rings */}
                <div className="relative shrink-0 w-[160px] h-[160px] sm:w-[185px] sm:h-[185px] flex items-center justify-center mx-auto sm:mx-0">
                  <svg className="w-full h-full" viewBox="0 0 185 185">
                    {(() => {
                      const maxPairPct = Math.max(...techStackPairs.slice(0, 5).map((p) => p.percentage), 1);
                      return techStackPairs.slice(0, 5).map((item, idx) => {
                        const r = 80 - idx * 11;
                        const circumference = 2 * Math.PI * r;
                        // Relative ring coverage so rings sweep ~64%–88% around the circle, wrapping into the left side
                        const normalizedCoverage = Math.min(94, Math.max(15, (item.percentage / maxPairPct) * 88));
                        const strokeDashoffset = circumference - (circumference * normalizedCoverage) / 100;
                        const color = PAIR_COLORS[idx % PAIR_COLORS.length];
                        const isHovered = hoveredStackPair?.pair === item.pair;
                        const isAnyHovered = hoveredStackPair !== null;

                        return (
                          <g
                            key={item.pair}
                            className="cursor-pointer transition-opacity duration-200"
                            style={{ opacity: isAnyHovered ? (isHovered ? 1 : 0.3) : 1 }}
                            onMouseEnter={() => setHoveredStackPair(item)}
                            onMouseLeave={() => setHoveredStackPair(null)}
                          >
                            <title>{`${item.pair}: ${item.count} jobs (${item.percentage}%)`}</title>
                            {/* Faint Background Track */}
                            <circle
                              cx={92.5}
                              cy={92.5}
                              r={r}
                              fill="none"
                              stroke={color}
                              strokeWidth={7.5}
                              className="opacity-15 dark:opacity-25"
                            />
                            {/* Active Progress Ring with Rounded Caps */}
                            <circle
                              cx={92.5}
                              cy={92.5}
                              r={r}
                              fill="none"
                              stroke={color}
                              strokeWidth={isHovered ? 8.5 : 7.5}
                              strokeLinecap="round"
                              strokeDasharray={circumference}
                              strokeDashoffset={strokeDashoffset}
                              transform="rotate(-90 92.5 92.5)"
                              className="transition-all duration-300"
                            />
                          </g>
                        );
                      });
                    })()}
                  </svg>

                  {/* Center Interactive Glyph / Stat */}
                  <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none transition-all duration-200">
                    {hoveredStackPair ? (
                      <>
                        <span className="text-[18px] font-black tracking-tight text-slate-900 dark:text-white leading-none">
                          {hoveredStackPair.percentage}%
                        </span>
                        <span className="text-[10px] font-bold text-indigo-600 dark:text-indigo-400 uppercase tracking-wider mt-0.5 max-w-[55px] truncate text-center">
                          {hoveredStackPair.skill}
                        </span>
                      </>
                    ) : (
                      <>
                        <Code2 className="h-5 w-5 text-indigo-500 dark:text-indigo-400" />
                        <span className="text-[10px] font-bold text-slate-700 dark:text-slate-400 uppercase tracking-wider mt-0.5">
                          Stack
                        </span>
                      </>
                    )}
                  </div>
                </div>

                {/* Right Legend List */}
                <div className="w-full sm:flex-1 flex flex-col min-w-0 select-none pr-1 space-y-1.5 my-auto">
                  {techStackPairs.slice(0, 5).map((item, idx) => {
                    const color = PAIR_COLORS[idx % PAIR_COLORS.length];
                    const isHovered = hoveredStackPair?.pair === item.pair;
                    const isAnyHovered = hoveredStackPair !== null;

                    return (
                      <div
                        key={item.pair}
                        onMouseEnter={() => setHoveredStackPair(item)}
                        onMouseLeave={() => setHoveredStackPair(null)}
                        className={`flex h-[26px] sm:h-[28px] shrink-0 items-center justify-between gap-2 px-1.5 py-0.5 rounded-lg cursor-pointer transition-all duration-150 ${
                          isHovered
                            ? 'bg-slate-100 dark:bg-slate-800'
                            : isAnyHovered
                            ? 'opacity-40'
                            : 'hover:bg-slate-50 dark:hover:bg-slate-800/40'
                        }`}
                      >
                        <div className="flex items-center gap-2 min-w-0">
                          <span
                            className="h-2.5 w-2.5 rounded-full shrink-0 transition-transform duration-150"
                            style={{
                              backgroundColor: color,
                              transform: isHovered ? 'scale(1.25)' : 'scale(1)',
                            }}
                          />
                          <span
                            className="text-[12.5px] sm:text-[13px] font-medium text-slate-800 dark:text-slate-200 truncate"
                            title={item.pair}
                          >
                            {item.pair}
                          </span>
                        </div>
                        <div className="flex items-center gap-1.5 shrink-0">
                          <span className="text-[12.5px] sm:text-[13px] font-bold text-slate-800 dark:text-slate-100 tabular-nums">
                            {item.count}
                          </span>
                          <span className="text-[11px] sm:text-[12px] font-medium text-slate-600 dark:text-slate-400 tabular-nums">
                            ({item.percentage}%)
                          </span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export const JobIntelligenceSection = JobDiscoverySection;
export default JobDiscoverySection;
