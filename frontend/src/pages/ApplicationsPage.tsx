import React, { useState, useEffect } from 'react';
import {
  Layers,
  Plus,
  Clock,
  ExternalLink,
  ChevronRight,
  MoreVertical,
  Calendar,
  CheckCircle2,
  FileText,
  Building2,
  Loader2,
  Search,
  X,
  MapPin,
  Globe,
  TrendingUp,
} from 'lucide-react';
import { getApplications, updateApplication, createApplication, getJobs } from '../api';
import type { Application, JobSummary } from '../types';
import { ApplicationStatusBadge, TierBadge } from '../components/ui/Badge';
import { CompanyAvatar } from '../components/ui/CompanyAvatar';
import { Modal } from '../components/ui/Modal';
import { Button } from '../components/ui/Button';
import { Pagination } from '../components/ui/Pagination';
import { useToast } from '../context/ToastContext';

export const ApplicationsPage: React.FC = () => {
  const { toast } = useToast();
  const [applications, setApplications] = useState<Application[]>([]);
  const [selectedTab, setSelectedTab] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [isLoading, setIsLoading] = useState(true);

  // Status update modal state
  const [editingApp, setEditingApp] = useState<Application | null>(null);
  const [newStatus, setNewStatus] = useState<string>('');
  const [transitionNote, setTransitionNote] = useState<string>('');
  const [isUpdating, setIsUpdating] = useState(false);

  // Create Application Modal state
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [availableJobs, setAvailableJobs] = useState<JobSummary[]>([]);
  const [selectedJobId, setSelectedJobId] = useState<number | ''>('');
  const [createStatus, setCreateStatus] = useState<string>('applied');
  const [createNotes, setCreateNotes] = useState<string>('');
  const [isCreating, setIsCreating] = useState(false);

  useEffect(() => {
    fetchApplications();
  }, []);

  const fetchApplications = async () => {
    try {
      setIsLoading(true);
      const data = await getApplications();
      setApplications(data);
    } catch (err) {
      console.error('Failed to load applications:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const openStatusModal = (app: Application) => {
    setEditingApp(app);
    setNewStatus(app.status);
    setTransitionNote('');
  };

  const handleStatusSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingApp) return;
    try {
      setIsUpdating(true);
      await updateApplication(editingApp.id, {
        status: newStatus,
        note_for_history: transitionNote || undefined,
      });
      await fetchApplications();
      setEditingApp(null);
      toast.success(`Application updated to ${newStatus.replace(/_/g, ' ')}`, 1800);
    } catch (err: any) {
      toast.error(err.message || 'Failed to update application', 2000);
    } finally {
      setIsUpdating(false);
    }
  };

  const handleOpenCreateModal = async () => {
    setIsCreateModalOpen(true);
    try {
      const res = await getJobs({ page_size: 50, active_only: true });
      setAvailableJobs(res.items);
      if (res.items.length > 0) {
        setSelectedJobId(res.items[0].id);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleCreateApplication = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedJobId) return;
    try {
      setIsCreating(true);
      await createApplication({
        job_id: Number(selectedJobId),
        initial_status: createStatus,
        notes: createNotes || undefined,
      });
      await fetchApplications();
      setIsCreateModalOpen(false);
      setCreateNotes('');
      toast.success('Application added to pipeline', 1800);
    } catch (err: any) {
      toast.error(err.message || 'Failed to track application', 2000);
    } finally {
      setIsCreating(false);
    }
  };

  // Filter applications by tab & search query
  const filteredApps = applications.filter((app) => {
    const statusLower = app.status.toLowerCase();
    const matchesTab =
      selectedTab === 'all' ||
      (selectedTab === 'drafted'
        ? statusLower === 'drafted' || statusLower === 'saved' || statusLower === 'draft'
        : statusLower === selectedTab.toLowerCase());
    if (!matchesTab) return false;
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    const titleMatch = app.job?.title?.toLowerCase().includes(q) || false;
    const companyMatch = app.job?.company_name?.toLowerCase().includes(q) || false;
    const notesMatch = app.notes?.toLowerCase().includes(q) || false;
    const portalMatch = app.portal_type?.toLowerCase().includes(q) || false;
    return titleMatch || companyMatch || notesMatch || portalMatch;
  });

  const totalFiltered = filteredApps.length;
  const totalPages = Math.ceil(totalFiltered / pageSize) || 1;
  const paginatedTableApps = filteredApps.slice(
    (currentPage - 1) * pageSize,
    currentPage * pageSize
  );

  const statusTabs = [
    { label: 'All', value: 'all', count: applications.length },
    {
      label: 'Saved / Draft',
      value: 'drafted',
      count: applications.filter((a) => {
        const s = a.status.toLowerCase();
        return s === 'drafted' || s === 'saved' || s === 'draft';
      }).length,
    },
    { label: 'Applied', value: 'applied', count: applications.filter((a) => a.status === 'applied').length },
    { label: 'Under Review', value: 'under_review', count: applications.filter((a) => a.status === 'under_review').length },
    { label: 'Interviewing', value: 'interviewing', count: applications.filter((a) => a.status === 'interviewing').length },
    { label: 'Offered', value: 'offered', count: applications.filter((a) => a.status === 'offered').length },
    { label: 'Rejected', value: 'rejected', count: applications.filter((a) => a.status === 'rejected').length },
  ];

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-[28px] sm:text-[32px] font-bold tracking-tight text-slate-900 dark:text-white">
            Applications CRM
          </h1>
          <p className="mt-1 text-[14px] text-slate-700 dark:text-slate-300">
            Track your pipeline, log recruiter interactions, and advance interview stages.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <Button
            variant="primary"
            size="md"
            leftIcon={<Plus className="h-4 w-4" />}
            onClick={handleOpenCreateModal}
          >
            Track Application
          </Button>
        </div>
      </div>

      {/* Pipeline Pulse Stats - Dashboard Aligned KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Card 1: Total Pipeline */}
        <div className="flex items-center gap-4 rounded-2xl border border-slate-200/80 bg-white p-[18px] shadow-[0_1px_3px_rgba(0,0,0,0.03),0_1px_2px_rgba(0,0,0,0.02)] transition-[transform,box-shadow,border-color] duration-200 ease-out hover:-translate-y-0.5 hover:border-slate-300 hover:shadow-[0_6px_20px_rgba(0,0,0,0.05)] dark:border-slate-800 dark:bg-[#111726] dark:hover:border-slate-700">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600 ring-1 ring-inset ring-indigo-600/15 shadow-xs dark:bg-indigo-950/60 dark:text-indigo-400 dark:ring-indigo-400/20">
            <Layers className="h-5 w-5" />
          </div>
          <div className="min-w-0">
            <span className="text-[15.5px] font-semibold text-slate-800 dark:text-slate-200">
              Total Pipeline
            </span>
            <p className="mt-1 text-[34px] sm:text-[36px] font-bold leading-none tracking-tight text-slate-900 dark:text-white">
              {applications.length}
            </p>
            <p className="mt-1.5 truncate text-[12.5px] font-medium text-slate-700 dark:text-slate-300">
              {applications.filter((a) => a.status !== 'rejected').length} active in pipeline
            </p>
          </div>
        </div>

        {/* Card 2: In Interview */}
        <div className="flex items-center gap-4 rounded-2xl border border-slate-200/80 bg-white p-[18px] shadow-[0_1px_3px_rgba(0,0,0,0.03),0_1px_2px_rgba(0,0,0,0.02)] transition-[transform,box-shadow,border-color] duration-200 ease-out hover:-translate-y-0.5 hover:border-slate-300 hover:shadow-[0_6px_20px_rgba(0,0,0,0.05)] dark:border-slate-800 dark:bg-[#111726] dark:hover:border-slate-700">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-purple-50 text-purple-600 ring-1 ring-inset ring-purple-600/15 shadow-xs dark:bg-purple-950/60 dark:text-purple-400 dark:ring-purple-400/20">
            <Clock className="h-5 w-5" />
          </div>
          <div className="min-w-0">
            <span className="text-[15.5px] font-semibold text-slate-800 dark:text-slate-200">
              In Interview
            </span>
            <p className="mt-1 text-[34px] sm:text-[36px] font-bold leading-none tracking-tight text-purple-600 dark:text-purple-400">
              {applications.filter((a) => a.status === 'interviewing').length}
            </p>
            <p className="mt-1.5 truncate text-[12.5px] font-medium text-slate-700 dark:text-slate-300">
              Active interview stages
            </p>
          </div>
        </div>

        {/* Card 3: Under Review */}
        <div className="flex items-center gap-4 rounded-2xl border border-slate-200/80 bg-white p-[18px] shadow-[0_1px_3px_rgba(0,0,0,0.03),0_1px_2px_rgba(0,0,0,0.02)] transition-[transform,box-shadow,border-color] duration-200 ease-out hover:-translate-y-0.5 hover:border-slate-300 hover:shadow-[0_6px_20px_rgba(0,0,0,0.05)] dark:border-slate-800 dark:bg-[#111726] dark:hover:border-slate-700">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-blue-50 text-blue-600 ring-1 ring-inset ring-blue-600/15 shadow-xs dark:bg-blue-950/60 dark:text-blue-400 dark:ring-blue-400/20">
            <CheckCircle2 className="h-5 w-5" />
          </div>
          <div className="min-w-0">
            <span className="text-[15.5px] font-semibold text-slate-800 dark:text-slate-200">
              Under Review
            </span>
            <p className="mt-1 text-[34px] sm:text-[36px] font-bold leading-none tracking-tight text-blue-600 dark:text-blue-400">
              {applications.filter((a) => a.status === 'under_review').length}
            </p>
            <p className="mt-1.5 truncate text-[12.5px] font-medium text-slate-700 dark:text-slate-300">
              Awaiting recruiter response
            </p>
          </div>
        </div>

        {/* Card 4: Offers Received */}
        <div className="flex items-center gap-4 rounded-2xl border border-slate-200/80 bg-white p-[18px] shadow-[0_1px_3px_rgba(0,0,0,0.03),0_1px_2px_rgba(0,0,0,0.02)] transition-[transform,box-shadow,border-color] duration-200 ease-out hover:-translate-y-0.5 hover:border-slate-300 hover:shadow-[0_6px_20px_rgba(0,0,0,0.05)] dark:border-slate-800 dark:bg-[#111726] dark:hover:border-slate-700">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-emerald-50 text-emerald-600 ring-1 ring-inset ring-emerald-600/15 shadow-xs dark:bg-emerald-950/60 dark:text-emerald-400 dark:ring-emerald-400/20">
            <TrendingUp className="h-5 w-5" />
          </div>
          <div className="min-w-0">
            <span className="text-[15.5px] font-semibold text-slate-800 dark:text-slate-200">
              Offers Received
            </span>
            <p className="mt-1 text-[34px] sm:text-[36px] font-bold leading-none tracking-tight text-emerald-600 dark:text-emerald-400">
              {applications.filter((a) => a.status === 'offered').length}
            </p>
            <p className="mt-1.5 truncate text-[12.5px] font-medium text-slate-700 dark:text-slate-300">
              Offers in hand
            </p>
          </div>
        </div>
      </div>

      {/* Control Bar: Search & Status Tabs */}
      <div className="space-y-3 pt-1">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="relative flex-1 max-w-md">
            <div className="group relative flex items-center p-1 rounded-xl border border-slate-200/90 dark:border-slate-700/80 bg-slate-50/70 dark:bg-slate-900/50 shadow-xs hover:border-slate-300 dark:hover:border-slate-600 focus-within:border-indigo-500 dark:focus-within:border-indigo-500 focus-within:bg-white dark:focus-within:bg-[#0f1422] focus-within:ring-4 focus-within:ring-indigo-500/15 focus-within:shadow-md focus-within:shadow-indigo-500/5 transition-all duration-300 ease-out">
              <Search className="h-4.5 w-4.5 ml-2.5 text-slate-600 dark:text-slate-300 group-focus-within:text-indigo-600 dark:group-focus-within:text-indigo-400 group-focus-within:scale-110 transition-all duration-300 ease-out shrink-0" />
              <input
                type="text"
                placeholder="Search by company, role, or notes..."
                value={searchQuery}
                onChange={(e) => {
                  setSearchQuery(e.target.value);
                  setCurrentPage(1);
                }}
                className="w-full h-9 bg-transparent border-0 px-2.5 text-[14px] text-slate-900 dark:text-slate-100 placeholder:text-slate-700 dark:placeholder:text-slate-300 font-medium focus:outline-none focus:ring-0 leading-normal"
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

          <span className="text-[13px] font-medium text-slate-500 dark:text-slate-400 px-1">
            Showing <strong className="text-slate-800 dark:text-slate-200 font-bold">{totalFiltered}</strong> application{totalFiltered === 1 ? '' : 's'}
          </span>
        </div>

        {/* Tabs Filter Bar */}
        <div className="border-b border-slate-200 dark:border-slate-800 flex gap-2 overflow-x-auto pb-px">
          {statusTabs.map((tab) => (
            <button
              key={tab.value}
              onClick={() => {
                setSelectedTab(tab.value);
                setCurrentPage(1);
              }}
              className={`pb-3 px-3.5 text-[14px] font-semibold whitespace-nowrap border-b-2 transition-[color,border-color,background-color] duration-150 ease-out cursor-pointer flex items-center gap-2 ${
                selectedTab === tab.value
                  ? 'border-indigo-600 text-indigo-600 dark:text-indigo-400 font-bold'
                  : 'border-transparent text-slate-700 hover:text-slate-900 dark:text-slate-300 dark:hover:text-white'
              }`}
            >
              <span>{tab.label}</span>
              <span
                className={`text-[12px] px-2.5 py-0.5 rounded-full font-semibold ${
                  selectedTab === tab.value
                    ? 'bg-indigo-100 dark:bg-indigo-950 text-indigo-700 dark:text-indigo-300'
                    : 'bg-slate-200/80 dark:bg-slate-800 text-slate-700 dark:text-slate-300'
                }`}
              >
                {tab.count}
              </span>
            </button>
          ))}
        </div>
      </div>

      {/* View Content */}
      {isLoading ? (
        <div className="flex flex-col items-center justify-center py-24 min-h-[480px] rounded-2xl border border-slate-200/80 dark:border-slate-800 bg-white dark:bg-[#111726]">
          <Loader2 className="h-8 w-8 animate-spin text-indigo-600" />
          <p className="text-[13.5px] text-slate-700 dark:text-slate-300 mt-2.5 font-semibold">Loading applications...</p>
        </div>
      ) : filteredApps.length === 0 ? (
        <div className="rounded-2xl border border-slate-200/90 dark:border-slate-800 bg-white dark:bg-[#111726] shadow-sm overflow-hidden flex flex-col">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[700px] text-left border-separate border-spacing-0">
              <thead>
                <tr className="bg-slate-50/95 dark:bg-[#151c2e]/95 backdrop-blur-md shadow-[0_2px_8px_-2px_rgba(0,0,0,0.06)] dark:shadow-[0_2px_8px_-2px_rgba(0,0,0,0.35)]">
                  <th className="px-6 py-4 w-[42%] text-slate-900 dark:text-white uppercase tracking-wider text-[12.5px] font-bold border-b border-slate-200/90 dark:border-slate-800">
                    Company & Role
                  </th>
                  <th className="px-6 py-4 w-[18%] text-slate-900 dark:text-white uppercase tracking-wider text-[12.5px] font-bold whitespace-nowrap border-b border-slate-200/90 dark:border-slate-800">
                    Status
                  </th>
                  <th className="px-6 py-4 w-[18%] text-slate-900 dark:text-white uppercase tracking-wider text-[12.5px] font-bold whitespace-nowrap border-b border-slate-200/90 dark:border-slate-800">
                    Applied Date
                  </th>
                  <th className="px-6 py-4 w-[14%] text-slate-900 dark:text-white uppercase tracking-wider text-[12.5px] font-bold whitespace-nowrap border-b border-slate-200/90 dark:border-slate-800">
                    Portal / Source
                  </th>
                  <th className="px-6 py-4 w-[8%] text-right text-slate-900 dark:text-white uppercase tracking-wider text-[12.5px] font-bold whitespace-nowrap border-b border-slate-200/90 dark:border-slate-800">
                    Actions
                  </th>
                </tr>
              </thead>
            </table>
          </div>
          <div className="flex flex-col items-center justify-center p-16 text-center min-h-[360px]">
            <p className="text-[15px] font-semibold text-slate-800 dark:text-slate-200">
              No applications match your current filters.
            </p>
            <Button
              variant="outline"
              size="md"
              className="mt-4"
              onClick={() => {
                setSelectedTab('all');
                setSearchQuery('');
              }}
            >
              Clear Filters
            </Button>
          </div>
        </div>
      ) : (
        /* God-Tier Enterprise Fixed-Header Vertical Scrollable Table */
        <div className="rounded-2xl border border-slate-200/90 dark:border-slate-800 bg-white dark:bg-[#111726] shadow-sm overflow-hidden flex flex-col">
          {/* Scrollable Viewport with Fixed Sticky Header */}
          <div className="overflow-x-auto overflow-y-auto max-h-[520px] scrollbar-thin scrollbar-thumb-slate-300 dark:scrollbar-thumb-slate-700">
            <table className="w-full min-w-[700px] text-left border-separate border-spacing-0">
              <thead className="sticky top-0 z-20">
                <tr className="bg-slate-50/95 dark:bg-[#151c2e]/95 backdrop-blur-md shadow-[0_2px_8px_-2px_rgba(0,0,0,0.06)] dark:shadow-[0_2px_8px_-2px_rgba(0,0,0,0.35)]">
                  <th className="px-6 py-4 w-[42%] text-slate-900 dark:text-white uppercase tracking-wider text-[12.5px] font-bold border-b border-slate-200/90 dark:border-slate-800">
                    Company & Role
                  </th>
                  <th className="px-6 py-4 w-[18%] text-slate-900 dark:text-white uppercase tracking-wider text-[12.5px] font-bold whitespace-nowrap border-b border-slate-200/90 dark:border-slate-800">
                    Status
                  </th>
                  <th className="px-6 py-4 w-[18%] text-slate-900 dark:text-white uppercase tracking-wider text-[12.5px] font-bold whitespace-nowrap border-b border-slate-200/90 dark:border-slate-800">
                    Applied Date
                  </th>
                  <th className="px-6 py-4 w-[14%] text-slate-900 dark:text-white uppercase tracking-wider text-[12.5px] font-bold whitespace-nowrap border-b border-slate-200/90 dark:border-slate-800">
                    Portal / Source
                  </th>
                  <th className="px-6 py-4 w-[8%] text-right text-slate-900 dark:text-white uppercase tracking-wider text-[12.5px] font-bold whitespace-nowrap border-b border-slate-200/90 dark:border-slate-800">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800/80">
                {paginatedTableApps.map((app) => (
                  <tr
                    key={app.id}
                    className="group even:bg-slate-50/60 dark:even:bg-[#141b2c]/60 odd:bg-white dark:odd:bg-[#111726] hover:bg-indigo-50/50 dark:hover:bg-indigo-950/40 transition-colors duration-150"
                  >
                    <td className="px-6 py-4 border-b border-slate-100/90 dark:border-slate-800/70">
                      <div className="flex items-center gap-3.5">
                        <CompanyAvatar name={app.job?.company_name || 'Company'} size="md" />
                        <div className="min-w-0">
                          <div className="flex items-center gap-2">
                            <p className="font-bold text-slate-900 dark:text-white text-[15px] leading-snug truncate group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors">
                              {app.job?.title || `Job #${app.job_id}`}
                            </p>
                            {app.job?.canonical_apply_url && (
                              <a
                                href={app.job.canonical_apply_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                onClick={(e) => e.stopPropagation()}
                                className="text-slate-400 hover:text-indigo-600 dark:hover:text-indigo-400 shrink-0 transition-colors"
                                title="Open Job Listing"
                              >
                                <ExternalLink className="h-3.5 w-3.5" />
                              </a>
                            )}
                          </div>
                          <div className="flex items-center gap-2 mt-1.5 flex-wrap">
                            {app.job?.priority_tier && (
                              <TierBadge tier={app.job.priority_tier} />
                            )}
                            <span className="font-bold text-slate-800 dark:text-slate-200 text-[13px]">
                              {app.job?.company_name}
                            </span>
                            <span className="text-slate-300 dark:text-slate-700">•</span>
                            <span className="flex items-center gap-1 text-slate-600 dark:text-slate-400 text-[12.5px] font-medium">
                              <MapPin className="h-3 w-3 text-slate-400 shrink-0" />
                              {app.job?.location || 'India'} {app.job?.is_remote ? '(Remote)' : ''}
                            </span>
                          </div>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap border-b border-slate-100/90 dark:border-slate-800/70">
                      <ApplicationStatusBadge status={app.status} size="md" />
                    </td>
                    <td className="px-6 py-4 text-slate-800 dark:text-slate-200 text-[13.5px] font-semibold whitespace-nowrap border-b border-slate-100/90 dark:border-slate-800/70">
                      {app.applied_at ? (
                        <div className="flex items-center gap-1.5 text-slate-800 dark:text-slate-200 text-[13.5px] font-semibold whitespace-nowrap">
                          <Calendar className="h-3.5 w-3.5 text-slate-400 shrink-0" />
                          <span>{new Date(app.applied_at).toLocaleDateString()}</span>
                        </div>
                      ) : (
                        <span className="inline-flex items-center px-2.5 py-1 rounded-md text-[12px] font-medium bg-slate-100 dark:bg-slate-800/80 text-slate-600 dark:text-slate-400 border border-slate-200/60 dark:border-slate-700/60">
                          Draft / Pending
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap border-b border-slate-100/90 dark:border-slate-800/70">
                      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[12px] font-semibold bg-slate-100/90 dark:bg-slate-800/80 text-slate-700 dark:text-slate-300 border border-slate-200/80 dark:border-slate-700/80 shadow-2xs">
                        <Globe className="h-3.5 w-3.5 text-slate-500" />
                        {app.portal_type || 'Direct Portal'}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-right whitespace-nowrap border-b border-slate-100/90 dark:border-slate-800/70">
                      <button
                        onClick={() => openStatusModal(app)}
                        className="px-4 py-1.5 text-[13px] font-semibold rounded-xl bg-indigo-50 hover:bg-indigo-600 hover:text-white text-indigo-700 dark:bg-indigo-950/70 dark:text-indigo-300 dark:hover:bg-indigo-600 dark:hover:text-white border border-indigo-200/80 dark:border-indigo-800/80 shadow-2xs transition-all duration-150 cursor-pointer"
                      >
                        Update
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Sticky Docked Bottom Pagination */}
          <div className="p-4 border-t border-slate-200 dark:border-slate-800 bg-slate-50/70 dark:bg-[#131929]/70 backdrop-blur-xs">
            <Pagination
              currentPage={currentPage}
              totalPages={totalPages}
              totalItems={totalFiltered}
              pageSize={pageSize}
              pageSizeOptions={[5, 10, 25, 100]}
              onPageChange={(p) => setCurrentPage(p)}
              onPageSizeChange={(sz) => {
                setPageSize(sz);
                setCurrentPage(1);
              }}
            />
          </div>
        </div>
      )}

      {/* Update Status Modal with Timeline History */}
      <Modal
        isOpen={!!editingApp}
        onClose={() => setEditingApp(null)}
        title={
          <div className="flex items-center gap-2">
            <span>Update Application Status</span>
          </div>
        }
        description={editingApp ? `${editingApp.job?.title} at ${editingApp.job?.company_name}` : ''}
      >
        {editingApp && (
          <form onSubmit={handleStatusSubmit} className="space-y-5">
            <div>
              <label className="block text-[12px] font-semibold uppercase tracking-wider text-slate-700 dark:text-slate-400 mb-1.5">
                Application Stage
              </label>
              <select
                value={newStatus}
                onChange={(e) => setNewStatus(e.target.value)}
                className="w-full bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-xl px-3.5 py-2 text-[13.5px] text-slate-900 dark:text-slate-100 focus:outline-none focus:border-indigo-500"
              >
                <option value="drafted">Saved / Draft</option>
                <option value="applied">Applied</option>
                <option value="under_review">Under Review</option>
                <option value="interviewing">Interviewing</option>
                <option value="offered">Offered</option>
                <option value="rejected">Rejected</option>
              </select>
            </div>

            <div>
              <label className="block text-[12px] font-semibold uppercase tracking-wider text-slate-700 dark:text-slate-400 mb-1.5">
                Note for Timeline History
              </label>
              <textarea
                rows={3}
                placeholder="e.g. Cleared round 1 technical screen, recruiter scheduling round 2 system design..."
                value={transitionNote}
                onChange={(e) => setTransitionNote(e.target.value)}
                className="w-full bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-xl px-3.5 py-2 text-[13.5px] text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:border-indigo-500"
              />
            </div>

            {/* Audit History Timeline */}
            {editingApp.history && editingApp.history.length > 0 && (
              <div className="pt-3 border-t border-slate-200 dark:border-slate-800">
                <span className="text-[12px] font-bold text-slate-700 dark:text-slate-300 block mb-2">
                  Transition Timeline History
                </span>
                <div className="space-y-3 max-h-40 overflow-y-auto">
                  {editingApp.history.map((h) => (
                    <div key={h.id} className="flex items-start gap-2.5 text-[12.5px]">
                      <span className="h-2 w-2 rounded-full bg-indigo-500 mt-1.5 shrink-0" />
                      <div>
                        <p className="font-semibold text-slate-800 dark:text-slate-200">
                          Changed to <span className="uppercase text-indigo-600">{h.new_status}</span>
                        </p>
                        {h.note && <p className="text-slate-600 dark:text-slate-400">{h.note}</p>}
                        <span className="text-[11px] text-slate-400">
                          {new Date(h.changed_at).toLocaleString()}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="flex justify-end gap-2.5 pt-3 border-t border-slate-200 dark:border-slate-800">
              <Button variant="secondary" size="md" onClick={() => setEditingApp(null)}>
                Cancel
              </Button>
              <Button variant="primary" size="md" type="submit" isLoading={isUpdating}>
                Save Changes
              </Button>
            </div>
          </form>
        )}
      </Modal>

      {/* Manual Track Application Modal */}
      <Modal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        title="Track New Application"
        description="Select an active job opportunity to add to your CRM pipeline."
      >
        <form onSubmit={handleCreateApplication} className="space-y-4">
          <div>
            <label className="block text-[12px] font-semibold uppercase tracking-wider text-slate-700 dark:text-slate-400 mb-1.5">
              Select Discovered Job
            </label>
            <select
              value={selectedJobId}
              onChange={(e) => setSelectedJobId(Number(e.target.value))}
              className="w-full bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-xl px-3.5 py-2 text-[13.5px] text-slate-900 dark:text-slate-100 focus:outline-none focus:border-indigo-500"
            >
              {availableJobs.map((j) => (
                <option key={j.id} value={j.id}>
                  {j.company_name} — {j.title} ({j.priority_tier})
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-[12px] font-semibold uppercase tracking-wider text-slate-700 dark:text-slate-400 mb-1.5">
              Initial Stage
            </label>
            <select
              value={createStatus}
              onChange={(e) => setCreateStatus(e.target.value)}
              className="w-full bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-xl px-3.5 py-2 text-[13.5px] text-slate-900 dark:text-slate-100 focus:outline-none focus:border-indigo-500"
            >
              <option value="drafted">Saved / Draft</option>
              <option value="applied">Applied</option>
              <option value="under_review">Under Review</option>
              <option value="interviewing">Interviewing</option>
            </select>
          </div>

          <div>
            <label className="block text-[12px] font-semibold uppercase tracking-wider text-slate-700 dark:text-slate-400 mb-1.5">
              Initial Notes
            </label>
            <textarea
              rows={3}
              placeholder="e.g. Applied directly on company career portal..."
              value={createNotes}
              onChange={(e) => setCreateNotes(e.target.value)}
              className="w-full bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-xl px-3.5 py-2 text-[13.5px] text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:border-indigo-500"
            />
          </div>

          <div className="flex justify-end gap-2.5 pt-3 border-t border-slate-200 dark:border-slate-800">
            <Button variant="secondary" size="md" onClick={() => setIsCreateModalOpen(false)}>
              Cancel
            </Button>
            <Button variant="primary" size="md" type="submit" isLoading={isCreating}>
              Add to Pipeline
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
