import React from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  BarChart3,
  Compass,
  CheckSquare,
  Building2,
  Radar,
  Rocket,
  Settings,
} from 'lucide-react';

interface NavItem {
  name: string;
  path: string;
  icon: React.ElementType;
}

export const Sidebar: React.FC = () => {
  const location = useLocation();

  const navItems: NavItem[] = [
    { name: 'Dashboard', path: '/dashboard', icon: LayoutDashboard },
    { name: 'Analytics', path: '/analytics', icon: BarChart3 },
    { name: 'Job Feed', path: '/jobs', icon: Compass },
    { name: 'Applications', path: '/applications', icon: CheckSquare },
    { name: 'Companies', path: '/companies', icon: Building2 },
    { name: 'Discovery', path: '/discovery', icon: Radar },
    { name: 'Settings', path: '/settings', icon: Settings },
  ];

  return (
    <aside className="w-[240px] shrink-0 flex flex-col h-screen sticky top-0 border-r border-slate-200/90 dark:border-slate-800/90 bg-white dark:bg-[#0B0F17] select-none transition-all duration-300 ease-out z-20">
      {/* Brand Header: Icon + CareerPilot Only */}
      <div className="h-16 flex items-center px-5 border-b border-slate-200/80 dark:border-slate-800/80">
        <NavLink
          to="/"
          className="flex items-center gap-2.5 group transition-opacity duration-200 hover:opacity-90"
        >
          <div className="h-9 w-9 rounded-xl bg-gradient-to-br from-indigo-500 via-indigo-600 to-indigo-700 flex items-center justify-center text-white shadow-sm shrink-0 transition-transform duration-200 group-hover:scale-105">
            <Rocket className="h-4 w-4" />
          </div>

          <span className="font-bold text-[26px] tracking-tight text-slate-900 dark:text-white leading-none">
            CareerPilot
          </span>
        </NavLink>
      </div>

      {/* Navigation Links: Flat List with Refined SaaS Typography */}
      <div className="flex-1 overflow-y-auto px-3 py-3 space-y-1.5">
        {navItems.map((item) => {
          const Icon = item.icon;

          const isItemActive =
            item.path === '/dashboard'
              ? location.pathname === '/' ||
              location.pathname === '/dashboard' ||
              location.pathname.startsWith('/dashboard/')
              : location.pathname.startsWith(item.path);

          return (
            <NavLink
              key={item.path}
              to={item.path}
              className={`group flex items-center gap-3 px-3 py-[9px] rounded-lg text-[15px] transition-all duration-150 ease-out ${isItemActive
                ? 'bg-indigo-50 text-indigo-600 dark:bg-indigo-950/60 dark:text-indigo-400 font-semibold'
                : 'font-semibold text-slate-700 dark:text-slate-400 hover:text-indigo-600 dark:hover:text-indigo-400 hover:bg-indigo-50/70 dark:hover:bg-indigo-950/40'
                }`}
            >
              <Icon
                className={`h-[18px] w-[18px] shrink-0 transition-colors duration-150 ease-out ${isItemActive
                  ? 'text-indigo-600 dark:text-indigo-400'
                  : 'text-slate-500 dark:text-slate-300 group-hover:text-indigo-600 dark:group-hover:text-indigo-400'
                  }`}
              />

              <span className="transition-colors duration-200 ease-out">
                {item.name}
              </span>
            </NavLink>
          );
        })}
      </div>


    </aside>
  );
};

export default Sidebar;