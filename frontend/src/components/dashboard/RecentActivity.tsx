import React from 'react';
import { Link } from 'react-router-dom';
import {
  Search,
  Plus,
  Send,
  Calendar,
  Sparkles,
  ArrowRight,
  Clock,
  Briefcase,
} from 'lucide-react';
import type { RecentActivityItem } from '../../types';

interface RecentActivityProps {
  activities?: RecentActivityItem[];
}

// Relative time formatting helper
const formatRelativeTime = (isoString?: string | null) => {
  if (!isoString) return 'Recently';
  try {
    const date = new Date(isoString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / (1000 * 60));
    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins} ${diffMins === 1 ? 'minute' : 'minutes'} ago`;
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours} ${diffHours === 1 ? 'hour' : 'hours'} ago`;
    const diffDays = Math.floor(diffHours / 24);
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 7) return `${diffDays} days ago`;
    return `${Math.floor(diffDays / 7)}w ago`;
  } catch {
    return 'Recently';
  }
};

const getActivityVisuals = (type: string) => {
  switch (type) {
    case 'discovery':
      return {
        icon: Search,
        bg: 'bg-blue-50 text-blue-700 dark:bg-blue-950/60 dark:text-blue-300',
      };
    case 'source':
      return {
        icon: Plus,
        bg: 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300',
      };
    case 'application':
      return {
        icon: Send,
        bg: 'bg-violet-50 text-violet-700 dark:bg-violet-950/60 dark:text-violet-300',
      };
    case 'interview':
      return {
        icon: Calendar,
        bg: 'bg-amber-50 text-amber-700 dark:bg-amber-950/60 dark:text-amber-300',
      };
    case 'offer':
      return {
        icon: Sparkles,
        bg: 'bg-teal-50 text-teal-700 dark:bg-teal-950/60 dark:text-teal-300',
      };
    default:
      return {
        icon: Briefcase,
        bg: 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300',
      };
  }
};

export const RecentActivity: React.FC<RecentActivityProps> = ({ activities }) => {
  const items = activities && activities.length > 0 ? activities : [];

  return (
    <div className="flex h-full flex-col overflow-hidden rounded-2xl border border-slate-200/80 bg-white shadow-sm dark:border-slate-800 dark:bg-[#111726]">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-100 px-6 py-5 dark:border-slate-800">
        <h3 className="text-[17px] font-bold tracking-tight text-slate-900 dark:text-white">
          Recent Activity
        </h3>
        <Link
          to="/applications"
          className="group inline-flex items-center gap-1 text-[13.5px] font-semibold text-indigo-600 hover:text-indigo-700 dark:text-indigo-400 dark:hover:text-indigo-300 transition-colors"
        >
          <span>View All</span>
          <ArrowRight className="h-3 w-3 transition-transform group-hover:translate-x-0.5" />
        </Link>
      </div>

      {/* Content */}
      <div className="flex-1 p-6">
        {items.length === 0 ? (
          <div className="flex h-full min-h-[240px] flex-col items-center justify-center gap-2 text-center text-slate-400">
            <Clock className="h-6 w-6 text-slate-300 dark:text-slate-600" />
            <p className="text-xs">No activity records recorded yet.</p>
          </div>
        ) : (
          <div className="relative space-y-6">
            {/* Timeline vertical connector thread */}
            {items.length > 1 && (
              <div className="absolute left-[15px] top-3.5 bottom-3.5 w-[2px] bg-slate-300 dark:bg-slate-800 pointer-events-none" />
            )}
            {items.map((item) => {
              const { icon: Icon, bg } = getActivityVisuals(item.activity_type);
              return (
                <div key={item.id} className="relative z-10 flex items-start gap-3.5">
                  <div
                    className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full ${bg} ring-4 ring-white dark:ring-[#111726] shadow-xs transition-transform hover:scale-105`}
                  >
                    <Icon className="h-4 w-4" />
                  </div>
                  <div className="min-w-0 flex-1 pt-0.5">
                    <p className="text-[14px] font-semibold text-slate-800 dark:text-slate-100">
                      {item.title}
                    </p>
                    <p className="mt-1 text-[12px] text-slate-600 dark:text-slate-500">
                      {formatRelativeTime(item.timestamp)}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};

export default RecentActivity;
