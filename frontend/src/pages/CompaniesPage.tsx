import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Building2,
  Search,
  Star,
  ExternalLink,
  Briefcase,
  Globe,
  Loader2,
  CheckCircle2,
  X,
  MapPin,
  Plane,
} from 'lucide-react';
import { getCompanies, getCompanyById } from '../api';
import type { Company, CompanyDetail } from '../types';
import { CompanyAvatar } from '../components/ui/CompanyAvatar';
import { Modal } from '../components/ui/Modal';
import { TierBadge, MatchScoreBadge } from '../components/ui/Badge';
import { Pagination } from '../components/ui/Pagination';

export const CompaniesPage: React.FC = () => {
  const navigate = useNavigate();
  const [companies, setCompanies] = useState<Company[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [targetOnly, setTargetOnly] = useState(false);
  const [locationFilter, setLocationFilter] = useState<'all' | 'INDIA' | 'ABROAD'>('all');

  // Pagination state
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [totalPages, setTotalPages] = useState(1);
  const [totalCompanies, setTotalCompanies] = useState(0);

  // Selected company detail modal
  const [selectedCompanyDetail, setSelectedCompanyDetail] = useState<CompanyDetail | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);

  useEffect(() => {
    fetchCompanies();
  }, [currentPage, pageSize, targetOnly, searchQuery, locationFilter]);

  const fetchCompanies = async () => {
    try {
      setIsLoading(true);
      const params: any = {
        page: currentPage,
        page_size: pageSize,
      };
      if (targetOnly) params.is_target = true;
      if (searchQuery.trim()) params.search = searchQuery.trim();
      if (locationFilter !== 'all') params.location = locationFilter;
      const res = await getCompanies(params);
      setCompanies(res.items);
      setTotalCompanies(res.meta.total);
      setTotalPages(res.meta.total_pages);
    } catch (err) {
      console.error('Failed to load companies:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleOpenCompany = async (company: Company) => {
    try {
      setLoadingDetail(true);
      const detail = await getCompanyById(company.id);
      setSelectedCompanyDetail(detail);
    } catch (err) {
      console.error('Failed to get company details:', err);
    } finally {
      setLoadingDetail(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-[28px] sm:text-[32px] font-bold tracking-tight text-slate-900 dark:text-white">
            Companies Directory
          </h1>
          <p className="mt-1 text-[13.5px] text-slate-800 dark:text-slate-300">
            Tracking {totalCompanies} enterprise engineering organizations, unicorn startups, and ATS portals.
          </p>
        </div>
      </div>

      {/* Search & Filter Controls */}
      <div className="p-4 sm:p-5 rounded-2xl border border-slate-200/80 dark:border-slate-800 bg-white dark:bg-[#111726] shadow-sm flex flex-col sm:flex-row items-center justify-between gap-3">
        <div className="relative w-full sm:max-w-md">
          <div className="group relative flex items-center p-1 rounded-xl border border-slate-200/90 dark:border-slate-700/80 bg-slate-50/70 dark:bg-slate-900/50 shadow-xs hover:border-slate-300 dark:hover:border-slate-600 focus-within:border-indigo-500 dark:focus-within:border-indigo-500 focus-within:bg-white dark:focus-within:bg-[#0f1422] focus-within:ring-4 focus-within:ring-indigo-500/15 focus-within:shadow-md focus-within:shadow-indigo-500/5 transition-all duration-300 ease-out">
            <Search className="h-4.5 w-4.5 ml-2.5 text-slate-600 dark:text-slate-300 group-focus-within:text-indigo-600 dark:group-focus-within:text-indigo-400 group-focus-within:scale-110 transition-all duration-300 ease-out shrink-0" />
            <input
              type="text"
              placeholder="Search companies (e.g. Razorpay, Zepto, Google)..."
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                setCurrentPage(1);
              }}
              className="w-full h-9 bg-transparent border-0 px-2.5 text-[14.5px] text-slate-900 dark:text-slate-100 placeholder:text-slate-700 dark:placeholder:text-slate-300 font-medium focus:outline-none focus:ring-0 leading-normal"
            />
            {searchQuery && (
              <button
                type="button"
                onClick={() => {
                  setSearchQuery('');
                  setCurrentPage(1);
                }}
                className="p-1.5 mr-1 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-200/60 dark:hover:bg-slate-800 transition-colors cursor-pointer animate-in fade-in zoom-in-90"
                title="Clear search"
              >
                <X className="h-4 w-4" />
              </button>
            )}
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2.5 w-full sm:w-auto">
          {/* Location Segmented Filter Pills */}
          <div className="inline-flex p-1 rounded-xl bg-slate-100 dark:bg-slate-800/80 border border-slate-200/80 dark:border-slate-700/60 shadow-2xs">
            <button
              type="button"
              onClick={() => {
                setLocationFilter('all');
                setCurrentPage(1);
              }}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all duration-150 cursor-pointer flex items-center gap-1.5 ${
                locationFilter === 'all'
                  ? 'bg-white dark:bg-slate-700 text-slate-900 dark:text-white shadow-2xs font-bold'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
              }`}
            >
              <Globe className="h-3.5 w-3.5" />
              <span>All</span>
            </button>

            <button
              type="button"
              onClick={() => {
                setLocationFilter('INDIA');
                setCurrentPage(1);
              }}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all duration-150 cursor-pointer flex items-center gap-1.5 ${
                locationFilter === 'INDIA'
                  ? 'bg-white dark:bg-slate-700 text-indigo-600 dark:text-indigo-400 shadow-2xs font-bold'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
              }`}
            >
              <MapPin className="h-3.5 w-3.5" />
              <span>India</span>
            </button>

            <button
              type="button"
              onClick={() => {
                setLocationFilter('ABROAD');
                setCurrentPage(1);
              }}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all duration-150 cursor-pointer flex items-center gap-1.5 ${
                locationFilter === 'ABROAD'
                  ? 'bg-white dark:bg-slate-700 text-indigo-600 dark:text-indigo-400 shadow-2xs font-bold'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
              }`}
            >
              <Plane className="h-3.5 w-3.5" />
              <span>Abroad</span>
            </button>
          </div>

          {/* Target Filter Button */}
          <button
            onClick={() => {
              setTargetOnly(!targetOnly);
              setCurrentPage(1);
            }}
            className={`h-9 px-3.5 text-xs font-semibold rounded-xl flex items-center gap-1.5 transition-all cursor-pointer ${
              targetOnly
                ? 'bg-amber-50 dark:bg-amber-950/60 text-amber-700 dark:text-amber-400 border border-amber-300 dark:border-amber-800 shadow-xs'
                : 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700'
            }`}
          >
            <Star className={`h-3.5 w-3.5 ${targetOnly ? 'fill-amber-500 text-amber-500' : ''}`} />
            <span>Target Only</span>
          </button>
        </div>
      </div>

      {/* Grid of Company Cards */}
      {isLoading ? (
        <div className="flex flex-col items-center justify-center py-20">
          <Loader2 className="h-8 w-8 animate-spin text-indigo-600" />
          <p className="text-xs text-slate-500 mt-2">Loading company directory...</p>
        </div>
      ) : companies.length === 0 ? (
        <div className="p-12 text-center rounded-2xl border border-dashed border-slate-300 dark:border-slate-800 bg-white/50 dark:bg-slate-900/30">
          <p className="text-sm font-medium text-slate-600 dark:text-slate-400">No companies found matching "{searchQuery}".</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {companies.map((company) => (
            <div
              key={company.id}
              onClick={() => handleOpenCompany(company)}
              className="p-5 sm:p-6 rounded-2xl border border-slate-200/80 dark:border-slate-800 bg-white dark:bg-[#111726] shadow-sm hover:border-indigo-300 dark:hover:border-indigo-700/60 hover:shadow-md hover:-translate-y-0.5 transition-[transform,box-shadow,border-color] duration-180 ease-out cursor-pointer flex flex-col justify-between group"
            >
              <div>
                <div className="flex items-start justify-between gap-3">
                  <CompanyAvatar name={company.name} size="lg" />
                  {company.is_target && (
                    <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-amber-50 dark:bg-amber-950/80 text-amber-700 dark:text-amber-400 border border-amber-200 dark:border-amber-800/80 shadow-xs">
                      <Star className="h-3 w-3 fill-amber-500 text-amber-500" />
                      Target
                    </span>
                  )}
                </div>

                <h3 className="text-[16px] sm:text-[17px] font-bold text-slate-900 dark:text-white mt-3 group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors truncate">
                  {company.name}
                </h3>
                <p className="text-[12.5px] text-slate-600 dark:text-slate-400 mt-1">
                  ATS: <span className="font-semibold text-slate-700 dark:text-slate-300">{company.ats_provider || 'Direct Career Site'}</span>
                </p>
              </div>

              <div className="mt-5 pt-3 border-t border-slate-100 dark:border-slate-800/80 flex items-center justify-between">
                <span className="text-[13px] font-semibold text-indigo-600 dark:text-indigo-400 flex items-center gap-1.5">
                  <Briefcase className="h-3.5 w-3.5" />
                  {company.active_jobs_count} Open Role{company.active_jobs_count === 1 ? '' : 's'}
                </span>

                <div className="flex items-center gap-1.5" onClick={(e) => e.stopPropagation()}>
                  {company.website && (
                    <a
                      href={company.website}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="p-1.5 rounded text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
                      title="Company Website"
                    >
                      <Globe className="h-3.5 w-3.5" />
                    </a>
                  )}
                  {company.career_url && (
                    <a
                      href={company.career_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="p-1.5 rounded text-slate-400 hover:text-indigo-600 dark:hover:text-indigo-400 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
                      title="Career Portal"
                    >
                      <ExternalLink className="h-3.5 w-3.5" />
                    </a>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Pagination Bar */}
      {totalCompanies > 0 && (
        <Pagination
          currentPage={currentPage}
          totalPages={totalPages}
          totalItems={totalCompanies}
          pageSize={pageSize}
          pageSizeOptions={[5, 10, 25, 100]}
          onPageChange={(p) => setCurrentPage(p)}
          onPageSizeChange={(sz) => {
            setPageSize(sz);
            setCurrentPage(1);
          }}
        />
      )}

      {/* Company Open Jobs Modal */}
      <Modal
        isOpen={!!selectedCompanyDetail}
        onClose={() => setSelectedCompanyDetail(null)}
        maxWidth="xl"
        title={
          selectedCompanyDetail ? (
            <div className="flex items-center gap-3">
              <CompanyAvatar name={selectedCompanyDetail.name} size="md" />
              <div>
                <h3 className="text-base font-bold text-slate-900 dark:text-white">
                  {selectedCompanyDetail.name}
                </h3>
                <p className="text-xs text-slate-500">
                  {selectedCompanyDetail.open_jobs?.length || 0} active openings discovered
                </p>
              </div>
            </div>
          ) : null
        }
      >
        {selectedCompanyDetail && (
          <div className="space-y-4">
            <div className="flex items-center justify-between text-xs text-slate-500 pb-2 border-b border-slate-200 dark:border-slate-800">
              <span>ATS Provider: <strong className="text-slate-800 dark:text-slate-200">{selectedCompanyDetail.ats_provider || 'Direct'}</strong></span>
              {selectedCompanyDetail.career_url && (
                <a
                  href={selectedCompanyDetail.career_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-indigo-600 dark:text-indigo-400 hover:underline flex items-center gap-1"
                >
                  Visit Careers Page
                  <ExternalLink className="h-3 w-3" />
                </a>
              )}
            </div>

            <div className="space-y-2.5 max-h-96 overflow-y-auto">
              {selectedCompanyDetail.open_jobs && selectedCompanyDetail.open_jobs.length > 0 ? (
                selectedCompanyDetail.open_jobs.map((job) => (
                  <div
                    key={job.id}
                    onClick={() => {
                      setSelectedCompanyDetail(null);
                      navigate(`/jobs?selected=${job.id}`);
                    }}
                    className="p-3.5 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/40 hover:border-indigo-400 dark:hover:border-indigo-600 transition-all cursor-pointer group"
                  >
                    <div className="flex items-center justify-between">
                      <h4 className="text-xs font-bold text-slate-900 dark:text-white group-hover:text-indigo-600 dark:group-hover:text-indigo-400">
                        {job.title}
                      </h4>
                      <TierBadge tier={job.priority_tier} />
                    </div>
                    <div className="mt-1 flex items-center gap-2 text-[11px] text-slate-500">
                      <span>{job.location || (job.is_remote ? 'Remote' : 'Location not specified')}</span>
                      <span>•</span>
                      <span>{job.experience_raw || (job.experience_min !== null ? `${job.experience_min}+ Years` : 'Experience not specified')}</span>
                      <span>•</span>
                      <MatchScoreBadge score={job.relevance_score} />
                    </div>
                  </div>
                ))
              ) : (
                <p className="text-xs text-slate-500 text-center py-6">
                  No currently open jobs ingested for this company.
                </p>
              )}
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
};
