import React from 'react';
import { Link } from 'react-router-dom';
import { Send, ChevronRight } from 'lucide-react';
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
  const [isMobile, setIsMobile] = React.useState(() => typeof window !== 'undefined' && window.innerWidth < 640);

  React.useEffect(() => {
    const handleResize = () => setIsMobile(window.innerWidth < 640);
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const formatStageLabel = (name: string): string => {
    if (!isMobile) return name;
    if (name === 'Under Review') return 'Review';
    return name;
  };

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
    <div className="relative flex h-[315px] flex-col overflow-hidden rounded-2xl border border-slate-200/80 bg-white p-4 sm:p-5 shadow-sm transition-[transform,box-shadow,border-color] duration-180 ease-out hover:-translate-y-0.5 hover:shadow-md dark:border-slate-800 dark:bg-[#111726]">
      {/* Header */}
      <div className="flex items-start justify-between border-b border-slate-100 pb-3 dark:border-slate-800">
        <h3 className="text-[17px] font-bold tracking-tight text-slate-900 dark:text-white">
          Application Pipeline
        </h3>
        <span className="text-[12.5px] font-medium text-slate-700 dark:text-slate-400">
          {total} total applications
        </span>
      </div>

      {/* Chart or Empty State */}
      <div className="w-full flex-1 pt-3 flex flex-col justify-center">
        {total === 0 ? (
          <div className="flex h-full flex-col items-center justify-center text-center p-4">
            <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400 ring-1 ring-inset ring-indigo-600/15 mb-3">
              <Send className="h-5 w-5" />
            </div>
            <h4 className="text-[15px] font-bold text-slate-800 dark:text-slate-200">
              No applications yet
            </h4>
            <p className="mt-1 text-[12.5px] text-slate-500 dark:text-slate-400 max-w-xs">
              Start applying to recommended jobs to build your application pipeline.
            </p>
            <Link
              to="/jobs?tier=Tier+1"
              className="mt-3.5 inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-indigo-50 dark:bg-indigo-950/60 text-indigo-700 dark:text-indigo-300 font-semibold text-[12.5px] hover:bg-indigo-100 dark:hover:bg-indigo-900/60 transition-colors"
            >
              <span>View Recommended Jobs</span>
              <ChevronRight className="h-3.5 w-3.5" />
            </Link>
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={chartData}
              margin={{ top: 20, right: 8, left: -16, bottom: isMobile ? 18 : 0 }}
            >
              <XAxis
                dataKey="name"
                tickLine={false}
                axisLine={false}
                tickFormatter={formatStageLabel}
                angle={isMobile ? -20 : 0}
                textAnchor={isMobile ? 'end' : 'middle'}
                height={isMobile ? 34 : 24}
                tick={{ fontSize: isMobile ? 10 : 11, fill: '#334155', fontWeight: 600, fontFamily: 'Inter, sans-serif' }}
                interval={0}
              />
              <YAxis
                tickLine={false}
                axisLine={false}
                tick={{ fontSize: 11, fill: '#334155', fontWeight: 600, fontFamily: 'Inter, sans-serif' }}
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
              <Bar dataKey="count" radius={[5, 5, 0, 0]} maxBarSize={36} animationDuration={350} animationEasing="ease-out">
                {chartData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
                <LabelList
                  dataKey="count"
                  position="top"
                  style={{ fontSize: 11.5, fontWeight: 700, fill: '#1E293B', fontFamily: 'Inter, sans-serif' }}
                />
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
};

export default ApplicationStatusChart;

