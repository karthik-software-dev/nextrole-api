import React, { useState, useEffect } from 'react';
import {
  Layers,
  Kanban,
  Table as TableIcon,
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
  const [viewMode, setViewMode] = useState<'kanban' | 'table'>('table');
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

  // Filter applications by tab
  const filteredApps = applications.filter((app) => {
    if (selectedTab === 'all') return true;
    return app.status.toLowerCase() === selectedTab.toLowerCase();
  });

  const totalFiltered = filteredApps.length;
  const totalPages = Math.ceil(totalFiltered / pageSize) || 1;
  const paginatedTableApps = filteredApps.slice(
    (currentPage - 1) * pageSize,
    currentPage * pageSize
  );

  const statusTabs = [
    { label: 'All', value: 'all', count: applications.length },
    { label: 'Saved / Draft', value: 'drafted', count: applications.filter((a) => a.status === 'drafted').length },
    { label: 'Applied', value: 'applied', count: applications.filter((a) => a.status === 'applied').length },
    { label: 'Under Review', value: 'under_review', count: applications.filter((a) => a.status === 'under_review').length },
    { label: 'Interviewing', value: 'interviewing', count: applications.filter((a) => a.status === 'interviewing').length },
    { label: 'Offered', value: 'offered', count: applications.filter((a) => a.status === 'offered').length },
    { label: 'Rejected', value: 'rejected', count: applications.filter((a) => a.status === 'rejected').length },
  ];

  const kanbanColumns = [
    { id: 'drafted', title: 'Saved / Draft' },
    { id: 'applied', title: 'Applied' },
    { id: 'under_review', title: 'Under Review' },
    { id: 'interviewing', title: 'Interviewing' },
    { id: 'offered', title: 'Offered' },
    { id: 'rejected', title: 'Rejected' },
  ];

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
            Applications CRM
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            Track your pipeline, log recruiter interactions, and advance interview stages.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          {/* View switcher */}
          <div className="p-1 rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 flex items-center gap-1">
            <button
              onClick={() => setViewMode('table')}
              className={`px-3 py-1 text-xs font-semibold rounded-md flex items-center gap-1.5 transition-colors cursor-pointer ${
                viewMode === 'table'
                  ? 'bg-indigo-50 dark:bg-indigo-950 text-indigo-600 dark:text-indigo-400'
                  : 'text-slate-500 hover:text-slate-800 dark:hover:text-slate-200'
              }`}
            >
              <TableIcon className="h-3.5 w-3.5" />
              Table
            </button>
            <button
              onClick={() => setViewMode('kanban')}
              className={`px-3 py-1 text-xs font-semibold rounded-md flex items-center gap-1.5 transition-colors cursor-pointer ${
                viewMode === 'kanban'
                  ? 'bg-indigo-50 dark:bg-indigo-950 text-indigo-600 dark:text-indigo-400'
                  : 'text-slate-500 hover:text-slate-800 dark:hover:text-slate-200'
              }`}
            >
              <Kanban className="h-3.5 w-3.5" />
              Kanban
            </button>
          </div>

          <Button
            variant="primary"
            size="sm"
            leftIcon={<Plus className="h-4 w-4" />}
            onClick={handleOpenCreateModal}
          >
            Track Application
          </Button>
        </div>
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
            className={`pb-3 px-3 text-xs font-semibold whitespace-nowrap border-b-2 transition-colors cursor-pointer flex items-center gap-2 ${
              selectedTab === tab.value
                ? 'border-indigo-600 text-indigo-600 dark:text-indigo-400'
                : 'border-transparent text-slate-500 hover:text-slate-800 dark:hover:text-slate-200'
            }`}
          >
            <span>{tab.label}</span>
            <span
              className={`text-[10px] px-1.5 py-0.2 rounded-full font-bold ${
                selectedTab === tab.value
                  ? 'bg-indigo-100 dark:bg-indigo-950 text-indigo-700 dark:text-indigo-300'
                  : 'bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400'
              }`}
            >
              {tab.count}
            </span>
          </button>
        ))}
      </div>

      {/* View Content */}
      {isLoading ? (
        <div className="flex flex-col items-center justify-center py-20">
          <Loader2 className="h-8 w-8 animate-spin text-indigo-600" />
          <p className="text-xs text-slate-500 mt-2">Loading applications...</p>
        </div>
      ) : filteredApps.length === 0 ? (
        <div className="p-12 text-center rounded-xl border border-dashed border-slate-300 dark:border-slate-800 bg-white/50 dark:bg-slate-900/30">
          <p className="text-sm font-medium text-slate-600 dark:text-slate-400">
            No applications found in this stage.
          </p>
          <Button
            variant="outline"
            size="sm"
            className="mt-3"
            onClick={handleOpenCreateModal}
          >
            + Track an Application
          </Button>
        </div>
      ) : viewMode === 'table' ? (
        /* Table View */
        <div className="rounded-xl border border-slate-200 dark:border-slate-800/80 bg-white dark:bg-slate-900/60 shadow-xs overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 dark:bg-slate-800/60 text-slate-500 dark:text-slate-400 uppercase tracking-wider font-semibold border-b border-slate-200 dark:border-slate-800">
                <tr>
                  <th className="px-6 py-3.5">Company & Role</th>
                  <th className="px-6 py-3.5">Status</th>
                  <th className="px-6 py-3.5">Applied Date</th>
                  <th className="px-6 py-3.5">Portal / Source</th>
                  <th className="px-6 py-3.5">Notes</th>
                  <th className="px-6 py-3.5 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800/80">
                {paginatedTableApps.map((app) => (
                  <tr
                    key={app.id}
                    className="hover:bg-slate-50/80 dark:hover:bg-slate-800/40 transition-colors"
                  >
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        <CompanyAvatar name={app.job?.company_name || 'Company'} size="md" />
                        <div>
                          <p className="font-semibold text-slate-900 dark:text-white">
                            {app.job?.title || `Job #${app.job_id}`}
                          </p>
                          <p className="text-slate-500 text-[11px]">
                            {app.job?.company_name} • {app.job?.location || 'Bangalore'}
                          </p>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <ApplicationStatusBadge status={app.status} />
                    </td>
                    <td className="px-6 py-4 text-slate-600 dark:text-slate-300">
                      {app.applied_at ? new Date(app.applied_at).toLocaleDateString() : 'Pending'}
                    </td>
                    <td className="px-6 py-4 text-slate-600 dark:text-slate-300 font-mono text-[11px]">
                      {app.portal_type || 'Direct Portal'}
                    </td>
                    <td className="px-6 py-4 text-slate-500 max-w-xs truncate">
                      {app.notes || '—'}
                    </td>
                    <td className="px-6 py-4 text-right">
                      <button
                        onClick={() => openStatusModal(app)}
                        className="px-3 py-1 text-xs font-semibold rounded-lg bg-indigo-50 hover:bg-indigo-100 dark:bg-indigo-950/60 dark:hover:bg-indigo-900/60 text-indigo-600 dark:text-indigo-400 transition-colors cursor-pointer"
                      >
                        Update
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {viewMode === 'table' && totalFiltered > 0 && (
            <div className="p-4 border-t border-slate-200 dark:border-slate-800">
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
          )}
        </div>
      ) : (
        /* Kanban Board View */
        <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-6 gap-4 overflow-x-auto pb-4">
          {kanbanColumns.map((col) => {
            const colApps = applications.filter((a) => a.status === col.id);
            return (
              <div
                key={col.id}
                className="rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/40 p-3 min-w-[240px] flex flex-col"
              >
                <div className="flex items-center justify-between pb-3 mb-2 border-b border-slate-200 dark:border-slate-800">
                  <span className="text-xs font-bold text-slate-700 dark:text-slate-300">
                    {col.title}
                  </span>
                  <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-slate-200 dark:bg-slate-800 text-slate-700 dark:text-slate-300">
                    {colApps.length}
                  </span>
                </div>

                <div className="flex-1 space-y-2.5 overflow-y-auto max-h-[70vh]">
                  {colApps.map((app) => (
                    <div
                      key={app.id}
                      onClick={() => openStatusModal(app)}
                      className="p-3.5 rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-xs hover:border-indigo-400 dark:hover:border-indigo-600 transition-all cursor-pointer group"
                    >
                      <div className="flex items-center gap-2 mb-2">
                        <CompanyAvatar name={app.job?.company_name || 'Company'} size="xs" />
                        <span className="text-[11px] font-semibold text-slate-500 truncate">
                          {app.job?.company_name}
                        </span>
                      </div>
                      <h4 className="text-xs font-bold text-slate-900 dark:text-white line-clamp-2 group-hover:text-indigo-600 dark:group-hover:text-indigo-400">
                        {app.job?.title || `Job #${app.job_id}`}
                      </h4>
                      {app.notes && (
                        <p className="mt-2 text-[11px] text-slate-500 line-clamp-2 italic bg-slate-50 dark:bg-slate-800/50 p-1.5 rounded">
                          "{app.notes}"
                        </p>
                      )}
                      <div className="mt-3 pt-2 border-t border-slate-100 dark:border-slate-800/80 flex items-center justify-between text-[10px] text-slate-400">
                        <span>{app.applied_at ? new Date(app.applied_at).toLocaleDateString() : 'Tracked'}</span>
                        <span className="text-indigo-600 dark:text-indigo-400 font-semibold group-hover:underline">
                          Edit →
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
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
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 dark:text-slate-400 mb-1.5">
                Application Stage
              </label>
              <select
                value={newStatus}
                onChange={(e) => setNewStatus(e.target.value)}
                className="w-full bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg px-3.5 py-2 text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:border-indigo-500"
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
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 dark:text-slate-400 mb-1.5">
                Note for Timeline History
              </label>
              <textarea
                rows={3}
                placeholder="e.g. Cleared round 1 technical screen, recruiter scheduling round 2 system design..."
                value={transitionNote}
                onChange={(e) => setTransitionNote(e.target.value)}
                className="w-full bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg px-3.5 py-2 text-sm text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:border-indigo-500"
              />
            </div>

            {/* Audit History Timeline */}
            {editingApp.history && editingApp.history.length > 0 && (
              <div className="pt-3 border-t border-slate-200 dark:border-slate-800">
                <span className="text-xs font-bold text-slate-700 dark:text-slate-300 block mb-2">
                  Transition Timeline History
                </span>
                <div className="space-y-3 max-h-40 overflow-y-auto">
                  {editingApp.history.map((h) => (
                    <div key={h.id} className="flex items-start gap-2.5 text-xs">
                      <span className="h-2 w-2 rounded-full bg-indigo-500 mt-1.5 shrink-0" />
                      <div>
                        <p className="font-semibold text-slate-800 dark:text-slate-200">
                          Changed to <span className="uppercase text-indigo-600">{h.new_status}</span>
                        </p>
                        {h.note && <p className="text-slate-500">{h.note}</p>}
                        <span className="text-[10px] text-slate-400">
                          {new Date(h.changed_at).toLocaleString()}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="flex justify-end gap-2.5 pt-3 border-t border-slate-200 dark:border-slate-800">
              <Button variant="secondary" size="sm" onClick={() => setEditingApp(null)}>
                Cancel
              </Button>
              <Button variant="primary" size="sm" type="submit" isLoading={isUpdating}>
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
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 dark:text-slate-400 mb-1.5">
              Select Discovered Job
            </label>
            <select
              value={selectedJobId}
              onChange={(e) => setSelectedJobId(Number(e.target.value))}
              className="w-full bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-900 dark:text-slate-100 focus:outline-none focus:border-indigo-500"
            >
              {availableJobs.map((j) => (
                <option key={j.id} value={j.id}>
                  {j.company_name} — {j.title} ({j.priority_tier})
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 dark:text-slate-400 mb-1.5">
              Initial Stage
            </label>
            <select
              value={createStatus}
              onChange={(e) => setCreateStatus(e.target.value)}
              className="w-full bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-900 dark:text-slate-100 focus:outline-none focus:border-indigo-500"
            >
              <option value="drafted">Saved / Draft</option>
              <option value="applied">Applied</option>
              <option value="under_review">Under Review</option>
              <option value="interviewing">Interviewing</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 dark:text-slate-400 mb-1.5">
              Initial Notes
            </label>
            <textarea
              rows={3}
              placeholder="e.g. Applied directly on company career portal..."
              value={createNotes}
              onChange={(e) => setCreateNotes(e.target.value)}
              className="w-full bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:border-indigo-500"
            />
          </div>

          <div className="flex justify-end gap-2.5 pt-3 border-t border-slate-200 dark:border-slate-800">
            <Button variant="secondary" size="sm" onClick={() => setIsCreateModalOpen(false)}>
              Cancel
            </Button>
            <Button variant="primary" size="sm" type="submit" isLoading={isCreating}>
              Add to Pipeline
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
