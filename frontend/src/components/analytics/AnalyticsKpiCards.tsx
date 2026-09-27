import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Send, Users, Percent, TrendingUp, ChevronRight } from 'lucide-react';
import type { AnalyticsKpiData } from '../../types';

interface AnalyticsKpiCardsProps {
  kpis?: AnalyticsKpiData;
}

export const AnalyticsKpiCards: React.FC<AnalyticsKpiCardsProps> = ({ kpis }) => {
  const navigate = useNavigate();

  const cards = [
    {
      id: 'applications',
      title: 'Applications',
      value: kpis?.applications ?? 0,
      suffix: '',
      subtext: kpis?.applications_subtext || 'Total applications submitted in period',
      icon: Send,
      color: 'text-indigo-600 dark:text-indigo-400',
      bg: 'bg-indigo-50 dark:bg-indigo-950/60',
      ring: 'ring-1 ring-inset ring-indigo-600/15 dark:ring-indigo-400/20',
      hoverColor: 'group-hover:text-indigo-600 dark:group-hover:text-indigo-400',
      action: () => navigate('/applications'),
    },
    {
      id: 'interviews',
      title: 'Interviews',
      value: kpis?.interviews ?? 0,
      suffix: '',
      subtext: kpis?.interviews_subtext || 'Applications reaching interview or offer stage',
      icon: Users,
      color: 'text-emerald-600 dark:text-emerald-400',
      bg: 'bg-emerald-50 dark:bg-emerald-950/60',
      ring: 'ring-1 ring-inset ring-emerald-600/15 dark:ring-emerald-400/20',
      hoverColor: 'group-hover:text-emerald-600 dark:group-hover:text-emerald-400',
      action: () => navigate('/applications?status=interviewing'),
    },
    {
      id: 'response-rate',
      title: 'Response Rate',
      value: kpis?.response_rate ?? 0.0,
      suffix: '%',
      subtext: kpis?.response_rate_subtext || 'Positive employer response rate (interview/offer)',
      icon: Percent,
      color: 'text-amber-600 dark:text-amber-400',
      bg: 'bg-amber-50 dark:bg-amber-950/60',
      ring: 'ring-1 ring-inset ring-amber-600/15 dark:ring-amber-400/20',
      hoverColor: 'group-hover:text-amber-600 dark:group-hover:text-amber-400',
      action: () => {},
    },
    {
      id: 'conversion-rate',
      title: 'Interview Conversion',
      value: kpis?.interview_conversion ?? 0.0,
      suffix: '%',
      subtext: kpis?.conversion_subtext || 'Interview-to-offer success rate',
      icon: TrendingUp,
      color: 'text-violet-600 dark:text-violet-400',
      bg: 'bg-violet-50 dark:bg-violet-950/60',
      ring: 'ring-1 ring-inset ring-violet-600/15 dark:ring-violet-400/20',
      hoverColor: 'group-hover:text-violet-600 dark:group-hover:text-violet-400',
      action: () => {},
    },
  ];

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {cards.map((c) => {
        const Icon = c.icon;

        return (
          <div
            key={c.id}
            onClick={c.action}
            className="group flex cursor-pointer items-center justify-between rounded-2xl border border-slate-200/80 bg-white p-[18px]
                 shadow-[0_1px_3px_rgba(0,0,0,0.03),0_1px_2px_rgba(0,0,0,0.02)]
                 transition-[transform,box-shadow,border-color] duration-200 ease-out
                 hover:-translate-y-0.5 hover:border-slate-300
                 hover:shadow-[0_6px_20px_rgba(0,0,0,0.05)]
                 dark:border-slate-800 dark:bg-[#111726] dark:hover:border-slate-700"
          >
            <div className="flex items-center gap-4 min-w-0">
              {/* Glyph Tile */}
              <div
                className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-xl ${c.bg} ${c.color} ${c.ring} shadow-xs`}
              >
                <Icon className="h-[18px] w-[18px]" />
              </div>

              <div className="min-w-0">
                <span className="text-[16.5px] font-semibold text-slate-800 dark:text-slate-200 block truncate">
                  {c.title}
                </span>

                <p className="mt-1 text-[36px] font-semibold leading-none tracking-tight text-slate-900 dark:text-white">
                  {c.value}
                  {c.suffix}
                </p>

                <p className="mt-1.5 truncate text-[12px] font-medium text-slate-700 dark:text-slate-300">
                  {c.subtext}
                </p>
              </div>
            </div>

            <ChevronRight
              className={`h-4 w-4 shrink-0 text-slate-400 transition-all duration-200
                   group-hover:translate-x-0.5 ${c.hoverColor} ml-2`}
            />
          </div>
        );
      })}
    </div>
  );
};
