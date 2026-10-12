import React, { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import {
  Radar,
  Play,
  Pause,
  CheckCircle2,
  AlertTriangle,
  Clock,
  Database,
  ArrowRight,
  RefreshCw,
  Server,
  Layers,
  Sparkles,
  Loader2,
  Terminal as TerminalIcon,
  Copy,
  Trash2,
  Check,
  Search,
  Globe,
  Briefcase,
  ExternalLink,
  ChevronDown,
  RotateCcw,
  X,
  Zap,
} from 'lucide-react';
import { getDiscoveryStatus, getDashboardSummary, getDiscoverySources } from '../api';
import { useDiscovery, type TerminalLog } from '../context/DiscoveryContext';
import type { DiscoveryStatus, DashboardSummary, DiscoverySource } from '../types';
import { Button } from '../components/ui/Button';
import { CompanyAvatar } from '../components/ui/CompanyAvatar';
import { playToggleSwitchSound } from '../utils/audio';

export const DiscoveryPage: React.FC = () => {
  const {
    isDiscovering,
    isPaused,
    pauseDiscovery,
    resumeDiscovery,
    discoveryStatusText,
    lastRunAt,
    terminalLogs,
    runDiscovery,
    clearTerminalLogs,
    useCache,
    setUseCache,
    setIsModalOpen,
    latestPipeline,
  } = useDiscovery();
  const [status, setStatus] = useState<DiscoveryStatus | null>(null);
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [sources, setSources] = useState<DiscoverySource[]>([]);
  const [sourceSearch, setSourceSearch] = useState('');
  const [sourceCategory, setSourceCategory] = useState<'all' | 'portals' | 'ats' | 'tech'>('all');
  const [activeTab, setActiveTab] = useState<'terminal' | 'sources'>('terminal');
  const [autoScroll, setAutoScroll] = useState(true);
  const [copied, setCopied] = useState(false);

  const terminalEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetchStatus();
  }, [lastRunAt]);

  // When discovery starts, auto-focus to the terminal tab
  useEffect(() => {
    if (isDiscovering) {
      setActiveTab('terminal');
    }
  }, [isDiscovering]);

  // Auto-scroll terminal to bottom when new logs arrive
  useEffect(() => {
    if (autoScroll && activeTab === 'terminal') {
      terminalEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [terminalLogs, autoScroll, activeTab]);

  const fetchStatus = async () => {
    try {
      const [st, sm, srcList] = await Promise.all([
        getDiscoveryStatus().catch(() => null),
        getDashboardSummary().catch(() => null),
        getDiscoverySources().catch(() => []),
      ]);
      setStatus(st);
      setSummary(sm);
      if (srcList && srcList.length > 0) {
        setSources(srcList);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleRunDiscovery = async () => {
    setActiveTab('terminal');
    await runDiscovery();
    fetchStatus();
  };

  const handleCopyLogs = () => {
    const text = terminalLogs.map((l) => `[${l.timestamp}] [${l.tag}] ${l.message}`).join('\n');
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const filteredLogs = terminalLogs;

  const getBadgeStyle = (level: TerminalLog['level']) => {
    switch (level) {
      case 'net':
        return 'text-cyan-400 bg-cyan-950/60 border-cyan-800/80';
      case 'scrape':
        return 'text-amber-400 bg-amber-950/60 border-amber-800/80';
      case 'parse':
        return 'text-sky-400 bg-sky-950/60 border-sky-800/80';
      case 'filter':
        return 'text-purple-400 bg-purple-950/60 border-purple-800/80';
      case 'dedup':
        return 'text-violet-400 bg-violet-950/60 border-violet-800/80';
      case 'tier':
        return 'text-pink-400 bg-pink-950/60 border-pink-800/80';
      case 'db':
        return 'text-emerald-400 bg-emerald-950/60 border-emerald-800/80';
      case 'success':
        return 'text-green-300 bg-green-950/80 border-green-700/80 font-bold';
      case 'warn':
        return 'text-rose-400 bg-rose-950/60 border-rose-800/80';
      default:
        return 'text-slate-400 bg-slate-800/80 border-slate-700';
    }
  };

  const isPortals = (s: DiscoverySource) =>
    s.engine_type.toLowerCase().includes('portal') ||
    s.engine_type.toLowerCase().includes('search engine') ||
    ['indeed', 'naukri', 'shine', 'timesjobs', 'internshala', 'apna', 'freshersworld'].some((k) =>
      s.slug.toLowerCase().includes(k) || s.name.toLowerCase().includes(k)
    );

  const isAts = (s: DiscoverySource) =>
    s.engine_type.toLowerCase().includes('ats') ||
    ['greenhouse', 'lever', 'smartrecruiters', 'workday', 'ashby', 'bamboohr', 'personio', 'recruitee', 'workable', 'teamtailor', 'breezy'].some((k) =>
      s.slug.toLowerCase().includes(k) || s.name.toLowerCase().includes(k)
    );

  const isTech = (s: DiscoverySource) =>
    s.engine_type.toLowerCase().includes('specialist') ||
    s.engine_type.toLowerCase().includes('network') ||
    s.engine_type.toLowerCase().includes('startup') ||
    ['cutshort', 'hirist', 'wellfound', 'remotive', 'jobicy', 'arbeitnow', 'relocateme', 'wwr', 'linkedin'].some((k) =>
      s.slug.toLowerCase().includes(k) || s.name.toLowerCase().includes(k)
    );

  const categoryOptions = [
    { key: 'all', label: 'All Sources', count: sources.length || 30 },
    { key: 'portals', label: 'Talent Portals', count: sources.filter(isPortals).length },
    { key: 'ats', label: 'Direct ATS Engines', count: sources.filter(isAts).length },
    { key: 'tech', label: 'Tech & Startups', count: sources.filter(isTech).length },
  ];

  const filteredSources = sources.filter((s) => {
    if (sourceCategory === 'ats' && !isAts(s)) return false;
    if (sourceCategory === 'portals' && !isPortals(s)) return false;
    if (sourceCategory === 'tech' && !isTech(s)) return false;

    if (!sourceSearch.trim()) return true;
    const q = sourceSearch.toLowerCase();
    return (
      s.name.toLowerCase().includes(q) ||
      s.engine_type.toLowerCase().includes(q) ||
      s.status.toLowerCase().includes(q) ||
      s.ats_detection.toLowerCase().includes(q)
    );
  });

  const getSourceStatusBadge = (st: string) => {
    switch (st) {
      case 'Active':
        return 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/80 dark:text-emerald-300 border-emerald-300 dark:border-emerald-800';
      case 'Integrated':
        return 'bg-indigo-100 text-indigo-800 dark:bg-indigo-950/80 dark:text-indigo-300 border-indigo-300 dark:border-indigo-800';
      case 'Standby':
        return 'bg-amber-100 text-amber-800 dark:bg-amber-950/80 dark:text-amber-300 border-amber-300 dark:border-amber-800';
      case 'Blocked':
        return 'bg-rose-100 text-rose-800 dark:bg-rose-950/80 dark:text-rose-300 border-rose-300 dark:border-rose-800';
      default:
        return 'bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-300 border-slate-300 dark:border-slate-700';
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-[28px] sm:text-[32px] font-bold tracking-tight text-slate-900 dark:text-white">
            Discovery Engine Monitor
          </h1>
          <p className="mt-1 text-[13.5px] text-slate-700 dark:text-slate-300">
            Real-time live crawler terminal, source yield telemetry, and multi-pipeline synchronization.
          </p>
        </div>

        {/* Discovery Action Controls with Test Cache / Real-Time Live Mode Switcher */}
        <div className="flex flex-col sm:flex-row sm:items-center gap-3 shrink-0">
          {/* Segmented Mode Selector */}
          <div className="flex items-center p-1 rounded-xl bg-slate-100 dark:bg-slate-800/90 border border-slate-200/80 dark:border-slate-700/80 shadow-2xs">
            <button
              type="button"
              disabled={isDiscovering}
              onClick={() => {
                if (!useCache) {
                  playToggleSwitchSound('cache');
                  setUseCache(true);
                }
              }}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer ${useCache
                  ? 'bg-white dark:bg-slate-900 text-indigo-600 dark:text-indigo-400 shadow-xs font-bold border border-slate-200/50 dark:border-slate-700/50'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200'
                } disabled:opacity-50 disabled:cursor-not-allowed`}
              title="Fast development testing using local snapshot cache without external network requests"
            >
              <Database className="h-3.5 w-3.5" />
              <span>Test Cache</span>
            </button>

            <button
              type="button"
              disabled={isDiscovering}
              onClick={() => {
                if (useCache) {
                  playToggleSwitchSound('live');
                  setUseCache(false);
                }
              }}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer ${!useCache
                  ? 'bg-white dark:bg-slate-900 text-emerald-600 dark:text-emerald-400 shadow-xs font-bold border border-slate-200/50 dark:border-slate-700/50'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200'
                } disabled:opacity-50 disabled:cursor-not-allowed`}
              title="Real-time live mode: queries live company career APIs directly"
            >
              <span className="relative flex h-2 w-2">
                {!useCache && (
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
                )}
                <span className={`relative inline-flex rounded-full h-2 w-2 ${!useCache ? 'bg-emerald-500' : 'bg-slate-400'}`} />
              </span>
              <Globe className="h-3.5 w-3.5" />
              <span>Real-Time Live</span>
            </button>
          </div>

          {/* Primary Discovery Button with Clean Round Spinner & Pause Control */}
          {isDiscovering ? (
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setIsModalOpen(true)}
                className="h-10 px-4 rounded-xl bg-indigo-50 dark:bg-indigo-950/60 border border-indigo-200/80 dark:border-indigo-800/80 text-indigo-600 dark:text-indigo-400 flex items-center justify-center gap-2 shadow-xs transition-all text-xs font-semibold cursor-pointer"
                title="View discovery modal"
              >
                <div className="flex items-center gap-1">
                  <span className="h-1.5 w-1.5 rounded-full bg-indigo-500 animate-bounce [animation-delay:-0.3s]" />
                  <span className="h-1.5 w-1.5 rounded-full bg-indigo-500 animate-bounce [animation-delay:-0.15s]" />
                  <span className="h-1.5 w-1.5 rounded-full bg-indigo-500 animate-bounce" />
                </div>
                <span>{isPaused ? 'Paused' : 'Syncing Feeds...'}</span>
              </button>

              <button
                type="button"
                onClick={isPaused ? resumeDiscovery : pauseDiscovery}
                className="h-10 px-3.5 rounded-xl bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 border border-slate-200/80 dark:border-slate-700 flex items-center justify-center gap-1.5 text-xs font-semibold transition-colors cursor-pointer"
                title={isPaused ? 'Resume syncing' : 'Pause syncing'}
              >
                {isPaused ? <Play className="h-3.5 w-3.5 fill-current" /> : <Pause className="h-3.5 w-3.5" />}
                <span>{isPaused ? 'Resume' : 'Pause'}</span>
              </button>
            </div>
          ) : (
            <Button
              variant="primary"
              size="md"
              leftIcon={<Play className="h-4 w-4 fill-white text-white" />}
              onClick={handleRunDiscovery}
              className="shadow-xs hover:shadow-indigo-500/25 transition-all cursor-pointer whitespace-nowrap"
            >
              Run Discovery
            </Button>
          )}
        </div>
      </div>

      {/* GitLab CI Pipeline Runner Telemetry Banner */}
      {latestPipeline && (
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 px-4 py-3 rounded-2xl border border-indigo-200/80 bg-indigo-50/50 dark:border-indigo-900/60 dark:bg-indigo-950/30 text-xs shadow-xs transition-all">
          <div className="flex items-center gap-2.5 flex-wrap">
            <span className="flex h-2.5 w-2.5 relative shrink-0">
              {(latestPipeline.status === 'running' || latestPipeline.status === 'active') && (
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
              )}
              <span
                className={`inline-flex rounded-full h-2.5 w-2.5 ${
                  latestPipeline.status === 'running' || latestPipeline.status === 'active'
                    ? 'bg-emerald-500'
                    : latestPipeline.status === 'success'
                    ? 'bg-indigo-500'
                    : 'bg-rose-500'
                }`}
              />
            </span>
            <span className="font-bold text-slate-900 dark:text-white">
              🦊 GitLab CI Pipeline #{latestPipeline.pipeline_id || 'Latest'}
            </span>
            <span
              className={`px-2 py-0.5 rounded-full text-[10.5px] font-bold capitalize ${
                latestPipeline.status === 'running' || latestPipeline.status === 'active'
                  ? 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-400 border border-emerald-500/20'
                  : latestPipeline.status === 'success'
                  ? 'bg-indigo-500/15 text-indigo-700 dark:text-indigo-400 border border-indigo-500/20'
                  : 'bg-rose-500/15 text-rose-700 dark:text-rose-400 border border-rose-500/20'
              }`}
            >
              {latestPipeline.status}
            </span>
            <span className="text-slate-500 dark:text-slate-400">
              Source: <strong className="text-slate-700 dark:text-slate-300 uppercase">{latestPipeline.source}</strong> &bull; Synced:{' '}
              <strong className="text-emerald-600 dark:text-emerald-400">{latestPipeline.jobs_synced}</strong> jobs
              {latestPipeline.duration_seconds ? ` (${latestPipeline.duration_seconds}s)` : ''}
            </span>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            {latestPipeline.pipeline_url && (
              <a
                href={latestPipeline.pipeline_url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl font-semibold bg-white dark:bg-slate-900 text-indigo-600 dark:text-indigo-400 border border-indigo-200/60 dark:border-indigo-800/60 hover:bg-indigo-50 dark:hover:bg-slate-800 shadow-2xs transition-colors"
              >
                <span>View in GitLab</span>
                <ExternalLink className="h-3 w-3" />
              </a>
            )}
          </div>
        </div>
      )}

      {/* KPI Cards - Exact Dashboard Card Dimension & Styling */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Card 1: Last Synchronization */}
        <div className="group flex items-center justify-between rounded-2xl border border-slate-200/80 bg-white p-5 sm:p-6 shadow-[0_1px_3px_rgba(0,0,0,0.03),0_1px_2px_rgba(0,0,0,0.02)] transition-[transform,box-shadow,border-color] duration-180 ease-out hover:-translate-y-0.5 hover:border-slate-300 hover:shadow-[0_8px_24px_rgba(0,0,0,0.06)] dark:border-slate-800 dark:bg-[#111726] dark:hover:border-slate-700 dark:hover:shadow-[0_8px_24px_rgba(0,0,0,0.25)]">
          <div className="flex items-center gap-3.5 sm:gap-4 min-w-0 flex-1">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-blue-50 text-blue-600 ring-1 ring-inset ring-blue-600/15 shadow-xs dark:bg-blue-950/60 dark:text-blue-400 dark:ring-blue-400/20">
              <Clock className="h-5 w-5" />
            </div>
            <div className="min-w-0 flex-1">
              <span className="text-[13.5px] font-semibold text-slate-600 dark:text-slate-400 block truncate">
                Last Synchronization
              </span>
              <p className="mt-1 text-[34px] sm:text-[36px] font-bold leading-none tracking-tight text-slate-900 dark:text-white truncate">
                {isDiscovering ? (
                  <span className="inline-flex items-center gap-1.5 py-1.5" title="Synchronizing feeds...">
                    <span className="h-3 w-3 rounded-full bg-blue-500 animate-bounce [animation-delay:-0.3s]" />
                    <span className="h-3 w-3 rounded-full bg-indigo-500 animate-bounce [animation-delay:-0.15s]" />
                    <span className="h-3 w-3 rounded-full bg-purple-500 animate-bounce" />
                  </span>
                ) : status?.last_run_at ? (
                  new Date(status.last_run_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                ) : (
                  lastRunAt || 'Recent'
                )}
              </p>
              <p className="mt-2 truncate text-xs font-medium text-slate-500 dark:text-slate-400">
                {isDiscovering
                  ? 'Crawling active feeds'
                  : `Status: ${status?.last_status === 'running' ? 'Active' : (status?.last_status || 'Success')} (${useCache ? 'Cache' : 'Live'})`}
              </p>
            </div>
          </div>
        </div>

        {/* Card 2: Pipeline Runtime */}
        <div className="group flex items-center justify-between rounded-2xl border border-slate-200/80 bg-white p-5 sm:p-6 shadow-[0_1px_3px_rgba(0,0,0,0.03),0_1px_2px_rgba(0,0,0,0.02)] transition-[transform,box-shadow,border-color] duration-180 ease-out hover:-translate-y-0.5 hover:border-slate-300 hover:shadow-[0_8px_24px_rgba(0,0,0,0.06)] dark:border-slate-800 dark:bg-[#111726] dark:hover:border-slate-700 dark:hover:shadow-[0_8px_24px_rgba(0,0,0,0.25)]">
          <div className="flex items-center gap-3.5 sm:gap-4 min-w-0 flex-1">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-amber-50 text-amber-600 ring-1 ring-inset ring-amber-600/15 shadow-xs dark:bg-amber-950/60 dark:text-amber-400 dark:ring-amber-400/20">
              {isDiscovering ? (
                <Loader2 className="h-5 w-5 animate-spin text-amber-500 dark:text-amber-400" />
              ) : (
                <Zap className="h-5 w-5 fill-amber-500 text-amber-500" />
              )}
            </div>
            <div className="min-w-0 flex-1">
              <span className="text-[13.5px] font-semibold text-slate-600 dark:text-slate-400 block truncate">
                Pipeline Runtime
              </span>
              <p className="mt-1 text-[34px] sm:text-[36px] font-bold leading-none tracking-tight text-slate-900 dark:text-white truncate">
                {isDiscovering ? (
                  <span className="inline-flex items-center gap-1.5 py-1.5" title="Calculating duration...">
                    <span className="h-3 w-3 rounded-full bg-amber-500 animate-bounce [animation-delay:-0.3s]" />
                    <span className="h-3 w-3 rounded-full bg-amber-600 animate-bounce [animation-delay:-0.15s]" />
                    <span className="h-3 w-3 rounded-full bg-yellow-500 animate-bounce" />
                  </span>
                ) : (
                  `${(status?.last_duration_seconds ?? 0) > 0 ? status?.last_duration_seconds : 0}s`
                )}
              </p>
              <p className="mt-2 truncate text-xs font-medium text-slate-500 dark:text-slate-400">
                Cycle #{status?.total_runs ?? 0} · 30 engines
              </p>
            </div>
          </div>
        </div>

        {/* Card 3: Last Total Yield */}
        <div className="group flex items-center justify-between rounded-2xl border border-slate-200/80 bg-white p-5 sm:p-6 shadow-[0_1px_3px_rgba(0,0,0,0.03),0_1px_2px_rgba(0,0,0,0.02)] transition-[transform,box-shadow,border-color] duration-180 ease-out hover:-translate-y-0.5 hover:border-slate-300 hover:shadow-[0_8px_24px_rgba(0,0,0,0.06)] dark:border-slate-800 dark:bg-[#111726] dark:hover:border-slate-700 dark:hover:shadow-[0_8px_24px_rgba(0,0,0,0.25)]">
          <div className="flex items-center gap-3.5 sm:gap-4 min-w-0 flex-1">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-indigo-50 text-indigo-600 ring-1 ring-inset ring-indigo-600/15 shadow-xs dark:bg-indigo-950/60 dark:text-indigo-400 dark:ring-indigo-400/20">
              <Layers className="h-5 w-5" />
            </div>
            <div className="min-w-0 flex-1">
              <span className="text-[13.5px] font-semibold text-slate-600 dark:text-slate-400 block truncate">
                Last Total Yield
              </span>
              <p className="mt-1 text-[34px] sm:text-[36px] font-bold leading-none tracking-tight text-slate-900 dark:text-white truncate">
                {isDiscovering ? (
                  <span className="inline-flex items-center gap-1.5 py-1.5" title="Aggregating postings...">
                    <span className="h-3 w-3 rounded-full bg-indigo-500 animate-bounce [animation-delay:-0.3s]" />
                    <span className="h-3 w-3 rounded-full bg-blue-500 animate-bounce [animation-delay:-0.15s]" />
                    <span className="h-3 w-3 rounded-full bg-emerald-500 animate-bounce" />
                  </span>
                ) : (status?.last_jobs_found && status.last_jobs_found > 0) ? (
                  `+${status.last_jobs_found} Jobs`
                ) : (status?.last_jobs_synced && status.last_jobs_synced > 0) ? (
                  `+${status.last_jobs_synced} Jobs`
                ) : (
                  `${summary?.active_jobs ?? 0} Jobs`
                )}
              </p>
              <p className="mt-2 truncate text-xs font-medium text-slate-500 dark:text-slate-400">
                {status?.last_jobs_found && status.last_jobs_found > 0
                  ? 'From latest discovery cycle'
                  : 'Across Bangalore & Chennai'}
              </p>
            </div>
          </div>
        </div>

        {/* Card 4: Synced to Database */}
        <div className="group flex items-center justify-between rounded-2xl border border-slate-200/80 bg-white p-5 sm:p-6 shadow-[0_1px_3px_rgba(0,0,0,0.03),0_1px_2px_rgba(0,0,0,0.02)] transition-[transform,box-shadow,border-color] duration-180 ease-out hover:-translate-y-0.5 hover:border-slate-300 hover:shadow-[0_8px_24px_rgba(0,0,0,0.06)] dark:border-slate-800 dark:bg-[#111726] dark:hover:border-slate-700 dark:hover:shadow-[0_8px_24px_rgba(0,0,0,0.25)]">
          <div className="flex items-center gap-3.5 sm:gap-4 min-w-0 flex-1">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-purple-50 text-purple-600 ring-1 ring-inset ring-purple-600/15 shadow-xs dark:bg-purple-950/60 dark:text-purple-400 dark:ring-purple-400/20">
              <Database className="h-5 w-5" />
            </div>
            <div className="min-w-0 flex-1">
              <span className="text-[13.5px] font-semibold text-slate-600 dark:text-slate-400 block truncate">
                Synced to Database
              </span>
              <p className="mt-1 text-[34px] sm:text-[36px] font-bold leading-none tracking-tight text-purple-600 dark:text-purple-400 truncate">
                {summary?.active_jobs ?? 0} Verified
              </p>
              <p className="mt-2 truncate text-xs font-medium text-slate-500 dark:text-slate-400">
                {summary?.tier1_jobs ?? 0} Tier 1 • {summary?.tier2_jobs ?? 0} Tier 2
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="border-b border-slate-200 dark:border-slate-800">
        <nav className="-mb-px flex space-x-3 sm:space-x-6 text-[13px] sm:text-[14.5px] font-bold overflow-x-auto no-scrollbar">
          <button
            onClick={() => setActiveTab('terminal')}
            className={`pb-2.5 sm:pb-3 border-b-2 flex items-center gap-1.5 sm:gap-2 transition-colors cursor-pointer shrink-0 ${activeTab === 'terminal'
                ? 'border-indigo-600 text-indigo-600 dark:text-indigo-400 font-bold'
                : 'border-transparent text-slate-700 hover:text-slate-900 dark:text-slate-300 dark:hover:text-white font-semibold'
              }`}
          >
            <TerminalIcon className="h-4 w-4 sm:h-4.5 sm:w-4.5" />
            <span className="sm:hidden">Live Terminal</span>
            <span className="hidden sm:inline">Live Crawler Terminal</span>
            {isDiscovering && (
              <span className="inline-flex items-center gap-1 px-1.5 sm:px-2 py-0.5 rounded-full text-[10px] sm:text-[10.5px] font-bold bg-amber-100 dark:bg-amber-950/80 text-amber-700 dark:text-amber-400 border border-amber-300 dark:border-amber-800">
                <span className="h-1.5 w-1.5 rounded-full bg-amber-500 animate-ping" />
                ACTIVE
              </span>
            )}
          </button>

          <button
            onClick={() => setActiveTab('sources')}
            className={`pb-2.5 sm:pb-3 border-b-2 flex items-center gap-1.5 sm:gap-2 transition-colors cursor-pointer shrink-0 ${activeTab === 'sources'
                ? 'border-indigo-600 text-indigo-600 dark:text-indigo-400 font-bold'
                : 'border-transparent text-slate-700 hover:text-slate-900 dark:text-slate-300 dark:hover:text-white font-semibold'
              }`}
          >
            <Server className="h-4 w-4 sm:h-4.5 sm:w-4.5" />
            <span className="sm:hidden">Sources ({sources.length || 30})</span>
            <span className="hidden sm:inline">Source Connectors ({sources.length || 30})</span>
          </button>
        </nav>
      </div>

      {/* Tab 1: Live Terminal Console View - Clean Engineer Style */}
      {activeTab === 'terminal' && (
        <div className="rounded-2xl border border-slate-800 bg-[#0A0D14] shadow-2xl overflow-hidden font-mono text-xs w-full max-w-full">
          {/* Terminal Window Chrome */}
          <div className="px-3 sm:px-4 py-2 sm:py-3 bg-[#0F1420] border-b border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-2 sm:gap-3 select-none">
            {/* Window Controls & Title */}
            <div className="flex items-center justify-between sm:justify-start gap-2 sm:gap-3 w-full sm:w-auto min-w-0">
              <div className="flex items-center gap-2 min-w-0">
                <div className="flex items-center gap-1.5 shrink-0">
                  <span className="h-2.5 w-2.5 sm:h-3 sm:w-3 rounded-full bg-rose-500/80 inline-block" />
                  <span className="h-2.5 w-2.5 sm:h-3 sm:w-3 rounded-full bg-amber-500/80 inline-block" />
                  <span className="h-2.5 w-2.5 sm:h-3 sm:w-3 rounded-full bg-emerald-500/80 inline-block" />
                </div>
                <span className="text-slate-400 text-[11px] sm:text-xs flex items-center gap-1 sm:gap-1.5 ml-1 font-mono truncate">
                  <span className="text-indigo-400 font-bold">NextRole</span>
                  <span className="text-slate-600">@</span>
                  <span className="text-slate-300 hidden xs:inline">discovery-</span>
                  <span className="text-slate-300">engine</span>
                </span>
              </div>

              {/* Action buttons on mobile (Copy & Clear) */}
              <div className="flex sm:hidden items-center gap-1 text-[11px] shrink-0">
                <button
                  onClick={handleCopyLogs}
                  className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors cursor-pointer"
                  title="Copy terminal logs"
                >
                  {copied ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
                </button>
                <button
                  onClick={clearTerminalLogs}
                  className="p-1.5 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-slate-800 transition-colors cursor-pointer"
                  title="Clear console logs"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
            </div>

            {/* Terminal Actions & Status */}
            <div className="flex items-center justify-between sm:justify-end gap-2 sm:gap-3 text-[10px] sm:text-[11px] w-full sm:w-auto shrink-0">
              {/* Status Indicator */}
              <div className="flex items-center gap-1.5 px-2 sm:px-2.5 py-0.5 sm:py-1 rounded-lg bg-slate-900/90 border border-slate-800 shrink-0">
                {isDiscovering ? (
                  <>
                    <Loader2 className="h-2.5 w-2.5 sm:h-3 sm:w-3 animate-spin text-amber-400" />
                    <span className="text-amber-400 font-bold">CRAWLER EXECUTING</span>
                  </>
                ) : (
                  <>
                    <span className="h-1.5 w-1.5 sm:h-2 sm:w-2 rounded-full bg-emerald-400" />
                    <span className="text-emerald-400 font-bold">STANDBY / READY</span>
                  </>
                )}
              </div>

              {/* Auto Scroll Toggle */}
              <button
                onClick={() => setAutoScroll(!autoScroll)}
                className={`px-2 sm:px-2.5 py-0.5 sm:py-1 rounded-lg transition-colors cursor-pointer border font-semibold shrink-0 ${autoScroll
                    ? 'border-indigo-500/50 bg-indigo-950/40 text-indigo-300'
                    : 'border-slate-800 bg-slate-900 text-slate-500'
                  }`}
                title="Toggle automatic scrolling to latest log lines"
              >
                Auto-scroll: {autoScroll ? 'ON' : 'OFF'}
              </button>

              {/* Copy Logs (Desktop only) */}
              <button
                onClick={handleCopyLogs}
                className="hidden sm:inline-flex p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors cursor-pointer"
                title="Copy terminal logs"
              >
                {copied ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
              </button>

              {/* Clear Terminal (Desktop only) */}
              <button
                onClick={clearTerminalLogs}
                className="hidden sm:inline-flex p-1.5 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-slate-800 transition-colors cursor-pointer"
                title="Clear console logs"
              >
                <Trash2 className="h-3.5 w-3.5" />
              </button>
            </div>
          </div>

          {/* Terminal Logs Viewport */}
          <div className="p-2.5 sm:p-4 space-y-2 sm:space-y-1.5 min-h-[300px] sm:min-h-[380px] max-h-[460px] sm:max-h-[540px] overflow-y-auto leading-relaxed">
            {filteredLogs.map((log) => (
              <div
                key={log.id}
                className="flex flex-col sm:flex-row sm:items-start gap-1 sm:gap-2.5 hover:bg-slate-900/50 p-1.5 sm:px-1.5 sm:py-0.5 rounded transition-colors text-[11px] sm:text-xs border-b border-slate-900/40 sm:border-0"
              >
                {/* Meta row on mobile, inline on desktop */}
                <div className="flex items-center gap-1.5 shrink-0">
                  <span className="text-slate-500 select-none text-[10px] sm:text-[11px] font-mono">
                    [{log.timestamp}]
                  </span>

                  <span
                    className={`px-1.5 py-0.2 rounded border text-[9px] sm:text-[10px] font-bold shrink-0 uppercase tracking-wide ${getBadgeStyle(
                      log.level
                    )}`}
                  >
                    {log.tag}
                  </span>
                </div>

                {/* Message body: wraps cleanly at word boundaries */}
                <span
                  className={`min-w-0 flex-1 break-words font-mono leading-relaxed pl-0.5 sm:pl-0 ${log.level === 'success'
                      ? 'text-emerald-300 font-bold'
                      : log.level === 'warn'
                        ? 'text-rose-400'
                        : log.level === 'scrape'
                          ? 'text-amber-200'
                          : 'text-slate-300'
                    }`}
                >
                  {log.message}
                </span>
              </div>
            ))}

            <div ref={terminalEndRef} />
          </div>

          {/* Terminal Bottom Prompt Bar */}
          <div className="px-3 sm:px-4 py-2 bg-[#090C12] border-t border-slate-900 flex items-center justify-between text-slate-500 text-[10.5px] sm:text-[11px] gap-2">
            <div className="flex items-center gap-1.5 sm:gap-2 font-mono min-w-0 flex-1 overflow-hidden">
              <span className="text-emerald-400 font-bold shrink-0">❯</span>
              <span className="text-slate-400 truncate hidden sm:inline">
                {isDiscovering
                  ? 'python -m engine.discovery --orchestrate-all --stream-logs [RUNNING]'
                  : 'python -m engine.discovery --orchestrate-all [IDLE]'}
              </span>
              <span className="text-slate-400 truncate sm:hidden">
                {isDiscovering
                  ? 'engine.discovery [RUNNING]'
                  : 'engine.discovery [IDLE]'}
              </span>
              <span className="inline-block w-2 h-3.5 bg-indigo-400 animate-pulse shrink-0" />
            </div>
            <span className="text-slate-600 font-mono shrink-0">utf-8</span>
          </div>
        </div>
      )}

      {/* Tab 2: Configured Source Connectors - Interactive Card Grid */}
      {activeTab === 'sources' && (
        <div className="space-y-4">
          {/* Search & Category Pills Controls (Company Directory Style) */}
          <div className="p-4 sm:p-5 rounded-2xl border border-slate-200/80 dark:border-slate-800 bg-white dark:bg-[#111726] shadow-sm space-y-3.5">
            {/* Search Input Box (Same size & styling as Companies Directory) */}
            <div className="relative w-full sm:max-w-md">
              <div className="group relative flex items-center p-1 rounded-xl border border-slate-200/90 dark:border-slate-700/80 bg-slate-50/70 dark:bg-slate-900/50 shadow-xs hover:border-slate-300 dark:hover:border-slate-600 focus-within:border-indigo-500 dark:focus-within:border-indigo-500 focus-within:bg-white dark:focus-within:bg-[#0f1422] focus-within:ring-4 focus-within:ring-indigo-500/15 focus-within:shadow-md focus-within:shadow-indigo-500/5 transition-all duration-300 ease-out">
                <Search className="h-4.5 w-4.5 ml-2.5 text-slate-600 dark:text-slate-300 group-focus-within:text-indigo-600 dark:group-focus-within:text-indigo-400 group-focus-within:scale-110 transition-all duration-300 ease-out shrink-0" />
                <input
                  type="text"
                  placeholder="Search source connectors (e.g. Indeed, Naukri)..."
                  value={sourceSearch}
                  onChange={(e) => setSourceSearch(e.target.value)}
                  className="w-full h-9 bg-transparent border-0 px-2.5 text-[14.5px] text-slate-900 dark:text-slate-100 placeholder:text-slate-700 dark:placeholder:text-slate-300 font-medium focus:outline-none focus:ring-0 leading-normal"
                />
                {sourceSearch && (
                  <button
                    type="button"
                    onClick={() => setSourceSearch('')}
                    className="p-1.5 mr-1 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-200/60 dark:hover:bg-slate-800 transition-colors cursor-pointer animate-in fade-in zoom-in-90"
                    title="Clear search"
                  >
                    <X className="h-4 w-4" />
                  </button>
                )}
              </div>
            </div>

            {/* Category Filter Pills (Direct Pills, Not Dropdown) */}
            <div className="flex flex-wrap items-center gap-2 pt-0.5">
              {categoryOptions.map((opt) => {
                const isActive = sourceCategory === opt.key;
                return (
                  <button
                    key={opt.key}
                    type="button"
                    onClick={() => setSourceCategory(opt.key as any)}
                    className={`inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl text-[13px] font-semibold transition-all cursor-pointer select-none ${isActive
                        ? 'bg-indigo-600 text-white shadow-xs'
                        : 'bg-slate-100 dark:bg-slate-800/80 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700 border border-slate-200/50 dark:border-slate-700/50'
                      }`}
                  >
                    <span>{opt.label}</span>
                    <span
                      className={`text-[11px] font-medium px-1.5 py-0.2 rounded-full tabular-nums ${isActive
                          ? 'bg-indigo-500/80 text-white'
                          : 'bg-slate-200/80 dark:bg-slate-700 text-slate-600 dark:text-slate-400'
                        }`}
                    >
                      {opt.count}
                    </span>
                  </button>
                );
              })}

              {/* Reset CTA if filtered */}
              {(sourceCategory !== 'all' || sourceSearch.trim()) && (
                <button
                  type="button"
                  onClick={() => {
                    setSourceSearch('');
                    setSourceCategory('all');
                  }}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-[12.5px] font-semibold text-slate-500 hover:text-rose-600 dark:text-slate-400 dark:hover:text-rose-400 hover:bg-rose-50/60 dark:hover:bg-rose-950/40 transition-colors cursor-pointer sm:ml-auto"
                >
                  <RotateCcw className="h-3.5 w-3.5" />
                  <span>Reset</span>
                </button>
              )}
            </div>
          </div>

          {/* Connectors Count Subheader */}
          <div className="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400 px-1">
            <span>
              Showing <strong className="text-slate-700 dark:text-slate-200 font-semibold">{filteredSources.length}</strong> of{' '}
              <strong className="text-slate-700 dark:text-slate-200 font-semibold">{sources.length || 30}</strong> configured connectors
            </span>
          </div>

          {/* Responsive Card Grid (Same style as Companies Directory) */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {filteredSources.length === 0 ? (
              <div className="col-span-full py-16 text-center text-xs text-slate-400 bg-white dark:bg-[#111726] rounded-2xl border border-slate-200/80 dark:border-slate-800">
                No matching source connectors found for "{sourceSearch}".
              </div>
            ) : (
              filteredSources.map((src) => (
                <Link
                  key={src.slug || src.id}
                  to={`/jobs?search=${encodeURIComponent(src.name)}`}
                  className="p-5 sm:p-5.5 rounded-2xl border border-slate-200/80 dark:border-slate-800 bg-white dark:bg-[#111726] shadow-xs hover:border-indigo-300 dark:hover:border-indigo-700/60 hover:shadow-md hover:-translate-y-0.5 transition-[transform,box-shadow,border-color] duration-180 ease-out cursor-pointer flex flex-col justify-between group"
                >
                  <div>
                    {/* Header: Monogram Avatar + Speed / Latency Chip + Status Badge */}
                    <div className="flex items-start justify-between gap-2.5">
                      <CompanyAvatar name={src.name} size="lg" />
                      <div className="flex items-center gap-1.5 shrink-0">
                        {/* Crawl Duration / Latency Chip */}
                        <span
                          className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-semibold bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-200/60 dark:border-slate-700/60"
                          title={`Scraper response latency: ${src.latency}`}
                        >
                          <Zap className="h-3 w-3 text-amber-500 fill-amber-500" />
                          {src.latency}
                        </span>

                        {/* Status Badge */}
                        <span
                          className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-semibold ${
                            src.status === 'Active'
                              ? 'bg-emerald-50 dark:bg-emerald-950/80 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800/80'
                              : 'bg-amber-50 dark:bg-amber-950/80 text-amber-700 dark:text-amber-400 border border-amber-200 dark:border-amber-800/80'
                          }`}
                        >
                          <span
                            className={`h-1.5 w-1.5 rounded-full ${
                              src.status === 'Active' ? 'bg-emerald-500' : 'bg-amber-500'
                            }`}
                          />
                          {src.status}
                        </span>
                      </div>
                    </div>

                    {/* Source Name & Engine Type */}
                    <h3 className="text-[16px] sm:text-[17px] font-bold text-slate-900 dark:text-white mt-3 group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors truncate">
                      {src.name}
                    </h3>
                    <p className="text-[12.5px] text-slate-600 dark:text-slate-400 mt-1 truncate">
                      Type: <span className="font-semibold text-slate-700 dark:text-slate-300">{src.engine_type}</span>
                    </p>
                  </div>

                  {/* Card Bottom: Active Roles + Tier 1 Pill Badge + Last Synced Timestamp */}
                  <div className="mt-5 pt-3 border-t border-slate-100 dark:border-slate-800/80 flex items-center justify-between text-xs">
                    <div className="flex items-center gap-2 truncate min-w-0">
                      <span className="text-[13.5px] font-bold text-indigo-600 dark:text-indigo-400 flex items-center gap-1.5 shrink-0">
                        <Briefcase className="h-3.5 w-3.5" />
                        {src.last_yield} Active
                      </span>
                      {src.tier1_count && src.tier1_count > 0 && src.last_yield > 0 ? (
                        <div className="flex items-center gap-1.5 shrink-0">
                          <span className="text-slate-400 dark:text-slate-500 font-normal">·</span>
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-amber-50 dark:bg-amber-950/80 text-amber-700 dark:text-amber-400 border border-amber-200 dark:border-amber-800/80">
                            {Math.min(src.tier1_count, src.last_yield)}/{src.last_yield} Tier 1
                          </span>
                        </div>
                      ) : null}
                    </div>

                    <span
                      className="text-[12.5px] font-medium text-slate-600 dark:text-slate-400 flex items-center gap-1.5 shrink-0 ml-2"
                      title={src.last_synced_at ? `Last synced: ${new Date(src.last_synced_at).toLocaleString()}` : 'Sync standby'}
                    >
                      <Clock className="h-3.5 w-3.5 text-slate-400" />
                      {src.last_synced_at
                        ? new Date(src.last_synced_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                        : 'Recent'}
                    </span>
                  </div>
                </Link>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
};
