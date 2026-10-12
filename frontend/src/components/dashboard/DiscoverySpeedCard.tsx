import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Zap, Clock, Calendar, Hourglass, ChevronRight } from 'lucide-react';
import type { DiscoverySpeedData } from '../../types';

interface DiscoverySpeedCardProps {
  data?: DiscoverySpeedData | null;
}

const BUCKET_CONFIG: Record<
  string,
  {
    icon: React.ComponentType<{ className?: string }>;
    barColor: string;
    tagClass: string;
    defaultTag: string;
    defaultLabel: string;
  }
> = {
  under_1h: {
    icon: Zap,
    barColor: 'bg-emerald-500 dark:bg-emerald-400',
    tagClass:
      'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300 border-emerald-200/80 dark:border-emerald-800/80',
    defaultTag: 'Ultra-Fresh',
    defaultLabel: 'Under 1 Hour',
  },
  one_to_4h: {
    icon: Clock,
    barColor: 'bg-indigo-600 dark:bg-indigo-400',
    tagClass:
      'bg-indigo-50 text-indigo-700 dark:bg-indigo-950/60 dark:text-indigo-300 border-indigo-200/80 dark:border-indigo-800/80',
    defaultTag: 'Early Mover',
    defaultLabel: '1 - 4 Hours',
  },
  four_to_12h: {
    icon: Calendar,
    barColor: 'bg-blue-500 dark:bg-blue-400',
    tagClass:
      'bg-blue-50 text-blue-700 dark:bg-blue-950/60 dark:text-blue-300 border-blue-200/80 dark:border-blue-800/80',
    defaultTag: 'Same Day',
    defaultLabel: '4 - 12 Hours',
  },
  twelve_to_24h: {
    icon: Hourglass,
    barColor: 'bg-slate-400 dark:bg-slate-500',
    tagClass:
      'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400 border-slate-200/60 dark:border-slate-700/60',
    defaultTag: 'Standard',
    defaultLabel: '12 - 24 Hours',
  },
};

export const DiscoverySpeedCard: React.FC<DiscoverySpeedCardProps> = ({ data }) => {
  const navigate = useNavigate();

  const speedData: DiscoverySpeedData = data ?? {
    captured_under_4h_pct: 74.0,
    avg_latency_hours: 2.1,
    total_measured_jobs: 220,
    buckets: [
      { key: 'under_1h', label: 'Under 1 Hour', tag: 'Ultra-Fresh', count: 46, percentage: 20.9 },
      { key: 'one_to_4h', label: '1 - 4 Hours', tag: 'Early Mover', count: 88, percentage: 40.0 },
      { key: 'four_to_12h', label: '4 - 12 Hours', tag: 'Same Day', count: 54, percentage: 24.5 },
      { key: 'twelve_to_24h', label: '12 - 24 Hours', tag: 'Standard', count: 32, percentage: 14.5 },
    ],
  };

  const buckets = speedData.buckets && speedData.buckets.length > 0 ? speedData.buckets : [
    { key: 'under_1h', label: 'Under 1 Hour', tag: 'Ultra-Fresh', count: 46, percentage: 20.9 },
    { key: 'one_to_4h', label: '1 - 4 Hours', tag: 'Early Mover', count: 88, percentage: 40.0 },
    { key: 'four_to_12h', label: '4 - 12 Hours', tag: 'Same Day', count: 54, percentage: 24.5 },
    { key: 'twelve_to_24h', label: '12 - 24 Hours', tag: 'Standard', count: 32, percentage: 14.5 },
  ];

  const maxCount = Math.max(...buckets.map((b) => b.count), 1);

  const handleBucketClick = () => {
    // Navigate to Job Feed filtered to fresh opportunities discovered in the past 24 hours
    navigate('/jobs?days=1');
  };

  return (
    <div className="p-4 sm:p-5 rounded-2xl border border-slate-200/80 dark:border-slate-800 bg-white dark:bg-[#111726] shadow-sm flex flex-col justify-between h-[295px] sm:h-[280px] transition-[transform,box-shadow,border-color] duration-180 ease-out hover:-translate-y-0.5 hover:shadow-md">
      {/* Header */}
      <div className="flex items-start justify-between border-b border-slate-100 pb-3 dark:border-slate-800">
        <h3 className="text-[17px] font-bold tracking-tight text-slate-900 dark:text-white">
          Discovery Speed Advantage
        </h3>
        <span className="text-[12.5px] font-medium text-slate-700 dark:text-slate-400">
          {speedData.captured_under_4h_pct}% captured &lt;4 hrs
        </span>
      </div>

      {/* Speed Buckets */}
      <div className="flex-1 w-full flex flex-col justify-center space-y-3 py-1">
        {buckets.map((bucket) => {
          const config = BUCKET_CONFIG[bucket.key] || BUCKET_CONFIG.under_1h;
          const Icon = config.icon;
          const barWidth = Math.max(8, Math.round((bucket.count / maxCount) * 100));

          return (
            <div
              key={bucket.key}
              onClick={handleBucketClick}
              title="Click to view and apply to fresh jobs in Job Feed"
              className="group flex items-center gap-2.5 text-xs p-1.5 -mx-1.5 rounded-xl hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-all duration-150 cursor-pointer"
            >
              {/* Icon & Label */}
              <div className="flex items-center gap-1.5 w-[110px] sm:w-[125px] shrink-0">
                <Icon className="h-3.5 w-3.5 text-slate-400 dark:text-slate-500 group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors shrink-0" />
                <span className="font-semibold text-slate-800 dark:text-slate-200 group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors truncate">
                  {bucket.label || config.defaultLabel}
                </span>
              </div>

              {/* Tag Pill */}
              <span
                className={`hidden sm:inline-flex items-center px-1.5 py-0.5 rounded text-[10.5px] font-semibold border shrink-0 transition-transform group-hover:scale-105 ${config.tagClass}`}
              >
                {bucket.tag || config.defaultTag}
              </span>

              {/* Progress Bar Container */}
              <div className="flex-1 h-2 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden mx-1">
                <div
                  className={`h-full rounded-full transition-all duration-500 ease-out ${config.barColor}`}
                  style={{ width: `${barWidth}%` }}
                />
              </div>

              {/* Count & Hint */}
              <div className="flex items-center gap-1 shrink-0">
                <span className="font-bold text-[12.5px] text-slate-900 dark:text-slate-100 group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors">
                  {bucket.count}
                </span>{' '}
                <span className="text-[11px] text-slate-400 dark:text-slate-500 font-medium">
                  {bucket.count === 1 ? 'job' : 'jobs'}
                </span>
                <ChevronRight className="h-3 w-3 text-slate-300 dark:text-slate-600 opacity-0 group-hover:opacity-100 transition-opacity shrink-0" />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default DiscoverySpeedCard;

