import React from 'react';

interface BadgeProps {
  children: React.ReactNode;
  variant?: 'tier1' | 'tier2' | 'tier3' | 'emerald' | 'amber' | 'blue' | 'indigo' | 'purple' | 'rose' | 'slate';
  size?: 'xs' | 'sm' | 'md';
  className?: string;
  dot?: boolean;
}

export const Badge: React.FC<BadgeProps> = ({
  children,
  variant = 'slate',
  size = 'sm',
  className = '',
  dot = false,
}) => {
  const sizeStyles = {
    xs: 'px-1.5 py-0.5 text-[10.5px] font-semibold',
    sm: 'px-2 py-0.5 text-[11.5px] font-semibold',
    md: 'px-2.5 py-1 text-[12px] font-semibold',
  };

  const variantStyles = {
    tier1: 'bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950/50 dark:text-emerald-400 dark:border-emerald-800/60',
    tier2: 'bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-950/50 dark:text-amber-400 dark:border-amber-800/60',
    tier3: 'bg-slate-100 text-slate-700 border-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:border-slate-700',
    emerald: 'bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950/50 dark:text-emerald-400 dark:border-emerald-800/60',
    amber: 'bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-950/50 dark:text-amber-400 dark:border-amber-800/60',
    blue: 'bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-950/50 dark:text-blue-400 dark:border-blue-800/60',
    indigo: 'bg-indigo-50 text-indigo-700 border-indigo-200 dark:bg-indigo-950/50 dark:text-indigo-400 dark:border-indigo-800/60',
    purple: 'bg-purple-50 text-purple-700 border-purple-200 dark:bg-purple-950/50 dark:text-purple-400 dark:border-purple-800/60',
    rose: 'bg-rose-50 text-rose-700 border-rose-200 dark:bg-rose-950/50 dark:text-rose-400 dark:border-rose-800/60',
    slate: 'bg-slate-100 text-slate-700 border-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:border-slate-700',
  };

  const dotStyles = {
    tier1: 'bg-emerald-500',
    tier2: 'bg-amber-500',
    tier3: 'bg-slate-400',
    emerald: 'bg-emerald-500',
    amber: 'bg-amber-500',
    blue: 'bg-blue-500',
    indigo: 'bg-indigo-500',
    purple: 'bg-purple-500',
    rose: 'bg-rose-500',
    slate: 'bg-slate-400',
  };

  return (
    <span
      className={`inline-flex items-center gap-1.5 whitespace-nowrap shrink-0 rounded-md border transition-colors ${sizeStyles[size]} ${variantStyles[variant]} ${className}`}
    >
      {dot && <span className={`h-1.5 w-1.5 rounded-full shrink-0 ${dotStyles[variant]}`} />}
      {children}
    </span>
  );
};

export const TierBadge: React.FC<{ tier: string; className?: string }> = ({ tier, className = '' }) => {
  const normalized = (tier || '').toLowerCase();
  if (normalized.includes('tier 1') || normalized.includes('tier1')) {
    return (
      <span
        className={`inline-flex items-center justify-center px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-gradient-to-r from-amber-500/20 via-amber-300/15 to-amber-500/20 text-amber-900 dark:text-amber-200 border border-amber-400/40 dark:border-amber-400/30 tracking-tight shadow-xs select-none ${className}`}
      >
        <span>Tier 1</span>
      </span>
    );
  }
  if (normalized.includes('tier 2') || normalized.includes('tier2')) {
    return (
      <span
        className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-slate-500/10 text-slate-600 dark:text-slate-400 border border-slate-500/20 select-none ${className}`}
      >
        <span className="h-1.5 w-1.5 rounded-full bg-slate-400 shrink-0" />
        <span>Tier 2</span>
      </span>
    );
  }
  return <Badge variant="tier3" className={className}>Tier 3</Badge>;
};

export const ApplicationStatusBadge: React.FC<{ status: string; size?: 'xs' | 'sm' | 'md'; className?: string }> = ({ status, size = 'sm', className }) => {
  const normalized = (status || '').toLowerCase().replace(/_/g, ' ');
  switch (normalized) {
    case 'offered':
    case 'offer':
      return <Badge variant="emerald" size={size} dot className={className}>Offered</Badge>;
    case 'interviewing':
    case 'interview':
      return <Badge variant="purple" size={size} dot className={className}>Interviewing</Badge>;
    case 'under review':
      return <Badge variant="blue" size={size} dot className={className}>Under Review</Badge>;
    case 'applied':
      return <Badge variant="indigo" size={size} dot className={className}>Applied</Badge>;
    case 'drafted':
    case 'saved':
      return <Badge variant="slate" size={size} dot className={className}>Saved / Draft</Badge>;
    case 'rejected':
      return <Badge variant="rose" size={size} dot className={className}>Rejected</Badge>;
    default:
      return <Badge variant="slate" size={size} className={className}>{status || 'Unknown'}</Badge>;
  }
};

export const MatchScoreBadge: React.FC<{ score: number; matchPercentage?: number; className?: string }> = ({ score, matchPercentage, className = '' }) => {
  // If matchPercentage provided by backend, use it; otherwise normalize raw 0-45 score to 0-100%
  const displayScore = matchPercentage ?? (score > 100 ? 100 : score <= 45 ? Math.min(100, Math.round((score / 35) * 100)) : Math.round(score));

  if (displayScore >= 80) {
    return (
      <span
        className={`inline-flex items-center px-2.5 py-0.5 rounded-md text-[11.5px] font-bold bg-emerald-100 text-emerald-800 dark:bg-emerald-950/80 dark:text-emerald-300 ring-1 ring-inset ring-emerald-600/30 select-none shadow-2xs ${className}`}
      >
        <span>{displayScore}% Match</span>
      </span>
    );
  }

  if (displayScore >= 65) {
    return (
      <span
        className={`inline-flex items-center px-2.5 py-0.5 rounded-md text-[11.5px] font-bold bg-indigo-100 text-indigo-800 dark:bg-indigo-950/80 dark:text-indigo-300 ring-1 ring-inset ring-indigo-600/30 select-none shadow-2xs ${className}`}
      >
        <span>{displayScore}% Match</span>
      </span>
    );
  }

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-md text-[11.5px] font-semibold bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300 ring-1 ring-inset ring-slate-400/20 select-none ${className}`}
    >
      <span>{displayScore}% Match</span>
    </span>
  );
};
