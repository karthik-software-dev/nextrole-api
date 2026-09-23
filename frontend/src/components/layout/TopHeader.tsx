import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, Sun, Moon, Bell, Play, Loader2, ChevronDown } from 'lucide-react';
import { useTheme } from '../../context/ThemeContext';
import { useDiscovery } from '../../context/DiscoveryContext';

interface TopHeaderProps {
  onSearch?: (term: string) => void;
}

export const TopHeader: React.FC<TopHeaderProps> = ({ onSearch }) => {
  const { theme, toggleTheme } = useTheme();
  const { isDiscovering, discoveryStatusText, runDiscovery } = useDiscovery();
  const navigate = useNavigate();
  const [searchTerm, setSearchTerm] = useState('');

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (onSearch) {
      onSearch(searchTerm);
    } else {
      navigate(`/jobs?search=${encodeURIComponent(searchTerm)}`);
    }
  };

  const handleRunDiscovery = () => {
    navigate('/discovery');
    runDiscovery();
  };

  return (
    <header className="h-16 shrink-0 border-b border-slate-200 dark:border-slate-800 bg-white dark:bg-[#0B0F17] px-6 flex items-center justify-between sticky top-0 z-20 transition-colors">
      {/* Search Input (around 400px) */}
      <div className="w-full max-w-[400px]">
        <form onSubmit={handleSearchSubmit} className="relative">
          <Search className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
          <input
            type="text"
            placeholder="Search jobs, companies..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg pl-9 pr-4 py-1.5 text-xs text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:border-blue-500 focus:bg-white dark:focus:bg-slate-900 transition-all"
          />
        </form>
      </div>

      {/* Right Controls & Profile */}
      <div className="flex items-center gap-3">
        {/* Run Discovery Action */}
        <button
          onClick={handleRunDiscovery}
          disabled={isDiscovering}
          className="hidden sm:inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-blue-50 hover:bg-blue-100 dark:bg-blue-950/60 dark:hover:bg-blue-900/60 text-blue-600 dark:text-blue-400 border border-blue-200 dark:border-blue-800/80 transition-colors disabled:opacity-60 disabled:cursor-not-allowed cursor-pointer"
          title={isDiscovering ? 'Discovery is in progress...' : 'Run discovery pipeline across all sources'}
        >
          {isDiscovering ? (
            <Loader2 className="h-3 w-3 animate-spin" />
          ) : (
            <Play className="h-3 w-3 fill-blue-600 text-blue-600 dark:fill-blue-400 dark:text-blue-400" />
          )}
          <span>{isDiscovering ? (discoveryStatusText || 'Discovering...') : 'Run Discovery'}</span>
        </button>

        {/* Theme Toggle */}
        <button
          onClick={toggleTheme}
          className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors cursor-pointer"
          aria-label="Toggle theme"
        >
          {theme === 'dark' ? <Sun className="h-4 w-4 text-amber-400" /> : <Moon className="h-4 w-4 text-slate-500" />}
        </button>

        {/* Notification Bell */}
        <button
          className="relative p-1.5 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors cursor-pointer"
          title="Notifications"
        >
          <Bell className="h-4 w-4" />
          <span className="absolute top-1 right-1 h-2 w-2 rounded-full bg-rose-500" />
        </button>

        <div className="h-5 w-px bg-slate-200 dark:border-slate-800 hidden sm:block" />

        {/* User Profile */}
        <div className="flex items-center gap-2 cursor-pointer select-none">
          <div className="h-8 w-8 rounded-full bg-blue-100 dark:bg-blue-950 text-blue-700 dark:text-blue-300 font-bold text-xs flex items-center justify-center border border-blue-200 dark:border-blue-800/60">
            KR
          </div>
          <span className="text-xs font-semibold text-slate-800 dark:text-slate-200 hidden md:inline-block">
            Karthik
          </span>
          <ChevronDown className="h-3.5 w-3.5 text-slate-400 hidden md:inline-block" />
        </div>
      </div>
    </header>
  );
};
