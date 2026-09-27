import React, { useState, useEffect, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  Search,
  ArrowUpRight,
  ArrowUpDown,
  X,
  MapPin,
  Briefcase,
  Layers,
  Banknote,
  Globe,
  RotateCcw,
  Loader2,
} from 'lucide-react';
import { getJobs } from '../api';
import { useDiscovery } from '../context/DiscoveryContext';
import type { JobSummary } from '../types';
import { TierBadge, MatchScoreBadge } from '../components/ui/Badge';
import { CompanyAvatar } from '../components/ui/CompanyAvatar';
import { Pagination } from '../components/ui/Pagination';
import { JobDetailDrawer } from './JobDetailDrawer';
import { CardSkeleton } from '../components/ui/Skeleton';

export const JobsPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const { lastRunAt } = useDiscovery();

  const [jobs, setJobs] = useState<JobSummary[]>([]);
  const [totalJobs, setTotalJobs] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState<number>(() => {
    const saved = localStorage.getItem('careerpilot_feed_default_page_size');
    return saved ? parseInt(saved, 10) : 10;
  });
  const [isLoading, setIsLoading] = useState(true);

  // Filters
  const [searchQuery, setSearchQuery] = useState(searchParams.get('search') || '');
  const [selectedTier, setSelectedTier] = useState<string>(() => {
    return searchParams.get('tier') || 'all';
  });
  const [selectedLocation, setSelectedLocation] = useState(searchParams.get('location') || 'all');
  const [isRemoteOnly, setIsRemoteOnly] = useState(searchParams.get('remote') === 'true');
  const [selectedMinScore, setSelectedMinScore] = useState<number | null>(() => {
    const fromUrl = searchParams.get('min_score');
    return fromUrl ? parseFloat(fromUrl) : null;
  });

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
    const urlRemote = searchParams.get('remote') === 'true';
    const urlMinScore = searchParams.get('min_score');
    const urlSelected = searchParams.get('selected');

    setSearchQuery((prev) => (prev !== urlSearch ? urlSearch : prev));
    setSelectedTier((prev) => (prev !== urlTier ? urlTier : prev));
    setSelectedLocation((prev) => (prev !== urlLoc ? urlLoc : prev));
    setIsRemoteOnly((prev) => (prev !== urlRemote ? urlRemote : prev));
    setSelectedMinScore((prev) => {
      const parsed = urlMinScore ? parseFloat(urlMinScore) : null;
      return prev !== parsed ? parsed : prev;
    });
    if (urlSelected) {
      const parsedId = parseInt(urlSelected, 10);
      setSelectedJobId((prev) => (prev !== parsedId ? parsedId : prev));
    }
  }, [searchParams]);

  useEffect(() => {
    fetchJobs();
  }, [currentPage, pageSize, selectedTier, selectedLocation, isRemoteOnly, selectedMinScore, lastRunAt]);

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
      if (isRemoteOnly) params.is_remote = true;
      if (selectedMinScore !== null) params.min_score = selectedMinScore;

      const res = await getJobs(params);
      if (requestId !== activeRequestIdRef.current) {
        return; // Discard outdated response from older request
      }
      setJobs(res.items);
      setTotalJobs(res.meta.total);
      setTotalPages(res.meta.total_pages);
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

  const handleTierChange = (tier: string) => {
    setSelectedTier(tier);
    setCurrentPage(1);
    updateUrlParam('tier', tier === 'all' ? null : tier);
  };

  const handleLocationChange = (loc: string) => {
    setSelectedLocation(loc);
    setCurrentPage(1);
    updateUrlParam('location', loc === 'all' ? null : loc);
  };

  const handleScoreChange = (score: number | null) => {
    setSelectedMinScore(score);
    setCurrentPage(1);
    updateUrlParam('min_score', score !== null ? score.toString() : null);
  };

  const handleRemoteToggle = () => {
    const nextVal = !isRemoteOnly;
    setIsRemoteOnly(nextVal);
    setCurrentPage(1);
    updateUrlParam('remote', nextVal ? 'true' : null);
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
    setIsRemoteOnly(false);
    setSelectedMinScore(null);
    setCurrentPage(1);
    setSearchParams(new URLSearchParams(), { replace: true });
    fetchJobs('');
  };

  const activeFilterCount =
    (selectedTier !== 'all' ? 1 : 0) +
    (selectedLocation !== 'all' ? 1 : 0) +
    (isRemoteOnly ? 1 : 0) +
    (selectedMinScore !== null ? 1 : 0) +
    (searchQuery.trim() !== '' ? 1 : 0);

  const hasActiveFilters = activeFilterCount > 0;

  const startItem = totalJobs === 0 ? 0 : (currentPage - 1) * pageSize + 1;
  const endItem = Math.min(currentPage * pageSize, totalJobs);

  return (
    <div className="space-y-6">
      {/* -------------------------------------------------- */}
      {/* PAGE HEADER                                        */}
      {/* -------------------------------------------------- */}
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-[28px] sm:text-[32px] font-bold tracking-tight text-slate-900 dark:text-white">
              Jobs Feed
            </h1>
            {/* Subtle active count — neutral, no icon, secondary */}
            <span className="px-2 py-0.5 rounded-md text-[13.5px] font-semibold bg-slate-100 dark:bg-slate-800 text-slate-800 dark:text-slate-400 border border-slate-200 dark:border-slate-700 self-center mt-1">
              {totalJobs} active
            </span>
          </div>
          <p className="mt-1 text-[13.5px] text-slate-800 dark:text-slate-300">
            Browse vetted backend &amp; engineering roles prioritized for maximum profile fit.
          </p>
        </div>
      </div>

      {/* -------------------------------------------------- */}
      {/* SEARCH + FILTER CARD                              */}
      {/* -------------------------------------------------- */}
      <div className="p-4 sm:p-5 rounded-2xl border border-slate-200/80 dark:border-slate-800 bg-white dark:bg-[#111726] shadow-sm space-y-4">
        {/* Search Row - Trial 1: Unified Command-Bar Style */}
        <form onSubmit={handleSearchSubmit} className="relative">
          <div className="group relative flex items-center p-1 sm:p-1.5 rounded-xl border border-slate-200/90 dark:border-slate-700/80 bg-slate-50/70 dark:bg-slate-900/50 shadow-xs hover:border-slate-300 dark:hover:border-slate-600 focus-within:border-indigo-500 dark:focus-within:border-indigo-500 focus-within:bg-white dark:focus-within:bg-[#0f1422] focus-within:ring-4 focus-within:ring-indigo-500/15 focus-within:shadow-md focus-within:shadow-indigo-500/5 transition-all duration-300 ease-out">
            <Search className="h-4.5 w-4.5 ml-2.5 text-slate-600 dark:text-slate-300 group-focus-within:text-indigo-600 dark:group-focus-within:text-indigo-400 group-focus-within:scale-110 transition-all duration-300 ease-out shrink-0" />

            <input
              ref={searchInputRef}
              type="text"
              placeholder="Search by job title, company, or skills (e.g. Python, Tech Lead, Razorpay)..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full h-10 bg-transparent border-0 px-3 text-[14.5px] text-slate-900 dark:text-slate-100 placeholder:text-slate-700 dark:placeholder:text-slate-300 font-medium focus:outline-none focus:ring-0 leading-normal"
            />

            <div className="flex items-center gap-1.5 shrink-0 pr-1">
              {searchQuery ? (
                <button
                  type="button"
                  onClick={handleClearSearch}
                  className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-200/60 dark:hover:bg-slate-800 hover:scale-105 active:scale-95 transition-all duration-200 cursor-pointer animate-in fade-in zoom-in-90"
                  title="Clear search"
                >
                  <X className="h-4 w-4" />
                </button>
              ) : (
                <div className="hidden sm:flex items-center gap-1 px-2 py-1 rounded-md bg-white dark:bg-slate-800/90 border border-slate-200/90 dark:border-slate-700/80 text-[11px] font-semibold text-slate-400 dark:text-slate-400 shadow-2xs select-none transition-opacity duration-200">
                  <span>Ctrl</span>
                  <span>K</span>
                </div>
              )}

              <button
                type="submit"
                disabled={isLoading}
                className="group/btn h-9 px-4 sm:px-5 text-[13.5px] font-semibold rounded-lg bg-gradient-to-r from-indigo-600 via-indigo-600 to-indigo-700 hover:from-indigo-500 hover:to-indigo-600 active:scale-[0.97] text-white shadow-xs hover:shadow-md hover:shadow-indigo-500/25 transition-all duration-200 ease-out cursor-pointer flex items-center gap-1.5 shrink-0 disabled:opacity-85"
              >
                {isLoading ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <Search className="h-3.5 w-3.5 transition-transform duration-200 ease-out group-hover/btn:scale-110 group-hover/btn:-rotate-6" />
                )}
                <span>{isLoading ? 'Searching...' : 'Search'}</span>
              </button>
            </div>
          </div>
        </form>

        {/* Filter Groups */}
        <div className="flex flex-wrap items-center justify-between gap-y-3 gap-x-6 pt-3.5 border-t border-slate-100 dark:border-slate-800/80">
          <div className="flex flex-wrap items-center gap-x-5 gap-y-3">
            {/* ── TIER ── */}
            <div className="flex items-center gap-2">
              <span className="text-[11.5px] font-semibold text-slate-700 dark:text-slate-400 uppercase tracking-wider shrink-0">
                Tier
              </span>
              <div className="inline-flex items-center p-0.5 rounded-lg bg-slate-100/90 dark:bg-slate-800/80 border border-slate-200/60 dark:border-slate-700/60">
                {['all', 'Tier 1', 'Tier 2'].map((tier) => (
                  <button
                    key={tier}
                    type="button"
                    onClick={() => handleTierChange(tier)}
                    className={`h-7 px-3 rounded-md text-[13px] font-medium transition-all cursor-pointer ${selectedTier === tier
                      ? 'bg-indigo-600 text-white font-semibold shadow-xs'
                      : 'text-slate-700 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white'
                      }`}
                  >
                    {tier === 'all' ? 'All' : tier}
                  </button>
                ))}
              </div>
            </div>

            <div className="h-4 w-px bg-slate-400 dark:bg-slate-700 hidden sm:block" />

            {/* ── MATCH ── */}
            <div className="flex items-center gap-2">
              <span className="text-[11.5px] font-semibold text-slate-700 dark:text-slate-400 uppercase tracking-wider shrink-0">
                Match
              </span>
              <div className="inline-flex items-center p-0.5 rounded-lg bg-slate-100/90 dark:bg-slate-800/80 border border-slate-200/60 dark:border-slate-700/60">
                {[
                  { label: 'All', value: null },
                  { label: '90%+', value: 90 },
                  { label: '80%+', value: 80 },
                  { label: '70%+', value: 70 },
                ].map((m) => (
                  <button
                    key={m.label}
                    type="button"
                    onClick={() => handleScoreChange(m.value)}
                    className={`h-7 px-3 rounded-md text-[13px] font-medium transition-all cursor-pointer ${selectedMinScore === m.value
                      ? 'bg-indigo-600 text-white font-semibold shadow-xs'
                      : 'text-slate-700 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white'
                      }`}
                  >
                    {m.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="h-4 w-px bg-slate-200 dark:bg-slate-700 hidden sm:block" />

            {/* ── LOCATION ── */}
            <div className="flex items-center gap-2">
              <span className="text-[11.5px] font-semibold text-slate-700 dark:text-slate-400 uppercase tracking-wider shrink-0">
                Location
              </span>
              <div className="inline-flex items-center p-0.5 rounded-lg bg-slate-100/90 dark:bg-slate-800/80 border border-slate-200/60 dark:border-slate-700/60">
                {[
                  { label: 'All', value: 'all' },
                  { label: 'Bangalore', value: 'Bangalore' },
                  { label: 'Chennai', value: 'Chennai' },
                ].map((loc) => (
                  <button
                    key={loc.value}
                    type="button"
                    onClick={() => handleLocationChange(loc.value)}
                    className={`h-7 px-3 rounded-md text-[13px] font-medium transition-all cursor-pointer ${selectedLocation === loc.value
                      ? 'bg-indigo-600 text-white font-semibold shadow-xs'
                      : 'text-slate-700 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white'
                      }`}
                  >
                    {loc.label}
                  </button>
                ))}
              </div>

              {/* Remote Toggle */}
              <button
                type="button"
                onClick={handleRemoteToggle}
                className={`inline-flex items-center gap-1.5 h-8 px-3 rounded-lg text-[13px] font-medium border transition-all cursor-pointer ${isRemoteOnly
                  ? 'bg-indigo-600 border-indigo-600 text-white font-semibold shadow-xs'
                  : 'bg-slate-100/90 dark:bg-slate-800/80 border-slate-200/60 dark:border-slate-700/60 text-slate-700 dark:text-slate-300 hover:bg-slate-200/70 dark:hover:bg-slate-700/70'
                  }`}
              >
                <Globe className="h-3.5 w-3.5" />
                <span>Remote</span>
              </button>
            </div>
          </div>

          {/* Clear Filters */}
          {hasActiveFilters && (
            <button
              type="button"
              onClick={clearFilters}
              className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[12.5px] font-medium text-rose-600 hover:text-rose-700 dark:text-rose-400 hover:bg-rose-50 dark:hover:bg-rose-950/40 cursor-pointer transition-colors shrink-0"
              title="Reset all filters"
            >
              <RotateCcw className="h-3.5 w-3.5" />
              <span>Reset filters ({activeFilterCount})</span>
            </button>
          )}
        </div>
      </div>

      {/* -------------------------------------------------- */}
      {/* RESULT TOOLBAR                                     */}
      {/* -------------------------------------------------- */}
      <div className="flex items-center justify-between text-xs px-1">
        {/* Result count — differentiated weights */}
        <span className="text-slate-800 dark:text-slate-500">
          Showing{' '}
          <strong className="font-bold text-slate-800 dark:text-slate-200">
            {startItem}–{endItem}
          </strong>{' '}
          of {totalJobs} jobs
        </span>

        {/* Sort — styled read-only compact chip, no clickable action (single sort mode) */}
        <span className="inline-flex h-7 items-center gap-1.5 px-2.5 rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111726] text-xs font-semibold text-slate-700 dark:text-slate-300 shadow-2xs select-none">
          <ArrowUpDown className="h-3 w-3 text-slate-800" />
          Best Match
        </span>
      </div>

      {/* Jobs Feed List */}
      {isLoading ? (
        <div className="space-y-4">
          <CardSkeleton />
          <CardSkeleton />
          <CardSkeleton />
          <CardSkeleton />
        </div>
      ) : jobs.length === 0 ? (
        <div className="p-12 text-center rounded-2xl border border-dashed border-slate-300 dark:border-slate-800 bg-white/50 dark:bg-slate-900/30">
          <p className="text-sm font-medium text-slate-600 dark:text-slate-400">
            No matching jobs found with the current filters.
          </p>
          <button
            onClick={clearFilters}
            className="mt-3 px-4 py-2 text-xs font-semibold bg-indigo-600 text-white rounded-xl shadow-xs hover:bg-indigo-700 cursor-pointer transition-colors"
          >
            Reset Filters
          </button>
        </div>
      ) : (
        <div className="space-y-3.5">
          {jobs.map((job) => {
            const sourceDisplay =
              job.ats_provider ||
              (job.apply_type === 'COMPANY_CAREERS'
                ? 'Company Site'
                : `${job.source_count} source${job.source_count > 1 ? 's' : ''}`);

            return (
              <div
                key={job.id}
                onClick={() => setSelectedJobId(job.id)}
                className="p-5 sm:p-6 rounded-2xl border border-slate-200/80 dark:border-slate-800 bg-white dark:bg-[#111726] shadow-sm hover:border-indigo-300 dark:hover:border-indigo-700/60 hover:shadow-md hover:-translate-y-0.5 transition-[transform,box-shadow,border-color] duration-180 ease-out cursor-pointer group"
              >
                <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
                  {/* Left: Avatar + Details */}
                  <div className="flex items-start gap-4 min-w-0">
                    <CompanyAvatar name={job.company_name} size="lg" />
                    <div className="min-w-0 space-y-1.5">
                      {/* Row 1: Title + Badges */}
                      <div className="flex items-center gap-2.5 flex-wrap">
                        <h3 className="text-[16px] sm:text-[17px] font-semibold text-slate-900 dark:text-white leading-snug truncate group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors">
                          {job.title}
                        </h3>
                        <div className="flex items-center gap-1.5 shrink-0">
                          <TierBadge tier={job.priority_tier} />
                          <MatchScoreBadge score={job.relevance_score} />
                        </div>
                      </div>

                      {/* Row 2: Company + Metadata */}
                      <div className="flex items-center gap-2.5 text-xs text-slate-500 dark:text-slate-400 flex-wrap">
                        <span className="font-semibold text-slate-800 dark:text-slate-200 text-[14px]">
                          {job.company_name}
                        </span>
                        <span className="text-slate-400 dark:text-slate-700">•</span>
                        <span className="flex items-center gap-1 text-slate-700 dark:text-slate-400">
                          <MapPin className="h-3.5 w-3.5 text-slate-700 shrink-0" />
                          {job.location || (job.is_remote ? 'Remote' : 'Location not specified')} {job.is_remote && job.location ? '(Remote)' : ''}
                        </span>
                        {job.experience_raw && (
                          <>
                            <span className="text-slate-400 dark:text-slate-700">•</span>
                            <span className="flex items-center gap-1 text-slate-700 dark:text-slate-400">
                              <Briefcase className="h-3.5 w-3.5 text-slate-700 shrink-0" />
                              {job.experience_raw}
                            </span>
                          </>
                        )}
                        {job.salary_raw && (
                          <>
                            <span className="text-slate-400 dark:text-slate-700">•</span>
                            <span className="flex items-center gap-1 text-slate-700 dark:text-slate-400">
                              <Banknote className="h-3.5 w-3.5 text-slate-700 shrink-0" />
                              {job.salary_raw}
                            </span>
                          </>
                        )}
                        <span className="text-slate-400 dark:text-slate-700">•</span>
                        <span className="flex items-center gap-1 text-[13px] text-slate-700 dark:text-slate-400">
                          <Layers className="h-3 w-3 shrink-0" />
                          {sourceDisplay}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Right: Actions Hierarchy (Inspect = Secondary, Apply = Primary) */}
                  <div className="flex items-center gap-2 sm:self-start shrink-0 pt-1 sm:pt-0">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelectedJobId(job.id);
                      }}
                      className="px-3 py-2 text-[14px] font-semibold rounded-xl bg-slate-100 hover:bg-slate-300 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 transition-colors cursor-pointer"
                    >
                      Inspect
                    </button>

                    {job.canonical_apply_url && (
                      <a
                        href={job.canonical_apply_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        onClick={(e) => e.stopPropagation()}
                        className="inline-flex items-center gap-1 px-3 py-2 text-[14px] font-semibold rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white shadow-xs transition-colors"
                        title="Direct application on company portal"
                      >
                        <span>Apply</span>
                        <ArrowUpRight className="h-3.5 w-3.5" />
                      </a>
                    )}
                  </div>
                </div>

                {/* Skills Tags */}
                {job.matched_skills && job.matched_skills.length > 0 && (
                  <div className="mt-3.5 pt-3 border-t border-slate-100 dark:border-slate-800/80 flex flex-wrap gap-1.5 items-center">
                    <span className="text-[12px] font-bold text-slate-600 dark:text-slate-500 uppercase tracking-wider mr-1">
                      Matched:
                    </span>
                    {job.matched_skills.slice(0, 6).map((skill, i) => (
                      <span
                        key={i}
                        className="px-2.5 py-0.5 text-[12px] font-semibold rounded-md bg-slate-100/70 dark:bg-slate-800/60 text-slate-700 dark:text-slate-300 border border-slate-300/60 dark:border-slate-700/60 transition-colors"
                      >
                        {skill}
                      </span>
                    ))}
                    {job.matched_skills.length > 6 && (
                      <span className="text-[11px] text-slate-500 dark:text-slate-500 font-semibold ml-0.5">
                        +{job.matched_skills.length - 6} more
                      </span>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Pagination Bar */}
      {totalJobs > 0 && (
        <Pagination
          currentPage={currentPage}
          totalPages={totalPages}
          totalItems={totalJobs}
          pageSize={pageSize}
          pageSizeOptions={[5, 10, 25, 100]}
          itemLabel="jobs"
          onPageChange={(p) => setCurrentPage(p)}
          onPageSizeChange={(sz) => {
            setPageSize(sz);
            setCurrentPage(1);
          }}
        />
      )}

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
