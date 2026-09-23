import React, { useState } from 'react';

interface CompanyAvatarProps {
  name: string;
  logoUrl?: string | null;
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl';
  className?: string;
}

const COLOR_PALETTES = [
  'bg-indigo-600 text-white',
  'bg-emerald-600 text-white',
  'bg-violet-600 text-white',
  'bg-blue-600 text-white',
  'bg-amber-600 text-white',
  'bg-rose-600 text-white',
  'bg-teal-600 text-white',
  'bg-cyan-600 text-white',
  'bg-fuchsia-600 text-white',
];

export const CompanyAvatar: React.FC<CompanyAvatarProps> = ({
  name,
  logoUrl,
  size = 'md',
  className = '',
}) => {
  const [imageError, setImageError] = useState(false);

  const cleanName = (name || 'Company').trim();
  const monogram = cleanName
    .split(/\s+/)
    .slice(0, 2)
    .map((w) => w[0]?.toUpperCase() || '')
    .join('') || cleanName.slice(0, 2).toUpperCase();

  // Deterministic color selection
  let hash = 0;
  for (let i = 0; i < cleanName.length; i++) {
    hash = cleanName.charCodeAt(i) + ((hash << 5) - hash);
  }
  const colorIndex = Math.abs(hash) % COLOR_PALETTES.length;
  const colorClass = COLOR_PALETTES[colorIndex];

  const sizeStyles = {
    xs: 'h-6 w-6 text-[10px] rounded',
    sm: 'h-8 w-8 text-xs rounded-md',
    md: 'h-10 w-10 text-sm rounded-lg font-semibold',
    lg: 'h-12 w-12 text-base rounded-xl font-semibold',
    xl: 'h-16 w-16 text-xl rounded-2xl font-bold',
  };

  if (logoUrl && !imageError) {
    return (
      <img
        src={logoUrl}
        alt={`${cleanName} logo`}
        onError={() => setImageError(true)}
        className={`${sizeStyles[size]} object-cover border border-slate-200 dark:border-slate-700 ${className}`}
      />
    );
  }

  return (
    <div
      className={`flex items-center justify-center shrink-0 tracking-tight shadow-xs ${sizeStyles[size]} ${colorClass} ${className}`}
    >
      {monogram}
    </div>
  );
};
