import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Search,
  Sun,
  Moon,
  Bell,
  Play,
  Loader2,
  ChevronDown,
  X,
  CheckCheck,
  Radar,
  Briefcase,
  CheckSquare,
  Sparkles,
  ArrowRight,
} from 'lucide-react';
import { useTheme } from '../../context/ThemeContext';
import { useDiscovery } from '../../context/DiscoveryContext';
import { getNotifications, markNotificationRead, markAllNotificationsRead } from '../../api';
import { getSettings } from '../../api/settings';
import type { NotificationItem } from '../../types';

interface TopHeaderProps {
  onSearch?: (term: string) => void;
}

export const TopHeader: React.FC<TopHeaderProps> = ({ onSearch }) => {
  const { theme, toggleTheme } = useTheme();
  const { isDiscovering, discoveryStatusText, runDiscovery, lastRunAt, useCache } = useDiscovery();
  const navigate = useNavigate();

  const [searchTerm, setSearchTerm] = useState('');
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [isNotifOpen, setIsNotifOpen] = useState(false);
  const [isLoadingNotifs, setIsLoadingNotifs] = useState(false);
  const [userName, setUserName] = useState('Karthik');

  const notifRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let isMounted = true;
    getSettings()
      .then((data) => {
        if (isMounted && data?.profile?.name) {
          setUserName(data.profile.name);
        }
      })
      .catch((err) => {
        console.warn('Failed to load user profile in header:', err);
      });
    return () => {
      isMounted = false;
    };
  }, []);

  // Fetch notifications from real backend API
  const fetchNotifs = async () => {
    try {
      setIsLoadingNotifs(true);
      const res = await getNotifications(20);
      setNotifications(res.items);
      setUnreadCount(res.unread_count);
    } catch (err) {
      console.error('Failed to fetch notifications:', err);
    } finally {
      setIsLoadingNotifs(false);
    }
  };

  // Initial load + refresh when discovery runs or finishes
  useEffect(() => {
    fetchNotifs();
  }, [lastRunAt, isDiscovering]);

  // Polling every 25 seconds for dynamic background events
  useEffect(() => {
    const timer = setInterval(() => {
      fetchNotifs();
    }, 25000);
    return () => clearInterval(timer);
  }, []);

  // Close notifications popover on click outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (notifRef.current && !notifRef.current.contains(e.target as Node)) {
        setIsNotifOpen(false);
      }
    };
    if (isNotifOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isNotifOpen]);

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

  const handleMarkAllRead = async () => {
    try {
      await markAllNotificationsRead();
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
      setUnreadCount(0);
    } catch (err) {
      console.error('Failed to mark all as read:', err);
    }
  };

  const handleNotificationClick = async (item: NotificationItem) => {
    try {
      if (!item.is_read) {
        await markNotificationRead(item.id);
        setNotifications((prev) =>
          prev.map((n) => (n.id === item.id ? { ...n, is_read: true } : n))
        );
        setUnreadCount((c) => Math.max(0, c - 1));
      }
      setIsNotifOpen(false);
      if (item.link) {
        navigate(item.link);
      }
    } catch (err) {
      console.error('Failed to mark notification read:', err);
    }
  };

  const formatTimeAgo = (dateStr: string) => {
    try {
      const d = new Date(dateStr);
      const now = new Date();
      const diffSec = Math.floor((now.getTime() - d.getTime()) / 1000);
      if (diffSec < 60) return 'Just now';
      const diffMin = Math.floor(diffSec / 60);
      if (diffMin < 60) return `${diffMin}m ago`;
      const diffHr = Math.floor(diffMin / 60);
      if (diffHr < 24) return `${diffHr}h ago`;
      const diffDays = Math.floor(diffHr / 24);
      return `${diffDays}d ago`;
    } catch {
      return '';
    }
  };

  const getNotificationIcon = (type: string) => {
    switch (type) {
      case 'discovery':
        return (
          <div className="h-9 w-9 rounded-xl bg-indigo-50 dark:bg-indigo-950/70 border border-indigo-200/60 dark:border-indigo-800/60 ring-1 ring-inset ring-indigo-300/20 dark:ring-indigo-700/20 flex items-center justify-center shrink-0 shadow-xs">
            <Radar className="h-4 w-4 text-indigo-600 dark:text-indigo-400" />
          </div>
        );
      case 'job':
        return (
          <div className="h-9 w-9 rounded-xl bg-emerald-50 dark:bg-emerald-950/70 border border-emerald-200/60 dark:border-emerald-800/60 ring-1 ring-inset ring-emerald-300/20 dark:ring-emerald-700/20 flex items-center justify-center shrink-0 shadow-xs">
            <Briefcase className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
          </div>
        );
      case 'application':
        return (
          <div className="h-9 w-9 rounded-xl bg-amber-50 dark:bg-amber-950/70 border border-amber-200/60 dark:border-amber-800/60 ring-1 ring-inset ring-amber-300/20 dark:ring-amber-700/20 flex items-center justify-center shrink-0 shadow-xs">
            <CheckSquare className="h-4 w-4 text-amber-600 dark:text-amber-400" />
          </div>
        );
      default:
        return (
          <div className="h-9 w-9 rounded-xl bg-purple-50 dark:bg-purple-950/70 border border-purple-200/60 dark:border-purple-800/60 ring-1 ring-inset ring-purple-300/20 dark:ring-purple-700/20 flex items-center justify-center shrink-0 shadow-xs">
            <Sparkles className="h-4 w-4 text-purple-600 dark:text-purple-400" />
          </div>
        );
    }
  };

  return (
    <header className="h-16 shrink-0 border-b border-slate-200 dark:border-slate-800 bg-white dark:bg-[#0B0F17] px-6 flex items-center justify-between sticky top-0 z-30 transition-colors">
      {/* Search Input (around 400px) */}
      <div className="w-full max-w-[400px]">
        <form onSubmit={handleSearchSubmit} className="relative">
          <div className="group relative flex items-center p-0.5 rounded-xl border border-slate-200/90 dark:border-slate-700/80 bg-slate-50/70 dark:bg-slate-900/50 shadow-2xs hover:border-slate-300 dark:hover:border-slate-600 focus-within:border-indigo-500 dark:focus-within:border-indigo-500 focus-within:bg-white dark:focus-within:bg-[#0f1422] focus-within:ring-4 focus-within:ring-indigo-500/15 focus-within:shadow-md focus-within:shadow-indigo-500/5 transition-all duration-300 ease-out">
            <Search className="h-4 w-4 ml-2.5 text-slate-600 dark:text-slate-300 group-focus-within:text-indigo-600 dark:group-focus-within:text-indigo-400 group-focus-within:scale-110 transition-all duration-300 ease-out shrink-0" />
            <input
              type="text"
              placeholder="Search jobs, companies..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full h-8 bg-transparent border-0 px-2.5 text-[13.5px] text-slate-900 dark:text-slate-100 placeholder:text-slate-700 dark:placeholder:text-slate-300 font-medium focus:outline-none focus:ring-0 leading-normal"
            />
            {searchTerm && (
              <button
                type="button"
                onClick={() => setSearchTerm('')}
                className="p-1 mr-1 rounded-md text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-200/60 dark:hover:bg-slate-800 transition-colors cursor-pointer animate-in fade-in zoom-in-90"
                title="Clear search"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            )}
          </div>
        </form>
      </div>

      {/* Right Controls & Profile */}
      <div className="flex items-center gap-2 sm:gap-3 shrink-0">
        {/* Run Discovery Action */}
        <button
          onClick={handleRunDiscovery}
          disabled={isDiscovering}
          className="hidden sm:inline-flex items-center gap-2 px-3 py-1.5 text-[12.5px] font-semibold rounded-xl bg-indigo-50 hover:bg-indigo-100 dark:bg-indigo-950/60 dark:hover:bg-indigo-900/60 text-indigo-600 dark:text-indigo-400 border border-indigo-200/80 dark:border-indigo-800/80 shadow-2xs hover:shadow-xs transition-all disabled:opacity-60 disabled:cursor-not-allowed cursor-pointer shrink-0"
          title={
            isDiscovering
              ? 'Discovery is in progress...'
              : `Run discovery pipeline (${useCache ? 'Test Cache Mode' : 'Real-Time Live Mode'})`
          }
        >
          {isDiscovering ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : (
            <Play className="h-3.5 w-3.5 fill-indigo-600 text-indigo-600 dark:fill-indigo-400 dark:text-indigo-400" />
          )}
          <span>{isDiscovering ? (discoveryStatusText || 'Discovering...') : 'Run Discovery'}</span>

          {!isDiscovering && (
            <span
              className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md text-[10px] font-extrabold tracking-wide uppercase transition-colors ${
                useCache
                  ? 'bg-amber-100/90 text-amber-800 dark:bg-amber-950/80 dark:text-amber-300 border border-amber-300/80 dark:border-amber-800/60'
                  : 'bg-emerald-100/90 text-emerald-800 dark:bg-emerald-950/80 dark:text-emerald-300 border border-emerald-300/80 dark:border-emerald-800/60'
              }`}
            >
              <span
                className={`h-1.5 w-1.5 rounded-full ${
                  useCache ? 'bg-amber-500' : 'bg-emerald-500 animate-pulse'
                }`}
              />
              {useCache ? 'Cache' : 'Live'}
            </span>
          )}
        </button>

        {/* Theme Toggle */}
        <button
          onClick={toggleTheme}
          className="h-9 w-9 rounded-xl flex items-center justify-center text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800/80 transition-colors cursor-pointer shrink-0"
          aria-label="Toggle theme"
        >
          {theme === 'dark' ? <Sun className="h-4 w-4 text-amber-400" /> : <Moon className="h-4 w-4 text-slate-500" />}
        </button>

        {/* Notification Bell Dropdown Container */}
        <div className="relative shrink-0" ref={notifRef}>
          <button
            onClick={() => {
              setIsNotifOpen(!isNotifOpen);
              if (!isNotifOpen) fetchNotifs();
            }}
            className="h-9 w-9 rounded-xl flex items-center justify-center text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800/80 transition-colors cursor-pointer relative shrink-0"
            title="Notifications"
            aria-label="Notifications"
          >
            <Bell className="h-4 w-4" />
            {unreadCount > 0 && (
              <span className="absolute top-0.5 right-0.5 flex h-3.5 min-w-3.5 px-1 items-center justify-center rounded-full bg-rose-500 text-white text-[9px] font-bold ring-2 ring-white dark:ring-[#0B0F17] animate-in zoom-in-50 duration-200">
                {unreadCount > 9 ? '9+' : unreadCount}
              </span>
            )}
          </button>

          {/* Premium Notifications Popover */}
          {isNotifOpen && (
            <div className="absolute right-0 mt-2.5 w-[380px] sm:w-[420px] max-w-[calc(100vw-1.5rem)] rounded-2xl border border-slate-200/80 dark:border-slate-700/60 bg-white/95 dark:bg-[#0f1422]/95 backdrop-blur-xl shadow-[0_20px_60px_-10px_rgba(0,0,0,0.15),0_8px_24px_-4px_rgba(0,0,0,0.08)] dark:shadow-[0_20px_60px_-10px_rgba(0,0,0,0.5),0_8px_24px_-4px_rgba(0,0,0,0.3)] z-50 overflow-hidden menu-reveal">

              {/* Popover Header */}
              <div className="px-5 py-4 border-b border-slate-100 dark:border-slate-800/70 flex items-center justify-between bg-gradient-to-r from-slate-50/80 to-white/60 dark:from-slate-900/60 dark:to-slate-900/30">
                <div className="flex items-center gap-2.5">
                  <div className="h-7 w-7 rounded-lg bg-indigo-50 dark:bg-indigo-950/60 border border-indigo-100 dark:border-indigo-900/60 flex items-center justify-center">
                    <Bell className="h-3.5 w-3.5 text-indigo-600 dark:text-indigo-400" />
                  </div>
                  <h3 className="text-[15px] font-bold text-slate-900 dark:text-white tracking-tight">
                    Notifications
                  </h3>
                  {unreadCount > 0 && (
                    <span className="px-2 py-0.5 rounded-full text-[11px] font-bold bg-indigo-600 dark:bg-indigo-500 text-white shadow-xs shadow-indigo-500/30">
                      {unreadCount}
                    </span>
                  )}
                </div>

                {unreadCount > 0 && (
                  <button
                    onClick={handleMarkAllRead}
                    className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-[12px] font-semibold text-indigo-600 hover:text-indigo-700 dark:text-indigo-400 dark:hover:text-indigo-300 hover:bg-indigo-50 dark:hover:bg-indigo-950/60 transition-all cursor-pointer"
                  >
                    <CheckCheck className="h-3.5 w-3.5" />
                    <span>Mark all read</span>
                  </button>
                )}
              </div>

              {/* Popover List */}
              <div className="max-h-[400px] overflow-y-auto scrollbar-thin scrollbar-thumb-slate-200 dark:scrollbar-thumb-slate-700 p-2 space-y-1">
                {isLoadingNotifs && notifications.length === 0 ? (
                  <div className="flex flex-col items-center justify-center py-12 text-slate-400 gap-3">
                    <Loader2 className="h-5 w-5 animate-spin text-indigo-600" />
                    <span className="text-[13px] font-medium text-slate-500 dark:text-slate-400">Checking for updates...</span>
                  </div>
                ) : notifications.length === 0 ? (
                  <div className="flex flex-col items-center justify-center py-12 px-6 text-center">
                    <div className="h-12 w-12 rounded-2xl bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 flex items-center justify-center mb-3 text-slate-400">
                      <Bell className="h-5 w-5" />
                    </div>
                    <p className="text-[14px] font-bold text-slate-800 dark:text-slate-200">
                      All caught up
                    </p>
                    <p className="text-[12.5px] text-slate-500 dark:text-slate-400 mt-1 leading-relaxed">
                      Job scraper alerts and application updates will appear here.
                    </p>
                  </div>
                ) : (
                  notifications.map((item) => (
                    <div
                      key={item.id}
                      onClick={() => handleNotificationClick(item)}
                      className={`relative flex items-start gap-3.5 p-3.5 rounded-xl cursor-pointer group transition-all duration-150 ${
                        !item.is_read
                          ? 'bg-indigo-50/70 dark:bg-indigo-950/30 border border-indigo-100/80 dark:border-indigo-800/40 hover:bg-indigo-50 dark:hover:bg-indigo-950/50 hover:border-indigo-200 dark:hover:border-indigo-700/60'
                          : 'hover:bg-slate-50/90 dark:hover:bg-slate-800/50 border border-transparent hover:border-slate-200/60 dark:hover:border-slate-700/50'
                      }`}
                    >
                      {/* Unread left accent bar */}
                      {!item.is_read && (
                        <div className="absolute left-0 top-3 bottom-3 w-[3px] rounded-full bg-indigo-500 dark:bg-indigo-400" />
                      )}

                      {getNotificationIcon(item.type)}

                      <div className="flex-1 min-w-0 pt-0.5">
                        <div className="flex items-start justify-between gap-2">
                          <p className={`text-[13.5px] font-bold leading-snug group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors truncate ${
                            !item.is_read ? 'text-slate-900 dark:text-white' : 'text-slate-800 dark:text-slate-200'
                          }`}>
                            {item.title}
                          </p>
                          <span className="text-[11px] font-medium text-slate-400 dark:text-slate-500 shrink-0 mt-0.5">
                            {formatTimeAgo(item.created_at)}
                          </span>
                        </div>
                        <p className="text-[12.5px] text-slate-600 dark:text-slate-300 mt-1 line-clamp-2 leading-relaxed">
                          {item.message}
                        </p>
                      </div>

                      {!item.is_read && (
                        <span className="h-2 w-2 rounded-full bg-indigo-500 dark:bg-indigo-400 shrink-0 mt-2 ring-2 ring-indigo-200 dark:ring-indigo-700 shadow-xs" />
                      )}
                    </div>
                  ))
                )}
              </div>

              {/* Popover Footer */}
              <div className="px-4 py-3 border-t border-slate-100 dark:border-slate-800/70 bg-gradient-to-r from-slate-50/80 to-white/60 dark:from-slate-900/60 dark:to-slate-900/30">
                <button
                  onClick={() => {
                    setIsNotifOpen(false);
                    navigate('/discovery');
                  }}
                  className="w-full py-2 px-3.5 rounded-xl text-[12.5px] font-semibold text-slate-600 dark:text-slate-400 hover:text-indigo-600 dark:hover:text-indigo-400 hover:bg-indigo-50 dark:hover:bg-indigo-950/50 border border-transparent hover:border-indigo-100 dark:hover:border-indigo-800/60 transition-all flex items-center justify-center gap-1.5 cursor-pointer group"
                >
                  <span>View discovery pipeline logs</span>
                  <ArrowRight className="h-3.5 w-3.5 group-hover:translate-x-0.5 transition-transform" />
                </button>
              </div>
            </div>
          )}
        </div>

        <div className="h-5 w-px bg-slate-200 dark:bg-slate-800 hidden sm:block shrink-0 mx-1" />

        {/* User Profile */}
        <div
          onClick={() => navigate('/settings')}
          className="flex items-center gap-2 cursor-pointer select-none shrink-0 pl-1 group"
          title="Account Settings"
        >
          <div className="h-[30px] w-[30px] rounded-full bg-indigo-100 dark:bg-indigo-950/80 text-indigo-700 dark:text-indigo-300 font-bold text-[12px] flex items-center justify-center border border-indigo-200/80 dark:border-indigo-800/60 shadow-2xs shrink-0">
            {userName ? userName.charAt(0).toUpperCase() : 'U'}
          </div>
          <span className="text-[14.5px] font-bold text-slate-900 dark:text-slate-100 hidden md:inline-block leading-none tracking-tight group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors">
            {userName}
          </span>
          <ChevronDown className="h-3.5 w-3.5 text-slate-400 group-hover:text-slate-600 dark:group-hover:text-slate-200 transition-colors shrink-0 hidden md:inline-block" />
        </div>
      </div>
    </header>
  );
};

export default TopHeader;
