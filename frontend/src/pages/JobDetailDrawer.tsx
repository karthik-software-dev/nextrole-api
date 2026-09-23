import React, { useState, useEffect } from 'react';
import {
  ExternalLink,
  Building2,
  MapPin,
  Calendar,
  Briefcase,
  Layers,
  Award,
  CheckCircle2,
  AlertCircle,
  Clock,
  Sparkles,
  Share2,
  Trash2,
  PlusCircle,
  Loader2,
} from 'lucide-react';
import { Drawer } from '../components/ui/Drawer';
import { TierBadge, MatchScoreBadge, ApplicationStatusBadge } from '../components/ui/Badge';
import { CompanyAvatar } from '../components/ui/CompanyAvatar';
import { Button } from '../components/ui/Button';
import { getJobById, createApplication, deactivateJob } from '../api';
import { useToast } from '../context/ToastContext';
import type { JobDetail } from '../types';

interface JobDetailDrawerProps {
  jobId: number | null;
  onClose: () => void;
  onJobUpdated?: () => void;
}

export const JobDetailDrawer: React.FC<JobDetailDrawerProps> = ({
  jobId,
  onClose,
  onJobUpdated,
}) => {
  const { toast } = useToast();
  const [job, setJob] = useState<JobDetail | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'requirements' | 'company' | 'description'>('overview');
  const [isLoading, setIsLoading] = useState(false);
  const [isApplying, setIsApplying] = useState(false);
  const [applicationStatus, setApplicationStatus] = useState<string>('applied');
  const [notes, setNotes] = useState<string>('');

  useEffect(() => {
    if (jobId) {
      loadJobDetails(jobId);
    } else {
      setJob(null);
    }
  }, [jobId]);

  const loadJobDetails = async (id: number) => {
    try {
      setIsLoading(true);
      const data = await getJobById(id);
      setJob(data);
      if (data.application_status) {
        setApplicationStatus(data.application_status);
      }
    } catch (err) {
      console.error('Failed to load job details:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleTrackApplication = async () => {
    if (!job) return;
    try {
      setIsApplying(true);
      await createApplication({
        job_id: job.id,
        initial_status: applicationStatus,
        notes: notes || undefined,
        portal_type: job.ats_provider || 'Company Career Portal',
      });
      toast.success(`Application marked as "${applicationStatus}" in CRM!`, 1800);
      if (onJobUpdated) onJobUpdated();
    } catch (err: any) {
      console.error(err);
      toast.error(err.message || 'Failed to track application', 2000);
    } finally {
      setIsApplying(false);
    }
  };

  const handleDeactivate = async () => {
    if (!job) return;
    if (!window.confirm('Are you sure you want to deactivate and hide this job?')) return;
    try {
      await deactivateJob(job.id);
      if (onJobUpdated) onJobUpdated();
      onClose();
    } catch (err: any) {
      alert(err.message || 'Failed to deactivate job');
    }
  };

  if (!jobId) return null;

  return (
    <Drawer
      isOpen={!!jobId}
      onClose={onClose}
      width="2xl"
      title={
        job ? (
          <div className="flex items-center gap-3">
            <CompanyAvatar name={job.company_name} size="md" />
            <div className="min-w-0">
              <h2 className="text-base font-bold text-slate-900 dark:text-white truncate">
                {job.title}
              </h2>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                {job.company_name} • {job.location || 'India'}
              </p>
            </div>
          </div>
        ) : (
          <div>Loading Job Details...</div>
        )
      }
    >
      {isLoading ? (
        <div className="flex flex-col items-center justify-center py-20 space-y-3">
          <Loader2 className="h-8 w-8 animate-spin text-indigo-600" />
          <p className="text-xs text-slate-500">Loading intelligence data...</p>
        </div>
      ) : !job ? (
        <div className="py-12 text-center text-slate-500">Job details not available.</div>
      ) : (
        <div className="space-y-6">
          {/* Top Score & Highlights Card */}
          <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-gradient-to-br from-indigo-50/50 via-white to-slate-50 dark:from-indigo-950/20 dark:via-slate-900 dark:to-slate-900 p-5 shadow-xs">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div className="flex items-center gap-4">
                {/* Circular / Large Score Badge */}
                <div className="h-16 w-16 rounded-2xl bg-indigo-600 dark:bg-indigo-500 text-white flex flex-col items-center justify-center shadow-lg shadow-indigo-500/20 shrink-0">
                  <span className="text-xl font-extrabold leading-none">{job.relevance_score}%</span>
                  <span className="text-[9px] uppercase tracking-wider font-semibold opacity-90 mt-0.5">Match</span>
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <TierBadge tier={job.priority_tier} />
                    {job.application_status && (
                      <ApplicationStatusBadge status={job.application_status} />
                    )}
                  </div>
                  <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-100 mt-1">
                    AI Match Evaluation
                  </h3>
                  <p className="text-xs text-slate-500 dark:text-slate-400">
                    High skill alignment with Python, FastAPI, and Distributed Architecture.
                  </p>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex flex-col gap-2 shrink-0">
                {job.canonical_apply_url && (
                  <a
                    href={job.canonical_apply_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center justify-center gap-2 px-4 py-2 text-xs font-semibold rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white shadow-xs transition-colors"
                  >
                    <span>Apply on Portal</span>
                    <ExternalLink className="h-3.5 w-3.5" />
                  </a>
                )}
                <button
                  onClick={handleDeactivate}
                  className="inline-flex items-center justify-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate-500 hover:text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/40 rounded-lg transition-colors cursor-pointer"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                  <span>Deactivate Job</span>
                </button>
              </div>
            </div>

            {/* Score Breakdown Bars */}
            <div className="mt-5 pt-4 border-t border-slate-200/80 dark:border-slate-800 grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
              <div>
                <span className="text-slate-600 dark:text-slate-400 font-medium">Stack Match</span>
                <div className="mt-1 flex items-center gap-2">
                  <div className="h-1.5 flex-1 rounded-full bg-slate-200 dark:bg-slate-800 overflow-hidden">
                    <div className="h-full bg-emerald-500" style={{ width: `${Math.min(job.relevance_score, 100)}%` }} />
                  </div>
                  <span className="font-semibold text-slate-700 dark:text-slate-300">{job.relevance_score}%</span>
                </div>
              </div>
              <div>
                <span className="text-slate-600 dark:text-slate-400 font-medium">Experience</span>
                <div className="mt-1 flex items-center gap-2">
                  <div className="h-1.5 flex-1 rounded-full bg-slate-200 dark:bg-slate-800 overflow-hidden">
                    <div className="h-full bg-indigo-500" style={{ width: '92%' }} />
                  </div>
                  <span className="font-semibold text-slate-700 dark:text-slate-300">92%</span>
                </div>
              </div>
              <div>
                <span className="text-slate-600 dark:text-slate-400 font-medium">Location</span>
                <div className="mt-1 flex items-center gap-2">
                  <div className="h-1.5 flex-1 rounded-full bg-slate-200 dark:bg-slate-800 overflow-hidden">
                    <div className="h-full bg-blue-500" style={{ width: '100%' }} />
                  </div>
                  <span className="font-semibold text-slate-700 dark:text-slate-300">100%</span>
                </div>
              </div>
              <div>
                <span className="text-slate-600 dark:text-slate-400 font-medium">Domain / Tier</span>
                <div className="mt-1 flex items-center gap-2">
                  <div className="h-1.5 flex-1 rounded-full bg-slate-200 dark:bg-slate-800 overflow-hidden">
                    <div className="h-full bg-purple-500" style={{ width: '95%' }} />
                  </div>
                  <span className="font-semibold text-slate-700 dark:text-slate-300">95%</span>
                </div>
              </div>
            </div>
          </div>

          {/* 1-Click Track in CRM Box */}
          <div className="p-4 rounded-xl border border-indigo-200 dark:border-indigo-800/60 bg-indigo-50/40 dark:bg-indigo-950/20 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-indigo-900 dark:text-indigo-300 flex items-center gap-1.5">
                <PlusCircle className="h-4 w-4 text-indigo-600" />
                Track Application in CRM
              </span>
            </div>
            <div className="flex flex-col sm:flex-row gap-2.5">
              <select
                value={applicationStatus}
                onChange={(e) => setApplicationStatus(e.target.value)}
                className="text-xs bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg px-3 py-2 text-slate-800 dark:text-slate-200 focus:outline-none focus:border-indigo-500"
              >
                <option value="drafted">Saved / Draft</option>
                <option value="applied">Applied</option>
                <option value="under_review">Under Review</option>
                <option value="interviewing">Interviewing</option>
                <option value="offered">Offered</option>
                <option value="rejected">Rejected</option>
              </select>
              <input
                type="text"
                placeholder="Optional notes (e.g. Applied with Resume v4, referral by Amit)..."
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                className="flex-1 text-xs bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg px-3 py-2 text-slate-800 dark:text-slate-200 placeholder-slate-400 focus:outline-none focus:border-indigo-500"
              />
              <Button
                variant="primary"
                size="sm"
                onClick={handleTrackApplication}
                isLoading={isApplying}
              >
                Save
              </Button>
            </div>
          </div>

          {/* Navigation Tabs */}
          <div className="border-b border-slate-200 dark:border-slate-800 flex gap-6">
            {(['overview', 'requirements', 'company', 'description'] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`pb-3 text-xs font-semibold capitalize border-b-2 transition-colors cursor-pointer ${
                  activeTab === tab
                    ? 'border-indigo-600 text-indigo-600 dark:text-indigo-400'
                    : 'border-transparent text-slate-500 hover:text-slate-800 dark:hover:text-slate-200'
                }`}
              >
                {tab}
              </button>
            ))}
          </div>

          {/* Tab Content */}
          {activeTab === 'overview' && (
            <div className="space-y-4 text-xs">
              <div className="grid grid-cols-2 gap-4">
                <div className="p-3 rounded-lg bg-slate-50 dark:bg-slate-800/40">
                  <span className="text-slate-600 dark:text-slate-400">Location Bucket</span>
                  <p className="font-semibold text-slate-800 dark:text-slate-200 mt-0.5">
                    {job.location_bucket || 'Bangalore'} {job.is_remote ? '(Remote)' : ''}
                  </p>
                </div>
                <div className="p-3 rounded-lg bg-slate-50 dark:bg-slate-800/40">
                  <span className="text-slate-600 dark:text-slate-400">Experience Requirement</span>
                  <p className="font-semibold text-slate-800 dark:text-slate-200 mt-0.5">
                    {job.experience_raw || `${job.experience_min ?? 4} - ${job.experience_max ?? 8} Years`}
                  </p>
                </div>
                <div className="p-3 rounded-lg bg-slate-50 dark:bg-slate-800/40">
                  <span className="text-slate-600 dark:text-slate-400">ATS Provider</span>
                  <p className="font-semibold text-slate-800 dark:text-slate-200 mt-0.5">
                    {job.ats_provider || 'Direct / Careers Portal'}
                  </p>
                </div>
                <div className="p-3 rounded-lg bg-slate-50 dark:bg-slate-800/40">
                  <span className="text-slate-600 dark:text-slate-400">First Discovered</span>
                  <p className="font-semibold text-slate-800 dark:text-slate-200 mt-0.5">
                    {new Date(job.first_seen_at).toLocaleDateString()}
                  </p>
                </div>
              </div>

              {/* Sources Aggregation */}
              <div className="mt-4">
                <h4 className="font-semibold text-slate-800 dark:text-slate-200 mb-2">
                  Discovered Across Sources ({job.sources?.length || 1})
                </h4>
                <div className="space-y-2">
                  {job.sources?.map((src) => (
                    <div
                      key={src.id}
                      className="p-3 rounded-lg border border-slate-200 dark:border-slate-800 flex items-center justify-between"
                    >
                      <div>
                        <span className="font-semibold text-slate-800 dark:text-slate-200">
                          {src.source_name}
                        </span>
                        <p className="text-[11px] text-slate-500">
                          Last confirmed active: {new Date(src.last_seen_at).toLocaleDateString()}
                        </p>
                      </div>
                      {src.source_apply_url && (
                        <a
                          href={src.source_apply_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-indigo-600 dark:text-indigo-400 hover:underline flex items-center gap-1 text-[11px]"
                        >
                          View Source Link
                          <ExternalLink className="h-3 w-3" />
                        </a>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {activeTab === 'requirements' && (
            <div className="space-y-4 text-xs">
              <div>
                <h4 className="font-semibold text-slate-800 dark:text-slate-200 mb-2">
                  Matched Target Skills ({job.matched_skills?.length || 0})
                </h4>
                <div className="flex flex-wrap gap-2">
                  {job.matched_skills?.map((skill, idx) => (
                    <span
                      key={idx}
                      className="inline-flex items-center gap-1.5 px-3 py-1 rounded-md bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800/80 font-medium"
                    >
                      <CheckCircle2 className="h-3.5 w-3.5" />
                      {skill}
                    </span>
                  ))}
                </div>
              </div>

              <div className="mt-4">
                <h4 className="font-semibold text-slate-800 dark:text-slate-200 mb-2">
                  Role Tags
                </h4>
                <div className="flex flex-wrap gap-2">
                  {job.tags?.map((tag, idx) => (
                    <span
                      key={idx}
                      className="px-2.5 py-1 rounded-md bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 font-medium"
                    >
                      #{tag}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          )}

          {activeTab === 'company' && (
            <div className="space-y-4 text-xs">
              <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/30 flex items-start gap-4">
                <CompanyAvatar name={job.company_name} size="lg" />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <h4 className="text-sm font-bold text-slate-900 dark:text-white">
                      {job.company_name}
                    </h4>
                    {job.company?.is_target && (
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-50 text-amber-700 border border-amber-200">
                        Target List
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-slate-500 mt-1">
                    Normalized key: <span className="font-mono">{job.company?.normalized_name || job.company_name.toLowerCase()}</span>
                  </p>
                  <div className="mt-3 flex gap-3">
                    {job.company?.website && (
                      <a
                        href={job.company.website}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-indigo-600 dark:text-indigo-400 hover:underline flex items-center gap-1 font-medium"
                      >
                        Company Website
                        <ExternalLink className="h-3 w-3" />
                      </a>
                    )}
                    {job.company?.career_url && (
                      <a
                        href={job.company.career_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-indigo-600 dark:text-indigo-400 hover:underline flex items-center gap-1 font-medium"
                      >
                        Official Careers Portal
                        <ExternalLink className="h-3 w-3" />
                      </a>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'description' && (
            <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/40 text-xs leading-relaxed text-slate-700 dark:text-slate-300 font-mono whitespace-pre-wrap max-h-96 overflow-y-auto">
              {job.description || 'Full raw description not ingested for this job source.'}
            </div>
          )}
        </div>
      )}
    </Drawer>
  );
};
