import React from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  BarChart3,
  Compass,
  CheckSquare,
  Building2,
  Radar,
  Settings,
  X,
  Sun,
  Moon,
} from 'lucide-react';
import { useTheme } from '../../context/ThemeContext';
import { useDiscovery } from '../../context/DiscoveryContext';
import { useAuth } from '../../context/AuthContext';
import { getSettings } from '../../api/settings';

interface NavItem {
  name: string;
  path: string;
  icon: React.ElementType;
}

export interface SidebarProps {
  isMobileOpen?: boolean;
  onMobileClose?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ isMobileOpen, onMobileClose }) => {
  const location = useLocation();
  const { theme, toggleTheme } = useTheme();
  const { lastRunAt } = useDiscovery();
  const { user } = useAuth();
  const [userName, setUserName] = React.useState('Rahul Karthik');

  React.useEffect(() => {
    let isMounted = true;
    getSettings()
      .then((data) => {
        if (isMounted && data?.profile?.name) {
          setUserName(data.profile.name);
        }
      })
      .catch(() => { });
    return () => {

      isMounted = false;
    };
  }, []);

  const navItems: NavItem[] = [
    { name: 'Dashboard', path: '/dashboard', icon: LayoutDashboard },
    { name: 'Analytics', path: '/analytics', icon: BarChart3 },
    { name: 'Job Feed', path: '/jobs', icon: Compass },
    { name: 'Applications', path: '/applications', icon: CheckSquare },
    { name: 'Companies', path: '/companies', icon: Building2 },
    { name: 'Discovery', path: '/discovery', icon: Radar },
    { name: 'Settings', path: '/settings', icon: Settings },
  ];

  const renderNavLinks = (isMobile = false) => (
    <div className="flex-1 overflow-y-auto px-3 py-3 space-y-1.5 butter-scroll">
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
            onClick={() => {
              if (isMobile && onMobileClose) {
                onMobileClose();
              }
            }}
            className={`group flex items-center gap-3 px-3 py-[9px] rounded-lg text-[15px] transition-all duration-150 ease-out active-pop ${isItemActive
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
  );

  return (
    <>
      {/* 1. Desktop Persistent Sidebar */}
      <aside className="hidden md:flex w-[240px] shrink-0 flex-col h-screen sticky top-0 border-r border-slate-200/90 dark:border-slate-800/90 bg-white dark:bg-[#0B0F17] select-none transition-all duration-300 ease-out z-20">
        {/* Brand Header: NextRole */}
        <div className="h-16 flex items-center px-5 border-b border-slate-200/80 dark:border-slate-800/80">
          <NavLink
            to="/"
            className="flex items-center gap-2.5 group transition-opacity duration-200 hover:opacity-90"
          >
            <img
              src="/nextrole-icon.png"
              alt="NextRole"
              className="h-[37px] w-[37px] object-contain rounded-xl shrink-0 transition-transform duration-200 group-hover:scale-105"
              style={{ width: '37px', height: '37px' }}
            />
            <span className="text-[25px] font-bold tracking-tight leading-none inline-flex items-center whitespace-nowrap select-none">
              <span className="text-slate-900 dark:text-white">Next</span>
              <span className="bg-gradient-to-r from-indigo-600 to-violet-600 dark:from-indigo-400 dark:to-violet-400 bg-clip-text text-transparent">Role</span>
            </span>
          </NavLink>
        </div>

        {/* Navigation Links */}
        {renderNavLinks(false)}
      </aside>

      {/* 2. Mobile Slide-Over Drawer with Backdrop */}
      {isMobileOpen && (
        <div className="md:hidden fixed inset-0 z-50 flex">
          {/* Backdrop Blur Overlay */}
          <div
            className="fixed inset-0 bg-slate-900/60 backdrop-blur-md transition-opacity animate-in fade-in duration-260 cursor-pointer"
            onClick={onMobileClose}
            aria-hidden="true"
          />

          {/* Drawer Sidebar Panel */}
          <aside className="relative flex flex-col w-[280px] max-w-[85vw] h-full bg-white dark:bg-[#0B0F17] border-r border-slate-200/90 dark:border-slate-800/90 shadow-2xl z-10 animate-in slide-in-from-left duration-300 ease-[cubic-bezier(0.2,0.95,0.2,1)] will-change-transform select-none">
            {/* Header: Logo + Close Button */}
            <div className="h-16 flex items-center justify-between px-4 border-b border-slate-200/80 dark:border-slate-800/80">
              <NavLink
                to="/"
                onClick={onMobileClose}
                className="flex items-center gap-2.5 group transition-opacity hover:opacity-90"
              >
                <img
                  src="/nextrole-icon.png"
                  alt="NextRole"
                  className="h-[35px] w-[35px] object-contain rounded-xl shrink-0"
                  style={{ width: '35px', height: '35px' }}
                />
                <span className="text-[24px] font-bold tracking-tight leading-none inline-flex items-center whitespace-nowrap select-none">
                  <span className="text-slate-900 dark:text-white">Next</span>
                  <span className="bg-gradient-to-r from-indigo-600 to-violet-600 dark:from-indigo-400 dark:to-violet-400 bg-clip-text text-transparent">Role</span>
                </span>
              </NavLink>

              <button
                type="button"
                onClick={onMobileClose}
                className="p-1.5 rounded-lg text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-100 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors cursor-pointer"
                aria-label="Close navigation"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Navigation Links */}
            {renderNavLinks(true)}

            {/* Mobile Drawer Footer: Sync Status + User Profile + Theme Toggle */}
            <div className="mt-auto border-t border-slate-200/80 dark:border-slate-800/80 bg-slate-50/60 dark:bg-slate-900/40 p-3.5 space-y-2.5 shrink-0">
              {/* Engine Sync Indicator */}
              <div className="flex items-center justify-between px-1">
                <div className="flex items-center gap-1.5 text-[11.5px] text-slate-500 dark:text-slate-400 font-medium">
                  <span className="relative flex h-2 w-2">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
                  </span>
                  <span>Last sync: <strong className="text-slate-700 dark:text-slate-300 font-semibold">{lastRunAt || 'Recent'}</strong></span>
                </div>
              </div>

              {/* User Profile Card & Theme Switcher */}
              <div className="flex items-center justify-between gap-2 pt-2 border-t border-slate-200/60 dark:border-slate-800/60">
                <NavLink
                  to="/settings"
                  onClick={onMobileClose}
                  className="flex items-center gap-2.5 min-w-0 flex-1 p-1 -ml-1 rounded-xl hover:bg-slate-200/60 dark:hover:bg-slate-800/60 transition-colors group cursor-pointer"
                  title="Open Settings"
                >
                  <div className="h-8 w-8 rounded-full bg-indigo-100 dark:bg-indigo-950/80 text-indigo-700 dark:text-indigo-300 font-bold text-xs flex items-center justify-center border border-indigo-200/80 dark:border-indigo-800/60 shadow-2xs shrink-0 group-hover:scale-105 transition-transform">
                    {(user?.name || userName).charAt(0).toUpperCase()}
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-[13px] font-bold text-slate-900 dark:text-slate-100 truncate leading-tight group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors">
                      {(user?.name || userName).split(' ')[0]}
                    </p>

                    <p className="text-[10.5px] text-slate-500 dark:text-slate-400 truncate leading-tight">
                      Account Settings
                    </p>
                  </div>
                </NavLink>

                <button
                  type="button"
                  onClick={toggleTheme}
                  className="h-10 w-10 rounded-xl flex items-center justify-center text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white bg-white dark:bg-slate-800 border border-slate-200/80 dark:border-slate-700/80 shadow-2xs hover:shadow-xs transition-all active-pop cursor-pointer shrink-0"
                  aria-label="Toggle theme"
                  title={theme === 'dark' ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
                >
                  {theme === 'dark' ? <Sun className="h-4 w-4 text-amber-400" /> : <Moon className="h-4 w-4 text-slate-600" />}
                </button>
              </div>
            </div>
          </aside>
        </div>
      )}
    </>
  );
};

export default Sidebar;