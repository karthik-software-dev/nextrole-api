import React from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Compass,
  CheckSquare,
  Building2,
  Radar,
} from 'lucide-react';

interface NavCard {
  label: string;
  path: string;
  icon: React.ElementType;
  description: string;
}

const navCards: NavCard[] = [
  {
    label: 'Job Feed',
    path: '/jobs',
    icon: Compass,
    description: 'Browse and filter job listings',
  },
  {
    label: 'Applications',
    path: '/applications',
    icon: CheckSquare,
    description: 'Track your application pipeline',
  },
  {
    label: 'Companies',
    path: '/companies',
    icon: Building2,
    description: 'Explore target companies',
  },
  {
    label: 'Discovery',
    path: '/discovery',
    icon: Radar,
    description: 'Discover new opportunities',
  },
];

export const SettingsPage: React.FC = () => {
  const navigate = useNavigate();

  return (
    <div className="space-y-8 pb-16 max-w-6xl mx-auto">
      {/* Page Header */}
      <div>
        <h1 className="text-[28px] sm:text-[32px] font-bold tracking-tight text-slate-900 dark:text-white flex items-center gap-3">
          <span>Settings & Navigation</span>
        </h1>
        <p className="mt-1 text-[13.5px] text-slate-700 dark:text-slate-400">
          Quick shortcuts and navigation across the Job Agent platform.
        </p>
      </div>

      {/* Quick Nav Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {navCards.map((card) => {
          const Icon = card.icon;
          return (
            <button
              key={card.path}
              onClick={() => navigate(card.path)}
              className="group flex flex-col items-center justify-center gap-2.5 p-4 rounded-2xl border border-slate-200/80 dark:border-slate-800 bg-white dark:bg-[#111726] shadow-2xs hover:border-indigo-300 dark:hover:border-indigo-700/60 hover:shadow-xs transition-all duration-200 cursor-pointer"
            >
              <div className="h-10 w-10 rounded-xl bg-indigo-50 dark:bg-indigo-950/60 flex items-center justify-center group-hover:bg-indigo-100 dark:group-hover:bg-indigo-900/60 transition-colors">
                <Icon className="h-5 w-5 text-indigo-600 dark:text-indigo-400" />
              </div>
              <div className="text-center">
                <p className="text-[17px] font-bold text-slate-900 dark:text-white group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors">
                  {card.label}
                </p>
                <p className="text-[13px] text-slate-700 dark:text-slate-400">
                  {card.description}
                </p>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
};

export default SettingsPage;
