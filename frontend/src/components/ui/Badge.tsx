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

export const TierBadge: React.FC<{ tier: string; className?: string }> = ({ tier, className }) => {
  const normalized = (tier || '').toLowerCase();
  if (normalized.includes('tier 1') || normalized.includes('tier1')) {
    return <Badge variant="tier1" dot className={className}>Tier 1</Badge>;
  }
  if (normalized.includes('tier 2') || normalized.includes('tier2')) {
    return <Badge variant="tier2" dot className={className}>Tier 2</Badge>;
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

export const MatchScoreBadge: React.FC<{ score: number; className?: string }> = ({ score, className }) => {
  let variant: 'emerald' | 'indigo' | 'amber' | 'slate' = 'slate';
  if (score >= 85) variant = 'emerald';
  else if (score >= 70) variant = 'indigo';
  else if (score >= 50) variant = 'amber';

  return (
    <Badge variant={variant} size="xs" className={`font-semibold ${className}`}>
      {score}% Match
    </Badge>
  );
};
