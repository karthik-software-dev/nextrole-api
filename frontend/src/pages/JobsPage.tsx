import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  Search,
  Filter,
  ArrowUpRight,
  SlidersHorizontal,
  X,
  ChevronLeft,
  ChevronRight,
  Sparkles,
  MapPin,
  Briefcase,
  Layers,
} from 'lucide-react';
import { getJobs } from '../api';
import { useDiscovery } from '../context/DiscoveryContext';
import type { JobSummary, PaginatedResponse } from '../types';
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
  const [pageSize, setPageSize] = useState(10);
  const [isLoading, setIsLoading] = useState(true);

  // Filters
  const [searchQuery, setSearchQuery] = useState(searchParams.get('search') || '');
  const [selectedTier, setSelectedTier] = useState(searchParams.get('tier') || 'all');
  const [selectedLocation, setSelectedLocation] = useState(searchParams.get('location') || 'all');
  const [isRemoteOnly, setIsRemoteOnly] = useState(searchParams.get('remote') === 'true');

  // Selected Job for Slide-over Drawer
  const [selectedJobId, setSelectedJobId] = useState<number | null>(() => {
    const fromUrl = searchParams.get('selected');
    return fromUrl ? parseInt(fromUrl, 10) : null;
  });

  // Sync state if URL query params change (e.g. from top nav search)
  useEffect(() => {
    const urlSearch = searchParams.get('search') || '';
    const urlTier = searchParams.get('tier') || 'all';
    const urlLoc = searchParams.get('location') || 'all';
    const urlRemote = searchParams.get('remote') === 'true';
    const urlSelected = searchParams.get('selected');

    setSearchQuery(urlSearch);
    setSelectedTier(urlTier);
    setSelectedLocation(urlLoc);
    setIsRemoteOnly(urlRemote);
    if (urlSelected) {
      setSelectedJobId(parseInt(urlSelected, 10));
    }
  }, [searchParams]);

  useEffect(() => {
    fetchJobs();
  }, [currentPage, pageSize, selectedTier, selectedLocation, isRemoteOnly, lastRunAt]);

  const fetchJobs = async () => {
    try {
      setIsLoading(true);
      const params: any = {
        page: currentPage,
        page_size: pageSize,
        active_only: true,
      };
      if (searchQuery.trim()) params.search = searchQuery.trim();
      if (selectedTier !== 'all') params.tier = selectedTier;
      if (selectedLocation !== 'all') params.location = selectedLocation;
      if (isRemoteOnly) params.is_remote = true;

      const res = await getJobs(params);
      setJobs(res.items);
      setTotalJobs(res.meta.total);
      setTotalPages(res.meta.total_pages);
    } catch (err) {
      console.error('Failed to fetch jobs:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setCurrentPage(1);
    fetchJobs();
  };

  const clearFilters = () => {
    setSearchQuery('');
    setSelectedTier('all');
    setSelectedLocation('all');
    setIsRemoteOnly(false);
    setCurrentPage(1);
  };

  const hasActiveFilters = searchQuery !== '' || selectedTier !== 'all' || selectedLocation !== 'all' || isRemoteOnly;

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
            Jobs Feed
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            Browse {totalJobs} vetted lead backend & engineering roles prioritized for maximum fit.
          </p>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800/80 bg-white dark:bg-slate-900/60 shadow-xs space-y-4">
        <form onSubmit={handleSearchSubmit} className="flex flex-col sm:flex-row gap-3">
          <div className="relative flex-1">
            <Search className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              placeholder="Search by job title, company, or skills (e.g. Python, Tech Lead, Razorpay)..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-lg pl-9 pr-4 py-2 text-xs sm:text-sm text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:border-indigo-500"
            />
          </div>
          <button
            type="submit"
            className="px-4 py-2 text-xs font-semibold rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white shadow-xs transition-colors cursor-pointer"
          >
            Search
          </button>
        </form>

        {/* Filter Pills */}
        <div className="flex flex-wrap items-center justify-between gap-3 pt-2 border-t border-slate-100 dark:border-slate-800/80">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider mr-1">
              Tier:
            </span>
            {['all', 'Tier 1', 'Tier 2'].map((tier) => (
              <button
                key={tier}
                onClick={() => {
                  setSelectedTier(tier);
                  setCurrentPage(1);
                }}
                className={`px-3 py-1 rounded-lg text-xs font-medium transition-colors cursor-pointer ${
                  selectedTier === tier
                    ? 'bg-indigo-600 text-white font-semibold'
                    : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700'
                }`}
              >
                {tier === 'all' ? 'All Tiers' : tier}
              </button>
            ))}

            <div className="h-4 w-px bg-slate-200 dark:bg-slate-700 mx-1 hidden sm:block" />

            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider mr-1">
              Location:
            </span>
            {[
              { label: 'All Locations', value: 'all' },
              { label: 'Bangalore', value: 'Bangalore' },
              { label: 'Chennai', value: 'Chennai' },
            ].map((loc) => (
              <button
                key={loc.value}
                onClick={() => {
                  setSelectedLocation(loc.value);
                  setCurrentPage(1);
                }}
                className={`px-3 py-1 rounded-lg text-xs font-medium transition-colors cursor-pointer ${
                  selectedLocation === loc.value
                    ? 'bg-indigo-600 text-white font-semibold'
                    : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700'
                }`}
              >
                {loc.label}
              </button>
            ))}

            <button
              onClick={() => {
                setIsRemoteOnly(!isRemoteOnly);
                setCurrentPage(1);
              }}
              className={`px-3 py-1 rounded-lg text-xs font-medium transition-colors cursor-pointer ${
                isRemoteOnly
                  ? 'bg-indigo-600 text-white font-semibold'
                  : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700'
              }`}
            >
              Remote Only
            </button>
          </div>

          {hasActiveFilters && (
            <button
              onClick={clearFilters}
              className="text-xs font-semibold text-rose-600 hover:text-rose-700 dark:text-rose-400 flex items-center gap-1 cursor-pointer"
            >
              <X className="h-3.5 w-3.5" />
              Clear Filters
            </button>
          )}
        </div>
      </div>

      {/* Jobs Feed List */}
      {isLoading ? (
        <div className="space-y-3">
          <CardSkeleton />
          <CardSkeleton />
          <CardSkeleton />
          <CardSkeleton />
        </div>
      ) : jobs.length === 0 ? (
        <div className="p-12 text-center rounded-xl border border-dashed border-slate-300 dark:border-slate-800 bg-white/50 dark:bg-slate-900/30">
          <p className="text-sm font-medium text-slate-600 dark:text-slate-400">
            No matching jobs found with the current filters.
          </p>
          <button
            onClick={clearFilters}
            className="mt-3 px-4 py-2 text-xs font-semibold bg-indigo-600 text-white rounded-lg cursor-pointer"
          >
            Reset Filters
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          {jobs.map((job) => (
            <div
              key={job.id}
              onClick={() => setSelectedJobId(job.id)}
              className="p-5 rounded-xl border border-slate-200 dark:border-slate-800/80 bg-white dark:bg-slate-900/60 shadow-xs hover:border-indigo-400 dark:hover:border-indigo-600 hover:shadow-md transition-all cursor-pointer group"
            >
              <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
                <div className="flex items-start gap-4 min-w-0">
                  <CompanyAvatar name={job.company_name} size="lg" />
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <h3 className="text-base font-bold text-slate-900 dark:text-white truncate group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors">
                        {job.title}
                      </h3>
                      <TierBadge tier={job.priority_tier} />
                      <MatchScoreBadge score={job.relevance_score} />
                    </div>

                    <div className="flex items-center gap-3 text-xs text-slate-500 dark:text-slate-400 mt-1 flex-wrap">
                      <span className="font-semibold text-slate-800 dark:text-slate-200">
                        {job.company_name}
                      </span>
                      <span>•</span>
                      <span className="flex items-center gap-1">
                        <MapPin className="h-3.5 w-3.5 text-slate-400" />
                        {job.location || 'Bangalore, India'} {job.is_remote ? '(Remote)' : ''}
                      </span>
                      {job.experience_raw && (
                        <>
                          <span>•</span>
                          <span className="flex items-center gap-1">
                            <Briefcase className="h-3.5 w-3.5 text-slate-400" />
                            {job.experience_raw}
                          </span>
                        </>
                      )}
                      <span>•</span>
                      <span className="text-[11px] text-slate-400">
                        {job.source_count} source{job.source_count > 1 ? 's' : ''}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-2.5 sm:self-start shrink-0">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setSelectedJobId(job.id);
                    }}
                    className="px-3 py-1.5 text-xs font-semibold rounded-lg bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 transition-colors cursor-pointer"
                  >
                    Inspect
                  </button>

                  {job.canonical_apply_url && (
                    <a
                      href={job.canonical_apply_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      onClick={(e) => e.stopPropagation()}
                      className="inline-flex items-center gap-1 px-3.5 py-1.5 text-xs font-semibold rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white shadow-xs transition-colors"
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
                <div className="mt-4 pt-3 border-t border-slate-100 dark:border-slate-800/80 flex flex-wrap gap-1.5 items-center">
                  <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider mr-1">
                    Matched:
                  </span>
                  {job.matched_skills.slice(0, 6).map((skill, i) => (
                    <span
                      key={i}
                      className="px-2 py-0.5 text-[11px] font-medium rounded bg-indigo-50/70 dark:bg-indigo-950/40 text-indigo-700 dark:text-indigo-300 border border-indigo-100 dark:border-indigo-900/50"
                    >
                      {skill}
                    </span>
                  ))}
                  {job.matched_skills.length > 6 && (
                    <span className="text-[10px] text-slate-400 font-medium">
                      +{job.matched_skills.length - 6} more
                    </span>
                  )}
                </div>
              )}
            </div>
          ))}
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
