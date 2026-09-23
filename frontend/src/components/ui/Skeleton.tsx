import React from 'react';

export const Skeleton: React.FC<{ className?: string }> = ({ className = '' }) => {
  return (
    <div
      className={`animate-pulse rounded bg-slate-200 dark:bg-slate-800 ${className}`}
    />
  );
};

export const CardSkeleton: React.FC = () => {
  return (
    <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/60 p-5 shadow-sm space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <Skeleton className="h-10 w-10 rounded-lg" />
          <div className="space-y-1.5">
            <Skeleton className="h-4 w-36" />
            <Skeleton className="h-3 w-24" />
          </div>
        </div>
        <Skeleton className="h-6 w-16 rounded-full" />
      </div>
      <div className="flex gap-2">
        <Skeleton className="h-5 w-20 rounded" />
        <Skeleton className="h-5 w-16 rounded" />
        <Skeleton className="h-5 w-24 rounded" />
      </div>
      <div className="flex justify-between items-center pt-2 border-t border-slate-100 dark:border-slate-800/80">
        <Skeleton className="h-3 w-28" />
        <Skeleton className="h-8 w-24 rounded-lg" />
      </div>
    </div>
  );
};
