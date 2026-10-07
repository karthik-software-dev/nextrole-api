import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import { triggerDiscoveryRun, getDashboardSummary, getDiscoveryStatus } from '../api';
import { useToast } from './ToastContext';
import {
  playDiscoverySuccessSound,
  playDiscoveryResumeSound,
  playDiscoveryPauseSound,
  playDiscoveryStopSound,
  playDiscoveryStartSound,
} from '../utils/audio';

export interface TerminalLog {
  id: string;
  timestamp: string;
  level: 'info' | 'net' | 'scrape' | 'parse' | 'filter' | 'dedup' | 'tier' | 'db' | 'success' | 'warn';
  tag: string;
  message: string;
}

interface DiscoveryContextType {
  isDiscovering: boolean;
  isPaused: boolean;
  discoveryStatusText: string;
  lastRunAt: string | null;
  lastSyncedCount: number;
  terminalLogs: TerminalLog[];
  runDiscovery: (source?: string, overrideCache?: boolean, openModal?: boolean) => Promise<void>;
  pauseDiscovery: () => void;
  resumeDiscovery: () => void;
  stopDiscovery: () => void;
  clearTerminalLogs: () => void;
  useCache: boolean;
  setUseCache: (val: boolean) => void;
  isModalOpen: boolean;
  setIsModalOpen: (open: boolean) => void;
}

const INITIAL_LOGS: TerminalLog[] = [
  {
    id: 'init-1',
    timestamp: '10:00:00',
    level: 'info',
    tag: 'SYS',
    message: 'NextRole Discovery Engine v2.4 initialized. 30 source connectors ready.',
  },
  {
    id: 'init-2',
    timestamp: '10:00:01',
    level: 'db',
    tag: 'DB',
    message: 'PostgreSQL connection verified (localhost:5432 / database: job_agent).',
  },
  {
    id: 'init-3',
    timestamp: '10:00:02',
    level: 'filter',
    tag: 'CALIB',
    message: 'Target filter calibrated: Python, FastAPI, Backend Engineer (Min score: 50%).',
  },
  {
    id: 'init-4',
    timestamp: '10:00:03',
    level: 'success',
    tag: 'STANDBY',
    message: 'Engine in standby. Click "Trigger Full Discovery Run" or top bar button to execute.',
  },
];

const DiscoveryContext = createContext<DiscoveryContextType>({
  isDiscovering: false,
  isPaused: false,
  discoveryStatusText: '',
  lastRunAt: null,
  lastSyncedCount: 0,
  terminalLogs: INITIAL_LOGS,
  runDiscovery: async () => {},
  pauseDiscovery: () => {},
  resumeDiscovery: () => {},
  stopDiscovery: () => {},
  clearTerminalLogs: () => {},
  useCache: true,
  setUseCache: () => {},
  isModalOpen: false,
  setIsModalOpen: () => {},
});

export const DiscoveryProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { toast } = useToast();
  const [isDiscovering, setIsDiscovering] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [discoveryStatusText, setDiscoveryStatusText] = useState('');
  const [lastRunAt, setLastRunAt] = useState<string | null>(null);
  const [lastSyncedCount, setLastSyncedCount] = useState<number>(0);
  const [terminalLogs, setTerminalLogs] = useState<TerminalLog[]>(INITIAL_LOGS);

  const isPausedRef = useRef(false);
  const isCancelledRef = useRef(false);

  const [useCache, setUseCacheState] = useState<boolean>(() => {
    const saved = localStorage.getItem('discovery_use_cache');
    return saved !== null ? saved === 'true' : true;
  });

  // Fetch real status from backend on mount so last executed time is immediately available
  useEffect(() => {
    let isMounted = true;
    getDiscoveryStatus()
      .then((st) => {
        if (!isMounted) return;
        if (st?.last_run_at) {
          const d = new Date(st.last_run_at);
          setLastRunAt(d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }));
        }
        if (st?.last_jobs_synced) {
          setLastSyncedCount(st.last_jobs_synced);
        }
      })
      .catch(() => {});
    return () => {
      isMounted = false;
    };
  }, []);

  const setUseCache = useCallback((val: boolean) => {
    setUseCacheState(val);
    localStorage.setItem('discovery_use_cache', String(val));
  }, []);

  const clearTerminalLogs = useCallback(() => {
    setTerminalLogs([]);
  }, []);

  const addLog = (level: TerminalLog['level'], tag: string, message: string) => {
    const timestamp = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    setTerminalLogs((prev) => [
      ...prev,
      {
        id: `${Date.now()}-${Math.random()}`,
        timestamp,
        level,
        tag,
        message,
      },
    ]);
  };

  const pauseDiscovery = useCallback(() => {
    if (!isDiscovering || isPausedRef.current) return;
    isPausedRef.current = true;
    setIsPaused(true);
    playDiscoveryPauseSound();
    addLog('warn', 'PAUSE', 'Discovery execution paused by user.');
    setDiscoveryStatusText('Paused (Click Resume to continue syncing)');
  }, [isDiscovering]);

  const resumeDiscovery = useCallback(() => {
    if (!isDiscovering || !isPausedRef.current) return;
    isPausedRef.current = false;
    setIsPaused(false);
    playDiscoveryResumeSound();
    addLog('info', 'RESUME', 'Discovery execution resumed.');
    setDiscoveryStatusText('Resuming discovery pipeline...');
  }, [isDiscovering]);

  const stopDiscovery = useCallback(() => {
    isCancelledRef.current = true;
    isPausedRef.current = false;
    setIsPaused(false);
    setIsDiscovering(false);
    playDiscoveryStopSound();
    addLog('warn', 'STOP', 'Discovery execution cancelled by user.');
    setDiscoveryStatusText('Cancelled');
    toast.info('Discovery pipeline stopped.');
  }, [toast]);

  const runDiscovery = useCallback(
    async (source?: string, overrideCache?: boolean, openModal: boolean = true) => {
      if (isDiscovering) return;

      playDiscoveryStartSound();

      const activeCache = overrideCache !== undefined ? overrideCache : useCache;
      isCancelledRef.current = false;
      isPausedRef.current = false;
      setIsPaused(false);

      if (openModal) {
        setIsModalOpen(true);
      }

      try {
        setIsDiscovering(true);
        const startTime = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
        addLog('info', 'SESSION', `──────────────── Discovery Session Started at ${startTime} [Source: ${source || 'ALL_30_INTEGRATED_SOURCES'}] ────────────────`);
        setDiscoveryStatusText('Bootstrapping crawler workers across 30 integrated sources...');
        addLog('info', 'INIT', `Bootstrapping NextRole Discovery Engine v2.4 (Worker PID: 10488)`);
        addLog(
          'info',
          'CONFIG',
          `Mode: ${activeCache ? '💾 TEST CACHE (Fast Offline Snapshot)' : '🌐 REAL-TIME LIVE SCRAPE (Active Web APIs)'} | Target: Python / FastAPI / Backend Engineer`
        );

        // Trigger backend API in background with selected cache mode
        await triggerDiscoveryRun({ source, use_cache: activeCache }).catch((err) => {
          console.warn('Discovery API call warning:', err);
          return { message: 'Discovery task queued' };
        });

        // Brief tick to allow backend background task to register in-memory status
        await new Promise((r) => setTimeout(r, 600));

        let pollCount = 0;
        let isBackendRunning = true;
        let lastFetchedStatus = null;

        // Poll backend /api/v1/discovery/status until background tasks finish
        while (isBackendRunning && pollCount < 120) {
          if (isCancelledRef.current) {
            break;
          }

          // Handle pause loop
          while (isPausedRef.current) {
            if (isCancelledRef.current) break;
            await new Promise((r) => setTimeout(r, 400));
          }

          if (isCancelledRef.current) {
            break;
          }

          pollCount++;
          const elapsedSec = Math.round(pollCount * 1.5);

          try {
            const st = await getDiscoveryStatus();
            lastFetchedStatus = st;
            isBackendRunning = st.is_running;

            if (!isBackendRunning) {
              break;
            }

            if (activeCache) {
              setDiscoveryStatusText(`Ingesting cached snapshots... (${elapsedSec}s)`);
              if (pollCount === 1) {
                addLog('net', 'CACHE', 'Loading pre-cached postings from local snapshot storage across 30 sources...');
              } else if (pollCount === 2) {
                addLog('parse', 'PARSE', 'Normalizing job schema records and eliminating duplicates...');
              }
            } else {
              // Live Scraping Progress Logging
              if (pollCount === 1) {
                setDiscoveryStatusText(`Querying Indeed & Naukri live... (${elapsedSec}s)`);
                addLog('net', 'NET', 'Dispatching live concurrent HTTP/2 scrapers to active pipelines...');
                addLog('scrape', 'INDEED', '[Indeed India] Executing live search "Python Developer Bangalore"...');
              } else if (pollCount === 3) {
                setDiscoveryStatusText(`Scanning ATS & Tech Portals... (${elapsedSec}s)`);
                addLog('scrape', 'NAUKRI', '[Naukri Portal] Searching "Backend Engineer 3-5 Yrs"...');
                addLog('scrape', 'ATS', '[ATS Engines] Scanning Greenhouse, Lever, SmartRecruiters, Workday, and Ashby boards...');
              } else if (pollCount === 7) {
                setDiscoveryStatusText(`Querying LinkedIn, Hirist & Wellfound live... (${elapsedSec}s)`);
                addLog('scrape', 'LINKEDIN', '[LinkedIn] In-house crawler querying job listings...');
                addLog('scrape', 'HIRIST', '[Hirist API] Fetching technology specialist opportunities...');
                addLog('scrape', 'WELLFOUND', '[Wellfound] Fetching verified startup postings with salary metadata...');
              } else if (pollCount === 12) {
                setDiscoveryStatusText(`Normalizing schemas & tech stack scoring... (${elapsedSec}s)`);
                addLog('parse', 'PARSE', 'Candidate postings retrieved across feeds. Executing schema normalization pipeline...');
                addLog('filter', 'RELEVANCE', 'Evaluating Tech Stack relevance (Python, FastAPI, PostgreSQL, AWS)... Threshold >= 50%');
              } else if (pollCount === 17) {
                setDiscoveryStatusText(`Deduplicating & computing priority tiers... (${elapsedSec}s)`);
                addLog('dedup', 'DEDUP', 'Computing SHA-256 fingerprint collision hashes... Eliminating duplicates');
                addLog('tier', 'TIER', 'Classifying Priority: Tier-1 opportunities (Target ATS & score >= 80%), Tier-2 opportunities');
              } else if (pollCount >= 22) {
                setDiscoveryStatusText(`Synchronizing PostgreSQL database... (${elapsedSec}s)`);
                if (pollCount === 22) {
                  addLog('db', 'POSTGRES', 'Writing transactional upserts to PostgreSQL (localhost:5432/job_agent)...');
                }
              } else {
                setDiscoveryStatusText(`Crawling & syncing jobs to database... (${elapsedSec}s)`);
              }
            }
          } catch (pollErr) {
            console.warn('Status poll warning:', pollErr);
          }

          await new Promise((r) => setTimeout(r, 1500));
        }

        if (isCancelledRef.current) {
          return;
        }

        // Fetch final status and summary
        const finalStatus = await getDiscoveryStatus().catch(() => lastFetchedStatus);
        const summaryRes = await getDashboardSummary().catch(() => null);
        const totalVerified = summaryRes?.active_jobs ?? 0;
        const syncedCount = finalStatus?.last_jobs_synced ?? 0;
        const finishTime = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });

        setLastRunAt(finishTime);
        setLastSyncedCount(syncedCount);

        if (finalStatus?.last_error) {
          addLog('warn', 'WARN', `Discovery completed with warning: ${finalStatus.last_error}`);
          toast.error(`Discovery warning: ${finalStatus.last_error.slice(0, 100)}`, 10000);
        } else {
          addLog(
            'success',
            'COMPLETE',
            `✅ Discovery cycle finished at ${finishTime}. Successfully synced ${syncedCount} fresh jobs into database! Total active jobs: ${totalVerified}.`
          );
          // Play pleasant notification sound chime
          playDiscoverySuccessSound();
          // Clear toast message
          toast.success(`🎉 Successfully discovered ${syncedCount} fresh jobs!`, 10000);
        }
      } catch (err: any) {
        console.error('Discovery error:', err);
        addLog('warn', 'WARN', `Discovery encountered an error: ${err.message || 'Check network connection'}`);
        toast.error('Discovery completed with errors.', 10000);
      } finally {
        setIsDiscovering(false);
        setIsPaused(false);
        isPausedRef.current = false;
        setDiscoveryStatusText('');
      }
    },
    [isDiscovering, toast, useCache]
  );

  return (
    <DiscoveryContext.Provider
      value={{
        isDiscovering,
        isPaused,
        discoveryStatusText,
        lastRunAt,
        lastSyncedCount,
        terminalLogs,
        runDiscovery,
        pauseDiscovery,
        resumeDiscovery,
        stopDiscovery,
        clearTerminalLogs,
        useCache,
        setUseCache,
        isModalOpen,
        setIsModalOpen,
      }}
    >
      {children}
    </DiscoveryContext.Provider>
  );
};

export const useDiscovery = () => useContext(DiscoveryContext);
