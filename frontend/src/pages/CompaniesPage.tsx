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
  }, [currentPage, pageSize, targetOnly, searchQuery]);

  const fetchCompanies = async () => {
    try {
      setIsLoading(true);
      const params: any = {
        page: currentPage,
        page_size: pageSize,
      };
      if (targetOnly) params.is_target = true;
      if (searchQuery.trim()) params.search = searchQuery.trim();
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
    <div className="space-y-6 animate-in fade-in duration-300">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
            Companies Directory
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            Tracking {totalCompanies} enterprise engineering organizations, unicorn startups, and ATS portals.
          </p>
        </div>
      </div>

      {/* Search & Filter Controls */}
      <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800/80 bg-white dark:bg-slate-900/60 shadow-xs flex flex-col sm:flex-row items-center justify-between gap-3">
        <div className="relative w-full sm:max-w-md">
          <Search className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search companies (e.g. Razorpay, Zepto, Google)..."
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
              setCurrentPage(1);
            }}
            className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-lg pl-9 pr-4 py-2 text-xs sm:text-sm text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:border-indigo-500"
          />
        </div>

        <div className="flex items-center gap-2 w-full sm:w-auto">
          <button
            onClick={() => {
              setTargetOnly(!targetOnly);
              setCurrentPage(1);
            }}
            className={`px-3.5 py-2 text-xs font-semibold rounded-lg flex items-center gap-1.5 transition-colors cursor-pointer ${
              targetOnly
                ? 'bg-amber-50 dark:bg-amber-950/60 text-amber-700 dark:text-amber-400 border border-amber-300 dark:border-amber-800'
                : 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700'
            }`}
          >
            <Star className={`h-3.5 w-3.5 ${targetOnly ? 'fill-amber-500 text-amber-500' : ''}`} />
            <span>Target Companies Only</span>
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
        <div className="p-12 text-center rounded-xl border border-dashed border-slate-300 dark:border-slate-800">
          <p className="text-sm text-slate-500">No companies found matching "{searchQuery}".</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {companies.map((company) => (
            <div
              key={company.id}
              onClick={() => handleOpenCompany(company)}
              className="p-5 rounded-xl border border-slate-200 dark:border-slate-800/80 bg-white dark:bg-slate-900/60 shadow-xs hover:border-indigo-400 dark:hover:border-indigo-600 hover:shadow-md transition-all cursor-pointer flex flex-col justify-between group"
            >
              <div>
                <div className="flex items-start justify-between gap-3">
                  <CompanyAvatar name={company.name} size="lg" />
                  {company.is_target && (
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold bg-amber-50 dark:bg-amber-950/80 text-amber-700 dark:text-amber-400 border border-amber-200 dark:border-amber-800/80">
                      <Star className="h-3 w-3 fill-amber-500 text-amber-500" />
                      Target
                    </span>
                  )}
                </div>

                <h3 className="text-base font-bold text-slate-900 dark:text-white mt-3 group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors truncate">
                  {company.name}
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                  ATS: <span className="font-semibold text-slate-700 dark:text-slate-300">{company.ats_provider || 'Direct Career Site'}</span>
                </p>
              </div>

              <div className="mt-5 pt-3 border-t border-slate-100 dark:border-slate-800/80 flex items-center justify-between">
                <span className="text-xs font-semibold text-indigo-600 dark:text-indigo-400 flex items-center gap-1">
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
                      <span>{job.location || 'Bangalore'}</span>
                      <span>•</span>
                      <span>{job.experience_raw || '4+ Years'}</span>
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
