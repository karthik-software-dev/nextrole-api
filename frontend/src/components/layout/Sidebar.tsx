import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Compass,
  CheckSquare,
  Building2,
  Radar,
  Settings,
  Rocket,
  Sprout,
} from 'lucide-react';

interface NavItem {
  name: string;
  path: string;
  icon: React.ElementType;
}

export const Sidebar: React.FC = () => {
  const navItems: NavItem[] = [
    { name: 'Dashboard', path: '/', icon: LayoutDashboard },
    { name: 'Job Feed', path: '/jobs', icon: Compass },
    { name: 'Applications', path: '/applications', icon: CheckSquare },
    { name: 'Companies', path: '/companies', icon: Building2 },
    { name: 'Discovery', path: '/discovery', icon: Radar },
    { name: 'Settings', path: '/settings', icon: Settings },
  ];

  return (
    <aside className="w-[230px] shrink-0 flex flex-col h-screen sticky top-0 border-r border-slate-200 dark:border-slate-800 bg-white dark:bg-[#0B0F17] select-none transition-colors">
      {/* Brand Header */}
      <div className="h-16 flex items-center px-5 border-b border-slate-200 dark:border-slate-800">
        <NavLink to="/" className="flex items-center gap-2.5 group">
          <div className="h-8 w-8 rounded-lg bg-blue-600 flex items-center justify-center text-white shadow-xs">
            <Rocket className="h-4 w-4" />
          </div>
          <div>
            <span className="font-bold text-[15px] tracking-tight text-slate-900 dark:text-white block leading-none">
              CareerPilot
            </span>
            <span className="text-[10px] text-slate-400 dark:text-slate-500 font-medium block mt-1 leading-none">
              AI Job Intelligence CRM
            </span>
          </div>
        </NavLink>
      </div>

      {/* Navigation Links */}
      <div className="flex-1 overflow-y-auto px-3 py-4 space-y-1">
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.path === '/'}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-[13px] font-medium transition-colors ${
                  isActive
                    ? 'bg-blue-50 text-blue-600 dark:bg-blue-950/50 dark:text-blue-400 font-semibold'
                    : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100 hover:bg-slate-50 dark:hover:bg-slate-800/40'
                }`
              }
            >
              <Icon className="h-4 w-4 shrink-0" />
              <span>{item.name}</span>
            </NavLink>
          );
        })}
      </div>

      {/* Bottom Motivational Card */}
      <div className="p-3 m-3 rounded-xl bg-slate-50 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800">
        <div className="flex items-center gap-2 mb-1.5">
          <div className="h-6 w-6 rounded-lg bg-emerald-50 dark:bg-emerald-950/60 flex items-center justify-center text-emerald-600 dark:text-emerald-400">
            <Sprout className="h-3.5 w-3.5" />
          </div>
          <p className="text-xs font-bold text-slate-800 dark:text-slate-200">
            Stay consistent
          </p>
        </div>
        <p className="text-[11px] text-slate-500 dark:text-slate-400 leading-relaxed">
          Small steps lead to big opportunities.
        </p>
      </div>
    </aside>
  );
};

export default Sidebar;
