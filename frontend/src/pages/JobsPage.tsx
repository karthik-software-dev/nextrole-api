import React, { useState, useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';
import { useSearchParams } from 'react-router-dom';
import {
  Search,
  ArrowUpRight,
  X,
  MapPin,
  Briefcase,
  Layers,
  Banknote,
  Globe,
  Plane,
  RotateCcw,
  ChevronDown,
  Check,
  Bookmark,
  Building2,
  Sparkles,
  Home,
  Clock,
} from 'lucide-react';
import { getJobs, getJobFilterCounts, createApplication, deleteApplicationByJobId } from '../api';
import { useDiscovery } from '../context/DiscoveryContext';
import { useToast } from '../context/ToastContext';
import type { FilterCounts, JobSummary } from '../types';
import { TierBadge, MatchScoreBadge, ApplicationStatusBadge } from '../components/ui/Badge';
import { CompanyAvatar } from '../components/ui/CompanyAvatar';
import { Pagination } from '../components/ui/Pagination';
import { JobDetailDrawer } from './JobDetailDrawer';
import { CardSkeleton } from '../components/ui/Skeleton';
import { playJobApplySound } from '../utils/audio';
import { formatRelativeTime } from '../utils/date';

// Sanitization guard to prevent non-salary description text blobs from rendering
const isValidSalary = (salary?: string | null): boolean => {
  if (!salary) return false;
  const s = salary.trim();
  if (s.length > 45) return false;
  if (/about|description|summary|equity|role|looking for|industry/i.test(s)) return false;
  return /\d/.test(s);
};

const MODE_LABELS: Record<string, string> = {
  wfo: 'Work from office',
  wfh: 'Work from home',
  hybrid: 'Hybrid',
  abroad: 'Abroad / Relocation',
};

const LOC_LABELS: Record<string, string> = {
  BANGALORE: 'Bangalore',
  CHENNAI: 'Chennai',
  REMOTE_INDIA: 'Remote (IN)',
  ABROAD: 'Abroad / Expat',
};

const SAL_LABELS: Record<string, string> = {
  '4-8': '4–8 Lakhs',
  '8-15': '8–15 Lakhs',
  '15-25': '15–25 Lakhs',
  '25+': '25+ Lakhs',
};

export const JobsPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const { lastRunAt } = useDiscovery();
  const { toast } = useToast();

  const [jobs, setJobs] = useState<JobSummary[]>([]);
  const [totalJobs, setTotalJobs] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState<number>(() => {
    const saved = localStorage.getItem('careerpilot_feed_default_page_size');
    return saved ? parseInt(saved, 10) : 10;
  });
  const [isLoading, setIsLoading] = useState(true);

  // Dynamic filter facet counts from database
  const [filterCounts, setFilterCounts] = useState<FilterCounts | null>(null);

  // Filters State
  const [searchQuery, setSearchQuery] = useState(searchParams.get('search') || '');
  const [selectedTier, setSelectedTier] = useState<string>(() => {
    return searchParams.get('tier') || 'all';
  });
  const [selectedLocation, setSelectedLocation] = useState(searchParams.get('location') || 'all');
  const [selectedWorkMode, setSelectedWorkMode] = useState<string>(searchParams.get('work_mode') || 'all');
  
  // Experience filter tailored for 2 Yrs experience target (default = 2)
  const [selectedExp, setSelectedExp] = useState<number | null>(() => {
    const fromUrl = searchParams.get('max_exp');
    return fromUrl ? parseInt(fromUrl, 10) : 2;
  });

  const [selectedSalary, setSelectedSalary] = useState<string>(searchParams.get('salary') || 'all');
  const [selectedMinScore, setSelectedMinScore] = useState<number | null>(() => {
    const fromUrl = searchParams.get('min_score');
    return fromUrl ? parseFloat(fromUrl) : null;
  });

  // Floating dropdown popover state for filter pills
  const [openDropdown, setOpenDropdown] = useState<'workMode' | 'experience' | 'location' | 'salary' | null>(null);
  const filterPillsRef = useRef<HTMLDivElement>(null);

  // Dismiss floating dropdown on click outside or Escape key
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent | TouchEvent) => {
      const mobileSheet = document.getElementById('mobile-filter-sheet');
      if (mobileSheet && mobileSheet.contains(event.target as Node)) {
        return;
      }
      if (filterPillsRef.current && !filterPillsRef.current.contains(event.target as Node)) {
        setOpenDropdown(null);
      }
    };
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setOpenDropdown(null);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('touchstart', handleClickOutside, { passive: true });
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('touchstart', handleClickOutside);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, []);

  // Lock body scroll on mobile when bottom sheet filter is open
  useEffect(() => {
    if (openDropdown) {
      document.body.style.overflow = 'hidden';
      return () => {
        document.body.style.overflow = '';
      };
    }
  }, [openDropdown]);

  // Saved / Bookmarked jobs state (persisted locally)
  const [savedJobIds, setSavedJobIds] = useState<Set<number>>(() => {
    try {
      const saved = localStorage.getItem('careerpilot_saved_jobs');
      return saved ? new Set(JSON.parse(saved)) : new Set();
    } catch {
      return new Set();
    }
  });

  const toggleSaveJob = async (e: React.MouseEvent, target: JobSummary | number) => {
    e.stopPropagation();
    const jobId = typeof target === 'number' ? target : target.id;
    const jobObj = typeof target === 'number' ? jobs.find((j) => j.id === jobId) : target;
    const jobTitle = jobObj?.title || `Job #${jobId}`;
    const isCurrentlySaved = savedJobIds.has(jobId) || jobObj?.application_status === 'drafted' || jobObj?.application_status === 'saved';

    if (isCurrentlySaved) {
      // Optimistically remove from saved
      setSavedJobIds((prev) => {
        const next = new Set(prev);
        next.delete(jobId);
        try {
          localStorage.setItem('careerpilot_saved_jobs', JSON.stringify(Array.from(next)));
        } catch {}
        return next;
      });
      setJobs((prev) =>
        prev.map((j) => (j.id === jobId && (j.application_status === 'drafted' || j.application_status === 'saved')
          ? { ...j, application_status: undefined }
          : j))
      );

      try {
        await deleteApplicationByJobId(jobId);
        toast.info(`"${jobTitle}" removed from Saved / Draft`, 2200);
      } catch (err: any) {
        console.error('Failed to un-save application:', err);
        // Revert on error
        setSavedJobIds((prev) => {
          const next = new Set(prev);
          next.add(jobId);
          try {
            localStorage.setItem('careerpilot_saved_jobs', JSON.stringify(Array.from(next)));
          } catch {}
          return next;
        });
        setJobs((prev) =>
          prev.map((j) => (j.id === jobId ? { ...j, application_status: 'drafted' } : j))
        );
        toast.error('Failed to remove job from saved list', 2200);
      }
    } else {
      // Optimistically add to saved
      setSavedJobIds((prev) => {
        const next = new Set(prev);
        next.add(jobId);
        try {
          localStorage.setItem('careerpilot_saved_jobs', JSON.stringify(Array.from(next)));
        } catch {}
        return next;
      });
      setJobs((prev) =>
        prev.map((j) => (j.id === jobId && !j.application_status ? { ...j, application_status: 'drafted' } : j))
      );

      try {
        await createApplication({
          job_id: jobId,
          initial_status: 'drafted',
          portal_type: jobObj?.ats_provider || 'Company Career Portal',
        });
        toast.success(`"${jobTitle}" saved to Applications CRM (Saved / Draft)`, 2500);
      } catch (err: any) {
        console.error('Failed to save application to CRM:', err);
        // Revert on error
        setSavedJobIds((prev) => {
          const next = new Set(prev);
          next.delete(jobId);
          try {
            localStorage.setItem('careerpilot_saved_jobs', JSON.stringify(Array.from(next)));
          } catch {}
          return next;
        });
        setJobs((prev) =>
          prev.map((j) => (j.id === jobId && j.application_status === 'drafted' ? { ...j, application_status: undefined } : j))
        );
        toast.error(err.message || 'Failed to save opportunity to CRM', 2200);
      }
    }
  };

  const handleApplyJob = async (e: React.MouseEvent, job: JobSummary) => {
    e.stopPropagation();
    playJobApplySound();
    if (job.canonical_apply_url) {
      window.open(job.canonical_apply_url, '_blank', 'noopener,noreferrer');
    }

    if (job.application_status === 'applied') {
      return;
    }

    // Optimistically update feed card
    setJobs((prev) =>
      prev.map((j) => (j.id === job.id ? { ...j, application_status: 'applied' } : j))
    );

    try {
      await createApplication({
        job_id: job.id,
        initial_status: 'applied',
        portal_type: job.ats_provider || 'Company Career Portal',
      });
      toast.success(`Application marked as "Applied" for ${job.company_name}!`, 2000);
    } catch (err: any) {
      console.error('Failed to auto-track application:', err);
      // Revert if error
      setJobs((prev) =>
        prev.map((j) => (j.id === job.id ? { ...j, application_status: job.application_status } : j))
      );
      toast.error(err.message || 'Failed to record application in CRM');
    }
  };

  // Request race guard reference
  const activeRequestIdRef = useRef(0);

  // Selected Job for Slide-over Drawer
  const [selectedJobId, setSelectedJobId] = useState<number | null>(() => {
    const fromUrl = searchParams.get('selected');
    return fromUrl ? parseInt(fromUrl, 10) : null;
  });

  const searchInputRef = useRef<HTMLInputElement>(null);

  // Helper to sync filter changes into URL searchParams
  const updateUrlParam = (key: string, value: string | null) => {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      if (value === null || value === '' || value === 'all') {
        next.delete(key);
      } else {
        next.set(key, value);
      }
      return next;
    }, { replace: true });
  };

  // Keyboard shortcut Ctrl+K / Cmd+K to focus search bar
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        searchInputRef.current?.focus();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  // Sync state if URL query params change (e.g. from top nav search or browser back/forward)
  useEffect(() => {
    const urlSearch = searchParams.get('search') || '';
    const urlTier = searchParams.get('tier') || 'all';
    const urlLoc = searchParams.get('location') || 'all';
    const urlWorkMode = searchParams.get('work_mode') || 'all';
    const urlMaxExp = searchParams.get('max_exp');
    const urlMinScore = searchParams.get('min_score');
    const urlSelected = searchParams.get('selected');

    setSearchQuery((prev) => (prev !== urlSearch ? urlSearch : prev));
    setSelectedTier((prev) => (prev !== urlTier ? urlTier : prev));
    setSelectedLocation((prev) => (prev !== urlLoc ? urlLoc : prev));
    setSelectedWorkMode((prev) => (prev !== urlWorkMode ? urlWorkMode : prev));
    setSelectedExp((prev) => {
      if (urlMaxExp) return parseInt(urlMaxExp, 10);
      return prev !== null ? prev : 2;
    });
    setSelectedMinScore((prev) => {
      const parsed = urlMinScore ? parseFloat(urlMinScore) : null;
      return prev !== parsed ? parsed : prev;
    });
    if (urlSelected) {
      const parsedId = parseInt(urlSelected, 10);
      setSelectedJobId((prev) => (prev !== parsedId ? parsedId : prev));
    }
  }, [searchParams]);

  // Load dynamic filter facet counts
  useEffect(() => {
    const fetchCounts = async () => {
      try {
        const counts = await getJobFilterCounts();
        setFilterCounts(counts);
      } catch (err) {
        console.error('Failed to load filter counts:', err);
      }
    };
    fetchCounts();
  }, [lastRunAt]);

  useEffect(() => {
    fetchJobs();
  }, [currentPage, pageSize, selectedTier, selectedLocation, selectedWorkMode, selectedExp, selectedSalary, selectedMinScore, lastRunAt]);

  const fetchJobs = async (searchOverride?: string) => {
    const requestId = ++activeRequestIdRef.current;
    try {
      setIsLoading(true);
      const query = searchOverride !== undefined ? searchOverride : searchQuery;
      const params: any = {
        page: currentPage,
        page_size: pageSize,
        active_only: true,
      };
      if (query.trim()) params.search = query.trim();
      if (selectedTier !== 'all') params.tier = selectedTier;
      if (selectedLocation !== 'all') params.location = selectedLocation;
      if (selectedWorkMode !== 'all') params.work_mode = selectedWorkMode;
      if (selectedExp !== null && selectedExp < 5) params.max_exp = selectedExp;
      if (selectedMinScore !== null) params.min_score = selectedMinScore;

      const res = await getJobs(params);
      if (requestId !== activeRequestIdRef.current) {
        return;
      }
      setJobs(res.items);
      setTotalJobs(res.meta.total);
      setTotalPages(res.meta.total_pages);
      setSavedJobIds((prev) => {
        const next = new Set(prev);
        res.items.forEach((j: JobSummary) => {
          if (j.application_status === 'drafted' || j.application_status === 'saved') {
            next.add(j.id);
          }
        });
        return next;
      });
    } catch (err) {
      if (requestId === activeRequestIdRef.current) {
        console.error('Failed to fetch jobs:', err);
      }
    } finally {
      if (requestId === activeRequestIdRef.current) {
        setIsLoading(false);
      }
    }
  };

  const selectedWorkModesList = React.useMemo(() => {
    if (!selectedWorkMode || selectedWorkMode === 'all') return [];
    return selectedWorkMode.split(',').map((s) => s.trim()).filter(Boolean);
  }, [selectedWorkMode]);

  const handleWorkModeToggle = (mode: string) => {
    if (mode === 'all') {
      setSelectedWorkMode('all');
      setCurrentPage(1);
      updateUrlParam('work_mode', null);
      return;
    }
    let nextModes: string[];
    if (selectedWorkModesList.includes(mode)) {
      nextModes = selectedWorkModesList.filter((m) => m !== mode);
    } else {
      nextModes = [...selectedWorkModesList, mode];
    }
    const nextValue = nextModes.length === 0 ? 'all' : nextModes.join(',');
    setSelectedWorkMode(nextValue);
    setCurrentPage(1);
    updateUrlParam('work_mode', nextValue === 'all' ? null : nextValue);
  };

  const handleLocationChange = (loc: string) => {
    const nextLoc = selectedLocation === loc ? 'all' : loc;
    setSelectedLocation(nextLoc);
    setCurrentPage(1);
    updateUrlParam('location', nextLoc === 'all' ? null : nextLoc);
  };

  const handleExpChange = (exp: number | null) => {
    setSelectedExp(exp);
    setCurrentPage(1);
    updateUrlParam('max_exp', exp !== null ? exp.toString() : null);
  };

  const handleSalaryChange = (sal: string) => {
    const nextSal = selectedSalary === sal ? 'all' : sal;
    setSelectedSalary(nextSal);
    setCurrentPage(1);
    updateUrlParam('salary', nextSal === 'all' ? null : nextSal);
  };

  const handleScoreChange = (score: number | null) => {
    setSelectedMinScore(score);
    setCurrentPage(1);
    updateUrlParam('min_score', score !== null ? score.toString() : null);
  };

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setCurrentPage(1);
    updateUrlParam('search', searchQuery.trim() || null);
    fetchJobs();
  };

  const handleClearSearch = () => {
    setSearchQuery('');
    setCurrentPage(1);
    updateUrlParam('search', null);
    fetchJobs('');
  };

  const clearFilters = () => {
    setSearchQuery('');
    setSelectedTier('all');
    setSelectedLocation('all');
    setSelectedWorkMode('all');
    setSelectedExp(2); // Reset to default 2 Yrs target
    setSelectedSalary('all');
    setSelectedMinScore(null);
    setCurrentPage(1);
    setSearchParams(new URLSearchParams(), { replace: true });
    fetchJobs('');
  };

  // Active Filter Chips List (derived directly from current filters)
  const activeFiltersList: { key: string; label: string; onRemove: () => void }[] = [];

  if (searchQuery.trim()) {
    activeFiltersList.push({
      key: 'search',
      label: `"${searchQuery.trim()}"`,
      onRemove: handleClearSearch,
    });
  }
  if (selectedWorkModesList.length > 0) {
    selectedWorkModesList.forEach((mode) => {
      activeFiltersList.push({
        key: `work_mode_${mode}`,
        label: MODE_LABELS[mode] || mode,
        onRemove: () => handleWorkModeToggle(mode),
      });
    });
  }
  if (selectedExp !== null && selectedExp !== 2) {
    activeFiltersList.push({
      key: 'max_exp',
      label: `Target: ${selectedExp < 5 ? `${selectedExp} Yrs` : 'Any'}`,
      onRemove: () => handleExpChange(2),
    });
  }
  if (selectedLocation !== 'all') {
    activeFiltersList.push({
      key: 'location',
      label: LOC_LABELS[selectedLocation] || selectedLocation,
      onRemove: () => handleLocationChange(selectedLocation),
    });
  }
  if (selectedSalary !== 'all') {
    activeFiltersList.push({
      key: 'salary',
      label: SAL_LABELS[selectedSalary] || `${selectedSalary} LPA`,
      onRemove: () => handleSalaryChange(selectedSalary),
    });
  }
  if (selectedTier !== 'all') {
    activeFiltersList.push({
      key: 'tier',
      label: selectedTier.toUpperCase(),
      onRemove: () => {
        setSelectedTier('all');
        setCurrentPage(1);
        updateUrlParam('tier', null);
      },
    });
  }
  if (selectedMinScore !== null) {
    activeFiltersList.push({
      key: 'min_score',
      label: `Score ≥ ${selectedMinScore}`,
      onRemove: () => handleScoreChange(null),
    });
  }

  const hasActiveFilters = activeFiltersList.length > 0;

  const workModeOptions = [
    { key: 'wfo', label: 'Work from office', count: filterCounts?.work_modes.find(m => m.key === 'wfo')?.count ?? 80 },
    { key: 'wfh', label: 'Work from home', count: filterCounts?.work_modes.find(m => m.key === 'wfh')?.count ?? 20 },
    { key: 'hybrid', label: 'Hybrid', count: filterCounts?.work_modes.find(m => m.key === 'hybrid')?.count ?? 15 },
    { key: 'abroad', label: 'Abroad / Relocation', count: filterCounts?.work_modes.find(m => m.key === 'abroad')?.count ?? 26 },
  ];

  const locationOptions = [
    { key: 'BANGALORE', label: 'Bangalore', count: filterCounts?.locations.find(l => l.key === 'BANGALORE')?.count ?? 69 },
    { key: 'CHENNAI', label: 'Chennai', count: filterCounts?.locations.find(l => l.key === 'CHENNAI')?.count ?? 22 },
    { key: 'REMOTE_INDIA', label: 'Remote (IN)', count: filterCounts?.locations.find(l => l.key === 'REMOTE_INDIA')?.count ?? 3 },
    { key: 'ABROAD', label: 'Abroad / Expat', count: filterCounts?.locations.find(l => l.key === 'ABROAD')?.count ?? 26 },
  ];

  const salaryOptions = [
    { key: '4-8', label: '4–8 Lakhs', count: filterCounts?.salary_buckets.find(s => s.key === '4-8')?.count ?? 16 },
    { key: '8-15', label: '8–15 Lakhs', count: filterCounts?.salary_buckets.find(s => s.key === '8-15')?.count ?? 15 },
    { key: '15-25', label: '15–25 Lakhs', count: filterCounts?.salary_buckets.find(s => s.key === '15-25')?.count ?? 11 },
    { key: '25+', label: '25+ Lakhs', count: filterCounts?.salary_buckets.find(s => s.key === '25+')?.count ?? 6 },
  ];

  return (
    <div className="space-y-5 pb-12">
      {/* -------------------------------------------------- */}
      {/* PAGE HEADER                                        */}
      {/* -------------------------------------------------- */}
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-[26px] sm:text-[30px] font-bold tracking-tight text-slate-900 dark:text-white">
              Jobs Feed
            </h1>
            <span className="px-2 py-0.5 rounded-md text-[12.5px] font-semibold bg-slate-100 dark:bg-slate-800 text-slate-800 dark:text-slate-300 border border-slate-200 dark:border-slate-700 self-center mt-1">
              {totalJobs} active
            </span>
          </div>
          <p className="mt-1 text-[13px] text-slate-600 dark:text-slate-400">
            Targeted backend &amp; full-stack roles calibrated for 2 years experience.
          </p>
        </div>
      </div>

      {/* -------------------------------------------------- */}
      {/* SEARCH COMMAND BAR & FLOATING DROPDOWN PILLS       */}
      {/* -------------------------------------------------- */}
      <div className="p-3 sm:p-3.5 rounded-2xl border border-slate-200/80 dark:border-slate-800 bg-white dark:bg-[#111726] shadow-sm space-y-3">
        <form onSubmit={handleSearchSubmit} className="relative">
          <div className="group relative flex items-center p-1 sm:p-1.5 rounded-xl border border-slate-200/90 dark:border-slate-700/80 bg-slate-50/70 dark:bg-slate-900/50 shadow-xs hover:border-slate-300 dark:hover:border-slate-600 focus-within:border-indigo-500 dark:focus-within:border-indigo-500 focus-within:bg-white dark:focus-within:bg-[#0f1422] focus-within:ring-4 focus-within:ring-indigo-500/15 focus-within:shadow-md transition-all duration-200 ease-out">
            <Search className="h-4.5 w-4.5 ml-2.5 text-slate-500 dark:text-slate-400 group-focus-within:text-indigo-600 dark:group-focus-within:text-indigo-400 shrink-0" />
            <input
              ref={searchInputRef}
              type="text"
              placeholder="Search jobs, skills, companies..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full h-9.5 bg-transparent border-0 px-3 text-[14px] text-slate-900 dark:text-slate-100 placeholder:text-slate-500 dark:placeholder:text-slate-400 font-medium focus:outline-none focus:ring-0 leading-normal"
            />
            <div className="flex items-center gap-1.5 shrink-0 pr-1">
              {searchQuery ? (
                <button
                  type="button"
                  onClick={handleClearSearch}
                  className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-200/60 dark:hover:bg-slate-800 transition-all cursor-pointer"
                  title="Clear search"
                >
                  <X className="h-4 w-4" />
                </button>
              ) : (
                <div className="hidden sm:flex items-center gap-0.5 px-2 py-1 rounded-md bg-slate-200/60 dark:bg-slate-800 text-[11px] font-semibold text-slate-600 dark:text-slate-400 border border-slate-300/50 dark:border-slate-700/50 select-none">
                  <kbd>Ctrl</kbd>+<kbd>K</kbd>
                </div>
              )}
              <button
                type="submit"
                className="px-3.5 py-1.5 text-[13px] font-semibold text-white bg-indigo-600 hover:bg-indigo-700 active:scale-95 rounded-lg shadow-xs transition-all cursor-pointer"
              >
                Search
              </button>
            </div>
          </div>
        </form>

        {/* Floating Dropdown Filter Pills */}
        <div ref={filterPillsRef} className="flex items-center gap-2 overflow-x-auto sm:overflow-visible pb-1.5 sm:pb-0 scrollbar-none sm:flex-wrap pt-0.5">
          {/* 1. Work Mode Pill */}
          <div className="relative shrink-0">
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                setOpenDropdown(openDropdown === 'workMode' ? null : 'workMode');
              }}
              className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[13px] font-semibold transition-all border cursor-pointer select-none ${
                selectedWorkModesList.length > 0
                  ? 'bg-indigo-50 dark:bg-indigo-950/60 text-indigo-700 dark:text-indigo-300 border-indigo-300 dark:border-indigo-800 shadow-2xs'
                  : 'bg-slate-50 dark:bg-slate-900/60 text-slate-700 dark:text-slate-300 border-slate-200/90 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700 hover:bg-slate-100/60 dark:hover:bg-slate-800/40'
              }`}
            >
              <Briefcase className="h-3.5 w-3.5 text-slate-400" />
              <span>
                {selectedWorkModesList.length === 0
                  ? 'Work mode'
                  : selectedWorkModesList.length === 1
                  ? (MODE_LABELS[selectedWorkModesList[0]] || selectedWorkModesList[0])
                  : `Work mode (${selectedWorkModesList.length})`}
              </span>
              {selectedWorkModesList.length > 0 ? (
                <span
                  onClick={(e) => {
                    e.stopPropagation();
                    handleWorkModeToggle('all');
                  }}
                  className="ml-0.5 p-0.5 rounded hover:bg-indigo-200/60 dark:hover:bg-indigo-900/60 text-indigo-600 dark:text-indigo-400 cursor-pointer"
                  title="Clear work mode"
                >
                  <X className="h-3 w-3" />
                </span>
              ) : (
                <ChevronDown className={`h-3.5 w-3.5 text-slate-400 transition-transform ${openDropdown === 'workMode' ? 'rotate-180' : ''}`} />
              )}
            </button>

            {openDropdown === 'workMode' && (
              <div className="hidden sm:block absolute top-full left-0 mt-1.5 z-40 w-64 p-2 rounded-xl border border-slate-200/90 dark:border-slate-800 bg-white dark:bg-[#111726] shadow-xl space-y-1">
                <div className="flex items-center justify-between px-2 py-1 text-[11px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider">
                  <span>Select Work Mode</span>
                  {selectedWorkModesList.length > 0 && (
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleWorkModeToggle('all');
                      }}
                      className="text-[11px] font-semibold text-indigo-600 dark:text-indigo-400 hover:underline cursor-pointer lowercase"
                    >
                      clear
                    </button>
                  )}
                </div>
                {workModeOptions.map((item) => {
                  const isChecked = selectedWorkModesList.includes(item.key);
                  return (
                    <button
                      key={item.key}
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleWorkModeToggle(item.key);
                      }}
                      className={`flex items-center justify-between w-full text-left text-[13px] px-2.5 py-1.5 rounded-lg transition-colors cursor-pointer select-none ${
                        isChecked
                          ? 'bg-indigo-50/70 dark:bg-indigo-950/40 text-indigo-700 dark:text-indigo-300 font-semibold'
                          : 'text-slate-700 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100/60 dark:hover:bg-slate-800/40'
                      }`}
                    >
                      <div className="flex items-center gap-2">
                        <div className={`h-4 w-4 rounded-md border-2 shrink-0 flex items-center justify-center transition-colors ${
                          isChecked
                            ? 'border-indigo-600 bg-indigo-600 text-white'
                            : 'border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900'
                        }`}>
                          {isChecked && <Check className="h-3 w-3 stroke-[3]" />}
                        </div>
                        <span>{item.label}</span>
                      </div>
                      <span className={`text-[11px] font-medium px-1.5 py-0.2 rounded-full tabular-nums ${
                        isChecked
                          ? 'bg-indigo-100/80 dark:bg-indigo-900/60 text-indigo-600 dark:text-indigo-300'
                          : 'bg-slate-100 dark:bg-slate-800/60 text-slate-400 dark:text-slate-500'
                      }`}>
                        {item.count}
                      </span>
                    </button>
                  );
                })}
              </div>
            )}
          </div>

          {/* 2. Experience Pill */}
          <div className="relative shrink-0">
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                setOpenDropdown(openDropdown === 'experience' ? null : 'experience');
              }}
              className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[13px] font-semibold transition-all border cursor-pointer select-none ${
                selectedExp !== null && selectedExp !== 2
                  ? 'bg-indigo-50 dark:bg-indigo-950/60 text-indigo-700 dark:text-indigo-300 border-indigo-300 dark:border-indigo-800 shadow-2xs'
                  : selectedExp === 2
                  ? 'bg-indigo-50/50 dark:bg-indigo-950/30 text-indigo-700 dark:text-indigo-300 border-indigo-200/80 dark:border-indigo-800/80'
                  : 'bg-slate-50 dark:bg-slate-900/60 text-slate-700 dark:text-slate-300 border-slate-200/90 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700 hover:bg-slate-100/60 dark:hover:bg-slate-800/40'
              }`}
            >
              <Layers className="h-3.5 w-3.5 text-slate-400 shrink-0" />
              <span>
                {selectedExp === 2
                  ? 'Experience: 2 Yrs'
                  : selectedExp !== null && selectedExp < 5
                  ? `Experience: ${selectedExp} Yrs`
                  : 'Experience'}
              </span>
              {selectedExp !== null && selectedExp !== 2 ? (
                <span
                  onClick={(e) => {
                    e.stopPropagation();
                    handleExpChange(2);
                  }}
                  className="ml-0.5 p-0.5 rounded hover:bg-indigo-200/60 dark:hover:bg-indigo-900/60 text-indigo-600 dark:text-indigo-400 cursor-pointer"
                  title="Reset to 2 Yrs default"
                >
                  <X className="h-3 w-3" />
                </span>
              ) : (
                <ChevronDown className={`h-3.5 w-3.5 text-slate-400 transition-transform ${openDropdown === 'experience' ? 'rotate-180' : ''}`} />
              )}
            </button>

            {openDropdown === 'experience' && (
              <div className="hidden sm:block absolute top-full left-0 mt-1.5 z-40 w-72 p-3.5 rounded-xl border border-slate-200/90 dark:border-slate-800 bg-white dark:bg-[#111726] shadow-xl space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-[12px] font-bold text-slate-900 dark:text-white">
                    Experience Range
                  </span>
                  <span className="px-1.5 py-0.2 rounded text-[10.5px] font-bold bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400 border border-indigo-200/60 dark:border-indigo-800/60">
                    {selectedExp !== null && selectedExp < 5 ? `${selectedExp} Yrs` : 'Any'}
                  </span>
                </div>

                <div className="relative pt-1 pb-1">
                  <input
                    type="range"
                    min="0"
                    max="5"
                    step="1"
                    value={selectedExp ?? 5}
                    onChange={(e) => {
                      const val = parseInt(e.target.value, 10);
                      handleExpChange(val >= 5 ? null : val);
                    }}
                    style={{
                      '--slider-fill': `${((selectedExp ?? 5) / 5) * 100}%`,
                    } as React.CSSProperties}
                    className="custom-range-slider"
                  />
                  <div className="flex justify-between text-[10.5px] text-slate-500 dark:text-slate-400 font-semibold mt-1 px-0.5">
                    <span className={selectedExp === 0 ? 'text-indigo-600 font-bold' : ''}>0 Yrs</span>
                    <span className={selectedExp === 1 ? 'text-indigo-600 font-bold' : ''}>1 Yr</span>
                    <span className={selectedExp === 2 ? 'text-indigo-600 dark:text-indigo-400 font-bold' : ''}>2 Yrs</span>
                    <span className={selectedExp === 3 ? 'text-indigo-600 font-bold' : ''}>3 Yrs</span>
                    <span className={selectedExp === null || selectedExp >= 5 ? 'text-indigo-600 dark:text-indigo-400 font-bold' : ''}>Any</span>
                  </div>
                </div>

                <button
                  type="button"
                  onClick={() => {
                    handleExpChange(2);
                    setOpenDropdown(null);
                  }}
                  className={`w-full text-left px-2.5 py-1.5 rounded-lg text-[11.5px] font-semibold border transition-all cursor-pointer flex items-center justify-between ${
                    selectedExp === 2
                      ? 'bg-indigo-50 dark:bg-indigo-950/40 border-indigo-300 dark:border-indigo-800 text-indigo-700 dark:text-indigo-300 shadow-2xs'
                      : 'bg-slate-50 dark:bg-slate-900 border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400 hover:border-slate-300'
                  }`}
                >
                  <div className="flex items-center gap-1.5">
                    <Layers className="h-3.5 w-3.5 text-indigo-600 dark:text-indigo-400 shrink-0" />
                    <span>2 Yrs (Target Level)</span>
                  </div>
                  {selectedExp === 2 && <span className="text-[9.5px] uppercase font-bold text-indigo-600">Active</span>}
                </button>
              </div>
            )}
          </div>

          {/* 3. Location Pill */}
          <div className="relative shrink-0">
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                setOpenDropdown(openDropdown === 'location' ? null : 'location');
              }}
              className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[13px] font-semibold transition-all border cursor-pointer select-none ${
                selectedLocation !== 'all'
                  ? 'bg-indigo-50 dark:bg-indigo-950/60 text-indigo-700 dark:text-indigo-300 border-indigo-300 dark:border-indigo-800 shadow-2xs'
                  : 'bg-slate-50 dark:bg-slate-900/60 text-slate-700 dark:text-slate-300 border-slate-200/90 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700 hover:bg-slate-100/60 dark:hover:bg-slate-800/40'
              }`}
            >
              <MapPin className="h-3.5 w-3.5 text-slate-400" />
              <span>
                {selectedLocation !== 'all'
                  ? (LOC_LABELS[selectedLocation] || selectedLocation)
                  : 'Location'}
              </span>
              {selectedLocation !== 'all' ? (
                <span
                  onClick={(e) => {
                    e.stopPropagation();
                    handleLocationChange(selectedLocation);
                  }}
                  className="ml-0.5 p-0.5 rounded hover:bg-indigo-200/60 dark:hover:bg-indigo-900/60 text-indigo-600 dark:text-indigo-400 cursor-pointer"
                  title="Clear location"
                >
                  <X className="h-3 w-3" />
                </span>
              ) : (
                <ChevronDown className={`h-3.5 w-3.5 text-slate-400 transition-transform ${openDropdown === 'location' ? 'rotate-180' : ''}`} />
              )}
            </button>

            {openDropdown === 'location' && (
              <div className="hidden sm:block absolute top-full left-0 mt-1.5 z-40 w-64 p-2 rounded-xl border border-slate-200/90 dark:border-slate-800 bg-white dark:bg-[#111726] shadow-xl space-y-1">
                <div className="px-2 py-1 text-[11px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider">
                  Select Location
                </div>
                {locationOptions.map((loc) => {
                  const isChecked = selectedLocation === loc.key;
                  return (
                    <button
                      key={loc.key}
                      type="button"
                      onClick={() => {
                        handleLocationChange(loc.key);
                        setOpenDropdown(null);
                      }}
                      className={`flex items-center justify-between w-full text-left text-[13px] px-2.5 py-1.5 rounded-lg transition-colors cursor-pointer select-none ${
                        isChecked
                          ? 'bg-indigo-50/70 dark:bg-indigo-950/40 text-indigo-700 dark:text-indigo-300 font-semibold'
                          : 'text-slate-700 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100/60 dark:hover:bg-slate-800/40'
                      }`}
                    >
                      <div className="flex items-center gap-2">
                        <div className={`h-3.5 w-3.5 rounded border flex items-center justify-center ${
                          isChecked
                            ? 'border-indigo-600 bg-indigo-600 text-white'
                            : 'border-slate-300 dark:border-slate-600'
                        }`}>
                          {isChecked && <Check className="h-2.5 w-2.5" />}
                        </div>
                        <span>{loc.label}</span>
                      </div>
                      <span className={`text-[11px] font-medium px-1.5 py-0.2 rounded-full tabular-nums ${
                        isChecked
                          ? 'bg-indigo-100/80 dark:bg-indigo-900/60 text-indigo-600 dark:text-indigo-300'
                          : 'bg-slate-100 dark:bg-slate-800/60 text-slate-400 dark:text-slate-500'
                      }`}>
                        {loc.count}
                      </span>
                    </button>
                  );
                })}
              </div>
            )}
          </div>

          {/* 4. Salary Pill */}
          <div className="relative shrink-0">
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                setOpenDropdown(openDropdown === 'salary' ? null : 'salary');
              }}
              className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[13px] font-semibold transition-all border cursor-pointer select-none ${
                selectedSalary !== 'all'
                  ? 'bg-indigo-50 dark:bg-indigo-950/60 text-indigo-700 dark:text-indigo-300 border-indigo-300 dark:border-indigo-800 shadow-2xs'
                  : 'bg-slate-50 dark:bg-slate-900/60 text-slate-700 dark:text-slate-300 border-slate-200/90 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700 hover:bg-slate-100/60 dark:hover:bg-slate-800/40'
              }`}
            >
              <Banknote className="h-3.5 w-3.5 text-slate-400" />
              <span>
                {selectedSalary !== 'all'
                  ? (SAL_LABELS[selectedSalary] || `${selectedSalary} LPA`)
                  : 'Salary'}
              </span>
              {selectedSalary !== 'all' ? (
                <span
                  onClick={(e) => {
                    e.stopPropagation();
                    handleSalaryChange(selectedSalary);
                  }}
                  className="ml-0.5 p-0.5 rounded hover:bg-indigo-200/60 dark:hover:bg-indigo-900/60 text-indigo-600 dark:text-indigo-400 cursor-pointer"
                  title="Clear salary"
                >
                  <X className="h-3 w-3" />
                </span>
              ) : (
                <ChevronDown className={`h-3.5 w-3.5 text-slate-400 transition-transform ${openDropdown === 'salary' ? 'rotate-180' : ''}`} />
              )}
            </button>

            {openDropdown === 'salary' && (
              <div className="hidden sm:block absolute top-full left-0 sm:left-auto sm:right-0 mt-1.5 z-40 w-64 p-2 rounded-xl border border-slate-200/90 dark:border-slate-800 bg-white dark:bg-[#111726] shadow-xl space-y-1">
                <div className="px-2 py-1 text-[11px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider">
                  Select Salary Range
                </div>
                {salaryOptions.map((sal) => {
                  const isChecked = selectedSalary === sal.key;
                  return (
                    <button
                      key={sal.key}
                      type="button"
                      onClick={() => {
                        handleSalaryChange(sal.key);
                        setOpenDropdown(null);
                      }}
                      className={`flex items-center justify-between w-full text-left text-[13px] px-2.5 py-1.5 rounded-lg transition-colors cursor-pointer select-none ${
                        isChecked
                          ? 'bg-indigo-50/70 dark:bg-indigo-950/40 text-indigo-700 dark:text-indigo-300 font-semibold'
                          : 'text-slate-700 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100/60 dark:hover:bg-slate-800/40'
                      }`}
                    >
                      <div className="flex items-center gap-2">
                        <div className={`h-3.5 w-3.5 rounded border flex items-center justify-center ${
                          isChecked
                            ? 'border-indigo-600 bg-indigo-600 text-white'
                            : 'border-slate-300 dark:border-slate-600'
                        }`}>
                          {isChecked && <Check className="h-2.5 w-2.5" />}
                        </div>
                        <span>{sal.label}</span>
                      </div>
                      <span className={`text-[11px] font-medium px-1.5 py-0.2 rounded-full tabular-nums ${
                        isChecked
                          ? 'bg-indigo-100/80 dark:bg-indigo-900/60 text-indigo-600 dark:text-indigo-300'
                          : 'bg-slate-100 dark:bg-slate-800/60 text-slate-400 dark:text-slate-500'
                      }`}>
                        {sal.count}
                      </span>
                    </button>
                  );
                })}
              </div>
            )}
          </div>

          {/* Reset Filters CTA */}
          {hasActiveFilters && (
            <button
              type="button"
              onClick={clearFilters}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[12.5px] font-semibold text-slate-500 hover:text-rose-600 dark:text-slate-400 dark:hover:text-rose-400 hover:bg-rose-50/60 dark:hover:bg-rose-950/40 transition-colors cursor-pointer shrink-0 sm:ml-auto"
            >
              <RotateCcw className="h-3.5 w-3.5" />
              <span>Reset filters</span>
            </button>
          )}
        </div>

        {/* Mobile Filter Bottom Sheet / Modal Drawer via React Portal */}
        {openDropdown && createPortal(
          <div id="mobile-filter-sheet" className="fixed inset-0 z-[9999] sm:hidden flex flex-col justify-end">
            {/* Backdrop */}
            <div
              className="fixed inset-0 bg-slate-950/70 backdrop-blur-xs transition-opacity"
              onClick={() => setOpenDropdown(null)}
            />

            {/* Bottom Sheet Modal */}
            <div
              className="relative z-10 w-full max-h-[85vh] overflow-y-auto rounded-t-3xl bg-white dark:bg-[#111726] border-t border-slate-200/90 dark:border-slate-800 p-5 shadow-2xl space-y-4"
              onClick={(e) => e.stopPropagation()}
            >
              {/* Drag Handle Bar */}
              <div className="mx-auto w-12 h-1.5 rounded-full bg-slate-300 dark:bg-slate-700 mb-2" />

              {/* Header */}
              <div className="flex items-center justify-between pb-3 border-b border-slate-100 dark:border-slate-800">
                <div className="flex items-center gap-2">
                  {openDropdown === 'workMode' && <Briefcase className="h-5 w-5 text-indigo-600 dark:text-indigo-400" />}
                  {openDropdown === 'experience' && <Layers className="h-5 w-5 text-indigo-600 dark:text-indigo-400" />}
                  {openDropdown === 'location' && <MapPin className="h-5 w-5 text-indigo-600 dark:text-indigo-400" />}
                  {openDropdown === 'salary' && <Banknote className="h-5 w-5 text-emerald-500" />}
                  <h3 className="text-[17px] font-bold text-slate-900 dark:text-white">
                    {openDropdown === 'workMode' && 'Select Work Mode'}
                    {openDropdown === 'experience' && 'Filter by Experience'}
                    {openDropdown === 'location' && 'Select Location'}
                    {openDropdown === 'salary' && 'Select Salary Bracket'}
                  </h3>
                </div>
                <button
                  type="button"
                  onClick={() => setOpenDropdown(null)}
                  className="p-1.5 rounded-full text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 bg-slate-100 dark:bg-slate-800 transition-colors"
                  aria-label="Close"
                >
                  <X className="h-4.5 w-4.5" />
                </button>
              </div>

              {/* Sheet Content for Work Mode */}
              {openDropdown === 'workMode' && (
                <div className="space-y-2">
                  <button
                    type="button"
                    onClick={() => {
                      handleWorkModeToggle('all');
                    }}
                    className={`flex items-center justify-between w-full text-left text-[14.5px] px-3.5 py-3 rounded-xl transition-colors cursor-pointer select-none ${
                      selectedWorkModesList.length === 0
                        ? 'bg-indigo-50 dark:bg-indigo-950/50 text-indigo-700 dark:text-indigo-300 font-semibold border border-indigo-200 dark:border-indigo-800'
                        : 'text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800/40 border border-slate-200/80 dark:border-slate-800/80'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <div className={`h-5 w-5 rounded-md border-2 shrink-0 flex items-center justify-center transition-colors ${
                        selectedWorkModesList.length === 0
                          ? 'border-indigo-600 bg-indigo-600 text-white'
                          : 'border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900'
                      }`}>
                        {selectedWorkModesList.length === 0 && <Check className="h-3.5 w-3.5 stroke-[3]" />}
                      </div>
                      <span className="font-medium">All Work Modes</span>
                    </div>
                  </button>
                  {workModeOptions.map((item) => {
                    const isChecked = selectedWorkModesList.includes(item.key);
                    return (
                      <button
                        key={item.key}
                        type="button"
                        onClick={() => {
                          handleWorkModeToggle(item.key);
                        }}
                        className={`flex items-center justify-between w-full text-left text-[14.5px] px-3.5 py-3 rounded-xl transition-colors cursor-pointer select-none ${
                          isChecked
                            ? 'bg-indigo-50 dark:bg-indigo-950/50 text-indigo-700 dark:text-indigo-300 font-semibold border border-indigo-200 dark:border-indigo-800'
                            : 'text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800/40 border border-slate-200/80 dark:border-slate-800/80'
                        }`}
                      >
                        <div className="flex items-center gap-3">
                          <div className={`h-5 w-5 rounded-md border-2 shrink-0 flex items-center justify-center transition-colors ${
                            isChecked
                              ? 'border-indigo-600 bg-indigo-600 text-white'
                              : 'border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900'
                          }`}>
                            {isChecked && <Check className="h-3.5 w-3.5 stroke-[3]" />}
                          </div>
                          <span className="font-medium">{item.label}</span>
                        </div>
                        <span className={`text-[12px] font-semibold px-2.5 py-1 rounded-full tabular-nums ${
                          isChecked
                            ? 'bg-indigo-100 dark:bg-indigo-900/60 text-indigo-700 dark:text-indigo-300'
                            : 'bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400'
                        }`}>
                          {item.count} jobs
                        </span>
                      </button>
                    );
                  })}

                  <div className="pt-3">
                    <button
                      type="button"
                      onClick={() => setOpenDropdown(null)}
                      className="w-full py-3 rounded-xl bg-indigo-600 text-white font-bold text-[14px] hover:bg-indigo-700 active:scale-98 transition-all cursor-pointer shadow-sm"
                    >
                      {selectedWorkModesList.length > 0 ? `Apply Filters (${selectedWorkModesList.length} Selected)` : 'Done'}
                    </button>
                  </div>
                </div>
              )}

              {/* Sheet Content for Experience */}
              {openDropdown === 'experience' && (
                <div className="space-y-4 pt-1">
                  <div className="flex items-center justify-between px-1">
                    <span className="text-[13px] font-bold text-slate-600 dark:text-slate-400 uppercase tracking-wider">
                      Target Level
                    </span>
                    <span className="px-2.5 py-1 rounded-lg text-xs font-bold bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400 border border-indigo-200/60 dark:border-indigo-800/60">
                      {selectedExp !== null && selectedExp < 5 ? `${selectedExp} Yrs Experience` : 'Any Experience'}
                    </span>
                  </div>

                  <div className="relative pt-2 pb-2 px-1">
                    <input
                      type="range"
                      min="0"
                      max="5"
                      step="1"
                      value={selectedExp ?? 5}
                      onChange={(e) => {
                        const val = parseInt(e.target.value, 10);
                        handleExpChange(val >= 5 ? null : val);
                      }}
                      style={{
                        '--slider-fill': `${((selectedExp ?? 5) / 5) * 100}%`,
                      } as React.CSSProperties}
                      className="custom-range-slider w-full"
                    />
                    <div className="flex justify-between text-xs text-slate-500 dark:text-slate-400 font-semibold mt-2 px-0.5">
                      <span className={selectedExp === 0 ? 'text-indigo-600 font-bold' : ''}>0 Yrs</span>
                      <span className={selectedExp === 1 ? 'text-indigo-600 font-bold' : ''}>1 Yr</span>
                      <span className={selectedExp === 2 ? 'text-indigo-600 dark:text-indigo-400 font-bold' : ''}>2 Yrs ★</span>
                      <span className={selectedExp === 3 ? 'text-indigo-600 font-bold' : ''}>3 Yrs</span>
                      <span className={selectedExp === null || selectedExp >= 5 ? 'text-indigo-600 dark:text-indigo-400 font-bold' : ''}>Any</span>
                    </div>
                  </div>

                  <div className="pt-2">
                    <button
                      type="button"
                      onClick={() => {
                        handleExpChange(2);
                        setOpenDropdown(null);
                      }}
                      className={`w-full text-left px-3.5 py-3 rounded-xl text-[13.5px] font-semibold border transition-all cursor-pointer flex items-center justify-between ${
                        selectedExp === 2
                          ? 'bg-indigo-50 dark:bg-indigo-950/40 border-indigo-300 dark:border-indigo-800 text-indigo-700 dark:text-indigo-300 shadow-2xs'
                          : 'bg-slate-50 dark:bg-slate-900 border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-300'
                      }`}
                    >
                      <div className="flex items-center gap-2">
                        <Sparkles className="h-4 w-4 text-amber-500 shrink-0" />
                        <span>2 Yrs Sweet Spot (Recommended)</span>
                      </div>
                      {selectedExp === 2 && <span className="text-[10px] uppercase font-bold text-indigo-600">Active</span>}
                    </button>
                  </div>

                  <div className="pt-2">
                    <button
                      type="button"
                      onClick={() => setOpenDropdown(null)}
                      className="w-full py-3 rounded-xl bg-indigo-600 text-white font-bold text-[14px] hover:bg-indigo-700 active:scale-98 transition-all"
                    >
                      Apply Filter
                    </button>
                  </div>
                </div>
              )}

              {/* Sheet Content for Location */}
              {openDropdown === 'location' && (
                <div className="space-y-2">
                  <button
                    type="button"
                    onClick={() => {
                      setSelectedLocation('all');
                      setCurrentPage(1);
                      updateUrlParam('location', null);
                      setOpenDropdown(null);
                    }}
                    className={`flex items-center justify-between w-full text-left text-[14.5px] px-3.5 py-3 rounded-xl transition-colors cursor-pointer select-none ${
                      selectedLocation === 'all'
                        ? 'bg-indigo-50 dark:bg-indigo-950/50 text-indigo-700 dark:text-indigo-300 font-semibold border border-indigo-200 dark:border-indigo-800'
                        : 'text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800/40 border border-slate-200/80 dark:border-slate-800/80'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <div className={`h-5 w-5 rounded-md border-2 shrink-0 flex items-center justify-center transition-colors ${
                        selectedLocation === 'all'
                          ? 'border-indigo-600 bg-indigo-600 text-white'
                          : 'border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900'
                      }`}>
                        {selectedLocation === 'all' && <Check className="h-3.5 w-3.5 stroke-[3]" />}
                      </div>
                      <span className="font-medium">All Locations</span>
                    </div>
                  </button>
                  {locationOptions.map((loc) => {
                    const isChecked = selectedLocation === loc.key;
                    return (
                      <button
                        key={loc.key}
                        type="button"
                        onClick={() => {
                          handleLocationChange(loc.key);
                          setOpenDropdown(null);
                        }}
                        className={`flex items-center justify-between w-full text-left text-[14.5px] px-3.5 py-3 rounded-xl transition-colors cursor-pointer select-none ${
                          isChecked
                            ? 'bg-indigo-50 dark:bg-indigo-950/50 text-indigo-700 dark:text-indigo-300 font-semibold border border-indigo-200 dark:border-indigo-800'
                            : 'text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800/40 border border-slate-200/80 dark:border-slate-800/80'
                        }`}
                      >
                        <div className="flex items-center gap-3">
                          <div className={`h-5 w-5 rounded-md border-2 shrink-0 flex items-center justify-center transition-colors ${
                            isChecked
                              ? 'border-indigo-600 bg-indigo-600 text-white'
                              : 'border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900'
                          }`}>
                            {isChecked && <Check className="h-3.5 w-3.5 stroke-[3]" />}
                          </div>
                          <span className="font-medium">{loc.label}</span>
                        </div>
                        <span className={`text-[12px] font-semibold px-2.5 py-1 rounded-full tabular-nums ${
                          isChecked
                            ? 'bg-indigo-100 dark:bg-indigo-900/60 text-indigo-700 dark:text-indigo-300'
                            : 'bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400'
                        }`}>
                          {loc.count} jobs
                        </span>
                      </button>
                    );
                  })}
                </div>
              )}

              {/* Sheet Content for Salary */}
              {openDropdown === 'salary' && (
                <div className="space-y-2">
                  <button
                    type="button"
                    onClick={() => {
                      setSelectedSalary('all');
                      setCurrentPage(1);
                      updateUrlParam('salary', null);
                      setOpenDropdown(null);
                    }}
                    className={`flex items-center justify-between w-full text-left text-[14.5px] px-3.5 py-3 rounded-xl transition-colors cursor-pointer select-none ${
                      selectedSalary === 'all'
                        ? 'bg-indigo-50 dark:bg-indigo-950/50 text-indigo-700 dark:text-indigo-300 font-semibold border border-indigo-200 dark:border-indigo-800'
                        : 'text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800/40 border border-slate-200/80 dark:border-slate-800/80'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <div className={`h-5 w-5 rounded-md border-2 shrink-0 flex items-center justify-center transition-colors ${
                        selectedSalary === 'all'
                          ? 'border-indigo-600 bg-indigo-600 text-white'
                          : 'border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900'
                      }`}>
                        {selectedSalary === 'all' && <Check className="h-3.5 w-3.5 stroke-[3]" />}
                      </div>
                      <span className="font-medium">All Salary Ranges</span>
                    </div>
                  </button>
                  {salaryOptions.map((sal) => {
                    const isChecked = selectedSalary === sal.key;
                    return (
                      <button
                        key={sal.key}
                        type="button"
                        onClick={() => {
                          handleSalaryChange(sal.key);
                          setOpenDropdown(null);
                        }}
                        className={`flex items-center justify-between w-full text-left text-[14.5px] px-3.5 py-3 rounded-xl transition-colors cursor-pointer select-none ${
                          isChecked
                            ? 'bg-indigo-50 dark:bg-indigo-950/50 text-indigo-700 dark:text-indigo-300 font-semibold border border-indigo-200 dark:border-indigo-800'
                            : 'text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800/40 border border-slate-200/80 dark:border-slate-800/80'
                        }`}
                      >
                        <div className="flex items-center gap-3">
                          <div className={`h-5 w-5 rounded-md border-2 shrink-0 flex items-center justify-center transition-colors ${
                            isChecked
                              ? 'border-indigo-600 bg-indigo-600 text-white'
                              : 'border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900'
                          }`}>
                            {isChecked && <Check className="h-3.5 w-3.5 stroke-[3]" />}
                          </div>
                          <span className="font-medium">{sal.label}</span>
                        </div>
                        <span className={`text-[12px] font-semibold px-2.5 py-1 rounded-full tabular-nums ${
                          isChecked
                            ? 'bg-indigo-100 dark:bg-indigo-900/60 text-indigo-700 dark:text-indigo-300'
                            : 'bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400'
                        }`}>
                          {sal.count} jobs
                        </span>
                      </button>
                    );
                  })}
                </div>
              )}
            </div>
          </div>,
          document.body
        )}

        {/* Active Filter Badges */}
        {activeFiltersList.length > 0 && (
          <div className="flex items-center gap-1.5 flex-wrap pt-2 border-t border-slate-100 dark:border-slate-800/60">
            <span className="text-[11px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider mr-1">
              Active:
            </span>
            {activeFiltersList.map((chip) => (
              <span
                key={chip.key}
                className="inline-flex items-center gap-1 pl-2.5 pr-1.5 py-0.5 rounded-lg text-[12px] font-semibold bg-slate-100 dark:bg-slate-800 text-slate-800 dark:text-slate-200 border border-slate-200/90 dark:border-slate-700/80 shadow-2xs group"
              >
                <span>{chip.label}</span>
                <button
                  type="button"
                  onClick={chip.onRemove}
                  className="p-0.5 rounded hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 transition-colors cursor-pointer"
                  aria-label={`Remove filter ${chip.label}`}
                >
                  <X className="h-3 w-3" />
                </button>
              </span>
            ))}
            <button
              type="button"
              onClick={clearFilters}
              className="text-[12px] font-semibold text-indigo-600 hover:text-indigo-700 dark:text-indigo-400 hover:underline ml-1 cursor-pointer"
            >
              Clear all
            </button>
          </div>
        )}
      </div>

      {/* -------------------------------------------------- */}
      {/* MAIN RESULTS FEED (Full Width)                     */}
      {/* -------------------------------------------------- */}
      <main className="w-full space-y-3.5">
          {/* Results Summary Toolbar */}
          <div className="flex items-center justify-between pb-0.5 px-0.5">
            <h2 className="text-[15.5px] font-bold text-slate-900 dark:text-white tracking-tight">
              {totalJobs} jobs found
            </h2>
          </div>

          {/* Jobs Feed Cards */}
          {isLoading ? (
            <div className="space-y-3">
              <CardSkeleton />
              <CardSkeleton />
              <CardSkeleton />
              <CardSkeleton />
            </div>
          ) : jobs.length === 0 ? (
            <div className="p-10 sm:p-14 text-center rounded-2xl border border-slate-200/90 dark:border-slate-800 bg-white dark:bg-[#111726] shadow-sm flex flex-col items-center justify-center">
              <div className="p-3.5 rounded-2xl bg-indigo-50 dark:bg-indigo-950/60 border border-indigo-100 dark:border-indigo-900/60 shadow-2xs text-indigo-600 dark:text-indigo-400 mb-4">
                <Search className="h-6 w-6 stroke-[2.2]" />
              </div>
              <h3 className="text-[17px] font-bold text-slate-900 dark:text-white">
                No matching opportunities found
              </h3>
              <p className="mt-1.5 text-[13.5px] text-slate-500 dark:text-slate-400 max-w-md leading-relaxed">
                We couldn't find any active roles matching your current filter criteria. Try clearing search keywords or relaxing work mode and location filters.
              </p>
              <button
                type="button"
                onClick={clearFilters}
                className="mt-5 inline-flex items-center gap-2 px-4 py-2 text-[13px] font-semibold bg-indigo-600 hover:bg-indigo-700 active:scale-95 text-white rounded-xl shadow-xs transition-all cursor-pointer"
              >
                <RotateCcw className="h-3.5 w-3.5" />
                <span>Reset All Filters</span>
              </button>
            </div>
          ) : (
            <div className="space-y-3 sm:space-y-3.5">
              {jobs.map((job) => {
                const isSaved = savedJobIds.has(job.id) || job.application_status === 'drafted' || job.application_status === 'saved';
                const isWfh = Boolean(
                  job.is_remote ||
                  job.location_bucket === 'REMOTE_INDIA' ||
                  job.location?.toLowerCase().includes('remote') ||
                  job.location?.toLowerCase().includes('wfh')
                );
                const isHybrid = !isWfh && Boolean(
                  job.location?.toLowerCase().includes('hybrid') ||
                  job.title?.toLowerCase().includes('hybrid')
                );
                const isAbroad = job.location_bucket === 'ABROAD';

                const displayLocation =
                  job.location ||
                  (isAbroad
                    ? 'Abroad / Relocation'
                    : isWfh
                    ? 'Remote'
                    : 'Bangalore');

                return (
                  <div
                    key={job.id}
                    onClick={() => setSelectedJobId(job.id)}
                    className="p-3.5 sm:py-3.5 sm:px-5 rounded-2xl border border-slate-200/80 dark:border-slate-800 bg-white dark:bg-[#111726] shadow-2xs hover:border-indigo-400 dark:hover:border-indigo-600/80 hover:shadow-xs transition-[border-color,box-shadow] duration-150 ease-out cursor-pointer group"
                  >
                    <div className="flex flex-col gap-2 sm:gap-2.5">
                      {/* Card Header: Avatar + Title & Company + Bookmark (Option A: Desktop Left Avatar, Mobile Top-Right Avatar + Bookmark) */}
                      <div className="flex items-start justify-between gap-3 sm:gap-3.5">
                        <div className="flex items-start gap-3 sm:gap-3.5 min-w-0 flex-1">
                          {/* Desktop Left Avatar */}
                          <div className="hidden sm:block shrink-0 p-1.5 rounded-xl bg-slate-50 dark:bg-slate-800/80 border border-slate-200/60 dark:border-slate-700/60 shadow-2xs">
                            <CompanyAvatar name={job.company_name} size="md" className="rounded-lg" />
                          </div>

                          <div className="min-w-0 flex-1">
                            <div className="flex items-start justify-between gap-2">
                              <div className="min-w-0 flex-1">
                                <h3 className="text-[15px] sm:text-[16px] font-bold text-slate-900 dark:text-white leading-snug tracking-tight group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors line-clamp-2">
                                  {job.title}
                                </h3>
                                <p className="text-[12.5px] sm:text-[13px] font-semibold text-slate-700 dark:text-slate-300 mt-0.5 truncate">
                                  {job.company_name}
                                </p>
                              </div>
                            </div>

                            {/* Line 1 Badges: Priority Tier + Match Score + Application Status */}
                            <div className="flex items-center gap-1.5 sm:gap-2 flex-wrap pt-1 sm:pt-1.5">
                              <TierBadge tier={job.priority_tier} />
                              <MatchScoreBadge score={job.relevance_score} matchPercentage={job.match_percentage} />
                              {job.application_status && (
                                <ApplicationStatusBadge status={job.application_status} size="sm" />
                              )}
                            </div>
                          </div>
                        </div>

                        {/* Desktop Actions: Timestamp + Bookmark + Apply Button */}
                        <div className="hidden sm:flex items-center gap-2.5 shrink-0 mt-0.5">
                          <span className="text-[12px] text-slate-400 dark:text-slate-500 font-medium whitespace-nowrap">
                            {formatRelativeTime(job.first_seen_at || job.last_seen_at)}
                          </span>

                          <button
                            type="button"
                            onClick={(e) => toggleSaveJob(e, job)}
                            className={`p-2 rounded-xl transition-all duration-150 active-pop cursor-pointer shrink-0 ${
                              isSaved
                                ? 'bg-amber-50 dark:bg-amber-950/40 text-amber-500 border border-amber-200/80 dark:border-amber-800/80 shadow-xs'
                                : 'text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800'
                            }`}
                            title={isSaved ? 'Job saved' : 'Save job'}
                          >
                            <Bookmark className={`h-4.5 w-4.5 transition-transform duration-150 ${isSaved ? 'fill-amber-500 text-amber-500 scale-105' : 'hover:scale-105'}`} />
                          </button>

                          {job.canonical_apply_url && (
                            <button
                              type="button"
                              onClick={(e) => handleApplyJob(e, job)}
                              className={`inline-flex items-center justify-center gap-1.5 px-4 py-2 text-[13px] sm:text-[13.5px] font-semibold rounded-xl active:scale-95 shadow-xs transition-all cursor-pointer whitespace-nowrap min-w-[102px] ${
                                job.application_status
                                  ? 'bg-indigo-50 hover:bg-indigo-100/90 text-indigo-700 border border-indigo-200/90 dark:bg-indigo-950/50 dark:text-indigo-300 dark:border-indigo-800/80 shadow-2xs'
                                  : 'bg-indigo-600 hover:bg-indigo-700 text-white shadow-xs'
                              }`}
                              title={job.application_status ? `Status: ${job.application_status}. Click to revisit link` : 'Open external link & mark as applied'}
                            >
                              <span>{job.application_status ? 'Apply Again' : 'Apply'}</span>
                              <ArrowUpRight className="h-4 w-4 shrink-0" />
                            </button>
                          )}
                        </div>
                      </div>

                      {/* Line 2: Location · Work Mode · Experience · Disclosed Salary */}
                      <div className="flex items-center gap-2 text-[12.5px] sm:text-[13px] text-slate-600 dark:text-slate-400 font-medium flex-wrap">
                        <span className="flex items-center gap-1.5">
                          {isAbroad ? (
                            <Plane className="h-3.5 w-3.5 text-indigo-500 shrink-0" />
                          ) : isWfh ? (
                            <Globe className="h-3.5 w-3.5 text-emerald-500 shrink-0" />
                          ) : (
                            <MapPin className="h-3.5 w-3.5 text-slate-400 shrink-0" />
                          )}
                          <span>{displayLocation}</span>
                        </span>

                        <span className="text-slate-300 dark:text-slate-700">·</span>

                        {/* Work Mode Capsule */}
                        {isWfh ? (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11.5px] font-medium bg-emerald-50/80 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-400 border border-emerald-200/60 dark:border-emerald-800/50">
                            <Home className="h-3 w-3 text-emerald-500 shrink-0" />
                            <span>Work from home</span>
                          </span>
                        ) : isHybrid ? (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11.5px] font-medium bg-indigo-50/80 dark:bg-indigo-950/40 text-indigo-700 dark:text-indigo-400 border border-indigo-200/60 dark:border-indigo-800/50">
                            <Building2 className="h-3 w-3 text-indigo-500 shrink-0" />
                            <span>Hybrid</span>
                          </span>
                        ) : isAbroad ? (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11.5px] font-medium bg-violet-50/80 dark:bg-violet-950/40 text-violet-700 dark:text-violet-400 border border-violet-200/60 dark:border-violet-800/50">
                            <Plane className="h-3 w-3 text-violet-500 shrink-0" />
                            <span>Relocation</span>
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11.5px] font-medium bg-slate-100/80 dark:bg-slate-800/80 text-slate-600 dark:text-slate-400 border border-slate-200/60 dark:border-slate-700/60">
                            <Building2 className="h-3 w-3 text-slate-400 shrink-0" />
                            <span>In-office</span>
                          </span>
                        )}

                        <span className="text-slate-300 dark:text-slate-700">·</span>
                        <span className="flex items-center gap-1.5">
                          <Briefcase className="h-3.5 w-3.5 text-slate-400 shrink-0" />
                          <span>{job.experience_raw || (job.experience_min !== null ? `${job.experience_min}–${job.experience_max || job.experience_min + 2} Yrs` : '0–2 Yrs')}</span>
                        </span>
                        {isValidSalary(job.salary_raw) && (
                          <>
                            <span className="text-slate-300 dark:text-slate-700">·</span>
                            <span className="inline-flex items-center gap-1 font-semibold text-emerald-600 dark:text-emerald-400 text-[12.5px] sm:text-[13px]">
                              <Banknote className="h-3.5 w-3.5 text-emerald-500 shrink-0" />
                              <span>{job.salary_raw}</span>
                            </span>
                          </>
                        )}
                      </div>

                      {/* Line 3: Dedicated Skill Capsules */}
                      {job.matched_skills && job.matched_skills.length > 0 && (
                        <div className="flex items-center gap-1.5 flex-wrap pt-0.5">
                          {job.matched_skills.slice(0, 6).map((skill, i) => (
                            <span
                              key={i}
                              className="px-2.5 sm:px-3 py-0.5 sm:py-0.5 rounded-lg bg-slate-100 dark:bg-slate-800 text-[11.5px] sm:text-[12px] text-slate-600 dark:text-slate-300 font-medium"
                            >
                              {skill}
                            </span>
                          ))}
                          {job.matched_skills.length > 6 && (
                            <span className="px-2 py-0.5 rounded-lg bg-slate-100/70 dark:bg-slate-800/60 text-[11px] sm:text-[11.5px] text-slate-400 dark:text-slate-500 font-semibold">
                              +{job.matched_skills.length - 6}
                            </span>
                          )}
                        </div>
                      )}

                      {/* Mobile Dedicated Bottom Action Bar (<sm only) */}
                      <div className="sm:hidden pt-2.5 mt-0.5 border-t border-slate-100 dark:border-slate-800/80 flex items-center justify-between">
                        <span className="text-[11.5px] text-slate-400 dark:text-slate-500 font-medium flex items-center gap-1">
                          <Clock className="h-3 w-3 text-slate-400 shrink-0" />
                          <span>{formatRelativeTime(job.first_seen_at || job.last_seen_at)}</span>
                        </span>

                        <div className="flex items-center gap-2">
                          <button
                            type="button"
                            onClick={(e) => toggleSaveJob(e, job)}
                            className={`p-2.5 rounded-xl transition-all duration-150 active-pop cursor-pointer ${
                              isSaved
                                ? 'bg-amber-50 dark:bg-amber-950/40 text-amber-500 border border-amber-200/80 dark:border-amber-800/80 shadow-xs'
                                : 'text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800'
                            }`}
                            title={isSaved ? 'Job saved' : 'Save job'}
                          >
                            <Bookmark className={`h-4.5 w-4.5 transition-transform duration-150 ${isSaved ? 'fill-amber-500 text-amber-500 scale-105' : 'hover:scale-105'}`} />
                          </button>

                          {job.canonical_apply_url && (
                            <button
                              type="button"
                              onClick={(e) => handleApplyJob(e, job)}
                              className={`inline-flex items-center justify-center gap-1.5 px-4 py-2 text-[13px] font-bold rounded-xl active:scale-95 shadow-xs transition-all cursor-pointer whitespace-nowrap min-w-[88px] ${
                                job.application_status
                                  ? 'bg-indigo-50 hover:bg-indigo-100/90 text-indigo-700 border border-indigo-200/90 dark:bg-indigo-950/50 dark:text-indigo-300 dark:border-indigo-800/80 shadow-2xs'
                                  : 'bg-indigo-600 hover:bg-indigo-700 text-white shadow-xs'
                              }`}
                            >
                              <span>{job.application_status ? 'Apply Again' : 'Apply'}</span>
                              <ArrowUpRight className="h-4 w-4 shrink-0" />
                            </button>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {/* Pagination Bar */}
          {totalJobs > 0 && (
            <div className="pt-2">
              <Pagination
                currentPage={currentPage}
                totalPages={totalPages}
                totalItems={totalJobs}
                pageSize={pageSize}
                pageSizeOptions={[5, 10, 25, 50]}
                itemLabel="jobs"
                onPageChange={(p) => setCurrentPage(p)}
                onPageSizeChange={(sz) => {
                  setPageSize(sz);
                  setCurrentPage(1);
                }}
              />
            </div>
          )}
        </main>

      {/* Slide-over Job Details Drawer */}
      <JobDetailDrawer
        jobId={selectedJobId}
        onClose={() => setSelectedJobId(null)}
        onJobUpdated={fetchJobs}
      />
    </div>
  );
};

export default JobsPage;
