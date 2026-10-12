import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import {
  triggerDiscoveryRun,
  getDashboardSummary,
  getDiscoveryStatus,
  getDiscoveryLogs,
  clearDiscoveryLogs as clearDiscoveryLogsApi,
} from '../api';
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
    timestamp: '--:--:--',
    level: 'info',
    tag: 'SYS',
    message: 'Connecting to live Discovery Engine backend telemetry...',
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

  // Fetch real status and real terminal logs from backend on mount
  useEffect(() => {
    let isMounted = true;
    getDiscoveryStatus()
      .then((st) => {
        if (!isMounted) return;
        if (st?.last_run_at) {
          const d = new Date(st.last_run_at);
          setLastRunAt(d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }));
        }
        if (st?.last_jobs_synced) {
          setLastSyncedCount(st.last_jobs_synced);
        }
      })
      .catch(() => {});

    getDiscoveryLogs()
      .then((logs) => {
        if (!isMounted) return;
        if (logs && logs.length > 0) {
          setTerminalLogs(logs as TerminalLog[]);
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
    clearDiscoveryLogsApi().catch(() => {});
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
        setDiscoveryStatusText('Triggering backend discovery pipeline...');

        // Trigger backend API in background with selected cache mode
        await triggerDiscoveryRun({ source, use_cache: activeCache }).catch((err) => {
          console.warn('Discovery API call warning:', err);
          return { message: 'Discovery task queued' };
        });

        let pollCount = 0;
        let isBackendRunning = true;
        let hasSeenRunning = false;
        let lastFetchedStatus = null;

        // Poll backend /api/v1/discovery/status and /api/v1/discovery/logs concurrently
        while (isBackendRunning && pollCount < 180) {
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

          // Wait 1 second between polls
          await new Promise((r) => setTimeout(r, 1000));
          pollCount++;
          const elapsedSec = pollCount;

          try {
            const [st, backendLogs] = await Promise.all([
              getDiscoveryStatus(),
              getDiscoveryLogs(),
            ]);
            lastFetchedStatus = st;

            if (backendLogs && backendLogs.length > 0) {
              setTerminalLogs(backendLogs as TerminalLog[]);
              const lastLog = backendLogs[backendLogs.length - 1];
              if (lastLog?.message) {
                setDiscoveryStatusText(`${lastLog.message} (${elapsedSec}s)`);
              }
            }

            if (st.is_running || st.last_status === 'running') {
              hasSeenRunning = true;
            }

            // Complete when backend is not running AND it was observed running (or minimum 2 polls checked)
            if (!st.is_running && st.last_status !== 'running' && (hasSeenRunning || pollCount >= 2)) {
              isBackendRunning = false;
              break;
            }
          } catch (pollErr) {
            console.warn('Status poll warning:', pollErr);
          }
        }

        if (isCancelledRef.current) {
          return;
        }

        // Fetch final status, summary, and real complete logs
        const [finalStatus, summaryRes, finalLogs] = await Promise.all([
          getDiscoveryStatus().catch(() => lastFetchedStatus),
          getDashboardSummary().catch(() => null),
          getDiscoveryLogs().catch(() => null),
        ]);

        if (finalLogs && finalLogs.length > 0) {
          setTerminalLogs(finalLogs as TerminalLog[]);
        }

        const syncedCount = finalStatus?.last_jobs_synced ?? 0;
        const finishTime = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });

        setLastRunAt(finishTime);
        setLastSyncedCount(syncedCount);

        if (finalStatus?.last_error) {
          toast.error(`Discovery warning: ${finalStatus.last_error.slice(0, 100)}`, 10000);
        } else {
          playDiscoverySuccessSound();
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
