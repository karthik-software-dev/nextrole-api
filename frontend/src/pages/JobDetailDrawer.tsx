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
import { playJobApplySound } from '../utils/audio';
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
    playJobApplySound();
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

  const cleanMatchedSkills = job
    ? (job.matched_skills || []).filter(
        (s) =>
          !s.includes('Synergy') &&
          !s.includes('Penalty') &&
          !s.includes('Role') &&
          !s.includes('Exp') &&
          !s.includes('Sweet-Spot')
      )
    : [];

  const evalSubtitle = cleanMatchedSkills.length > 0
    ? `High skill alignment with ${cleanMatchedSkills.slice(0, 3).join(', ')}.`
    : job
    ? `Evaluated as ${job.priority_tier} priority matching candidate preferences.`
    : '';

  const expAlignmentPct = job?.matched_skills?.some((s) => s.includes('Sweet-Spot'))
    ? 100
    : job?.matched_skills?.some((s) => s.includes('Penalty') || s.includes('High Exp'))
    ? 55
    : job?.experience_min !== null
    ? 85
    : 70;

  const locAlignmentPct =
    job?.is_remote || job?.location_bucket === 'BANGALORE'
      ? 100
      : job?.location_bucket === 'CHENNAI'
      ? 85
      : 70;

  const tierLower = (job?.priority_tier || '').toLowerCase();
  const tierAlignmentPct =
    tierLower.includes('tier 1') || tierLower.includes('tier-1') || tierLower.includes('tier1')
      ? 95
      : tierLower.includes('tier 2') || tierLower.includes('tier-2') || tierLower.includes('tier2')
      ? 80
      : 65;

  const matchPct = job
    ? job.match_percentage ?? (job.relevance_score > 50
        ? Math.min(Math.round(job.relevance_score), 100)
        : Math.min(100, Math.round((job.relevance_score / 35) * 100)))
    : 0;

  const stackPct = matchPct;

  return (
    <Drawer
      isOpen={!!jobId}
      onClose={onClose}
      width="2xl"
      title={
        job ? (
          <div className="flex items-center gap-3.5">
            <CompanyAvatar name={job.company_name} size="md" />
            <div className="min-w-0">
              <h2 className="text-[19px] sm:text-[21px] font-bold text-slate-900 dark:text-white truncate tracking-tight">
                {job.title}
              </h2>
              <p className="mt-0.5 text-[13px] font-semibold text-slate-700 dark:text-slate-300">
                {job.company_name} • {job.location || 'India'}
              </p>
            </div>
          </div>
        ) : (
          <div className="text-[15px] font-semibold text-slate-700 dark:text-slate-300">Loading Job Details...</div>
        )
      }
    >
      {isLoading ? (
        <div className="flex flex-col items-center justify-center py-20 space-y-3">
          <Loader2 className="h-8 w-8 animate-spin text-indigo-600" />
          <p className="text-[13px] font-semibold text-slate-600 dark:text-slate-400">Loading intelligence data...</p>
        </div>
      ) : !job ? (
        <div className="py-12 text-center text-[14px] font-medium text-slate-600 dark:text-slate-400">Job details not available.</div>
      ) : (
        <div className="space-y-6">
          {/* Top Score & Highlights Card */}
          <div className="rounded-2xl border border-slate-200/90 dark:border-slate-800 bg-white dark:bg-[#111726] p-5 shadow-xs">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div className="flex items-center gap-4">
                {/* Circular / Large Score Badge */}
                <div className="h-16 w-16 rounded-2xl bg-gradient-to-br from-indigo-600 to-indigo-700 text-white flex flex-col items-center justify-center shadow-md shadow-indigo-500/25 ring-1 ring-inset ring-white/20 shrink-0">
                  <span className="text-[22px] font-bold leading-none">{matchPct}%</span>
                  <span className="text-[9.5px] uppercase tracking-wider font-bold opacity-90 mt-0.5">Match</span>
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <TierBadge tier={job.priority_tier} />
                    {job.application_status && (
                      <ApplicationStatusBadge status={job.application_status} size="sm" />
                    )}
                  </div>
                  <h3 className="text-[16.5px] font-bold text-slate-900 dark:text-white mt-1.5 leading-snug">
                    Match Evaluation
                  </h3>
                  <p className="text-[13px] font-medium text-slate-700 dark:text-slate-300 mt-0.5">
                    {evalSubtitle}
                  </p>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex flex-col gap-1.5 shrink-0">
                {job.canonical_apply_url && (
                  <>
                    <a
                      href={job.canonical_apply_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      onClick={() => playJobApplySound()}
                      className="inline-flex items-center justify-center gap-2 px-4.5 py-2.5 text-[13.5px] font-bold rounded-xl bg-indigo-600 hover:bg-indigo-700 active:scale-95 text-white shadow-xs transition-all cursor-pointer"
                    >
                      <span>Apply on Portal</span>
                      <ExternalLink className="h-3.5 w-3.5" />
                    </a>
                    <span className="text-[10.5px] text-slate-400 dark:text-slate-500 text-center font-medium">
                      ↗ Opens official company ATS in new tab
                    </span>
                  </>
                )}
                <button
                  onClick={handleDeactivate}
                  className="inline-flex items-center justify-center gap-1.5 px-3 py-1.5 text-[12.5px] font-semibold text-slate-500 hover:text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/40 rounded-xl transition-colors cursor-pointer"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                  <span>Deactivate Job</span>
                </button>
              </div>
            </div>

            {/* Score Breakdown Bars */}
            <div className="mt-5 pt-4 border-t border-slate-200/80 dark:border-slate-800 grid grid-cols-2 sm:grid-cols-4 gap-3.5 text-[12px]">
              <div>
                <span className="text-slate-800 dark:text-slate-200 font-bold text-[12px]">Stack Match</span>
                <div className="mt-1.5 flex items-center gap-2">
                  <div className="h-2 flex-1 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
                    <div className="h-full bg-emerald-500 rounded-full" style={{ width: `${stackPct}%` }} />
                  </div>
                  <span className="font-bold text-slate-900 dark:text-white text-[12.5px]">{job.relevance_score}%</span>
                </div>
              </div>
              <div>
                <span className="text-slate-800 dark:text-slate-200 font-bold text-[12px]">Experience</span>
                <div className="mt-1.5 flex items-center gap-2">
                  <div className="h-2 flex-1 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
                    <div className="h-full bg-indigo-500 rounded-full" style={{ width: `${expAlignmentPct}%` }} />
                  </div>
                  <span className="font-bold text-slate-900 dark:text-white text-[12.5px]">{expAlignmentPct}%</span>
                </div>
              </div>
              <div>
                <span className="text-slate-800 dark:text-slate-200 font-bold text-[12px]">Location</span>
                <div className="mt-1.5 flex items-center gap-2">
                  <div className="h-2 flex-1 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
                    <div className="h-full bg-blue-500 rounded-full" style={{ width: `${locAlignmentPct}%` }} />
                  </div>
                  <span className="font-bold text-slate-900 dark:text-white text-[12.5px]">{locAlignmentPct}%</span>
                </div>
              </div>
              <div>
                <span className="text-slate-800 dark:text-slate-200 font-bold text-[12px]">Domain / Tier</span>
                <div className="mt-1.5 flex items-center gap-2">
                  <div className="h-2 flex-1 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
                    <div className="h-full bg-purple-500 rounded-full" style={{ width: `${tierAlignmentPct}%` }} />
                  </div>
                  <span className="font-bold text-slate-900 dark:text-white text-[12.5px]">{tierAlignmentPct}%</span>
                </div>
              </div>
            </div>
          </div>

          {/* 1-Click Track in CRM Box */}
          <div className="p-5 rounded-2xl border border-indigo-200/90 dark:border-indigo-900/60 bg-indigo-50/60 dark:bg-indigo-950/30 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-[14px] font-bold text-indigo-950 dark:text-indigo-200 flex items-center gap-2">
                <PlusCircle className="h-4.5 w-4.5 text-indigo-600 dark:text-indigo-400" />
                Track Application in CRM
              </span>
            </div>
            <div className="flex flex-col sm:flex-row gap-2.5">
              <select
                value={applicationStatus}
                onChange={(e) => setApplicationStatus(e.target.value)}
                className="h-10 text-[13.5px] font-medium bg-white dark:bg-[#111726] border border-slate-300 dark:border-slate-700 rounded-xl px-3.5 py-2 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 shadow-2xs"
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
                className="flex-1 h-10 text-[13.5px] font-medium bg-white dark:bg-[#111726] border border-slate-300 dark:border-slate-700 rounded-xl px-3.5 py-2 text-slate-900 dark:text-slate-100 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 shadow-2xs"
              />
              <Button
                variant="primary"
                size="md"
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
                className={`pb-3 text-[14.5px] capitalize border-b-2 transition-all cursor-pointer ${activeTab === tab
                    ? 'border-indigo-600 text-indigo-600 dark:text-indigo-400 font-bold'
                    : 'border-transparent text-slate-700 hover:text-slate-900 dark:text-slate-300 dark:hover:text-white font-semibold'
                  }`}
              >
                {tab}
              </button>
            ))}
          </div>

          {/* Tab Content */}
          {activeTab === 'overview' && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-3.5">
                <div className="p-4 rounded-2xl border border-slate-200/80 dark:border-slate-800 bg-white dark:bg-[#111726] shadow-2xs hover:border-slate-300 dark:hover:border-slate-700 transition-colors">
                  <span className="text-[12px] font-bold uppercase tracking-wider text-slate-700 dark:text-slate-400">Location Bucket</span>
                  <p className="font-bold text-[15.5px] text-slate-900 dark:text-white mt-1 leading-snug">
                    {job.location_bucket || job.location || (job.is_remote ? 'Remote' : 'Not specified')} {job.is_remote && (job.location_bucket || job.location) ? '(Remote)' : ''}
                  </p>
                </div>
                <div className="p-4 rounded-2xl border border-slate-200/80 dark:border-slate-800 bg-white dark:bg-[#111726] shadow-2xs hover:border-slate-300 dark:hover:border-slate-700 transition-colors">
                  <span className="text-[12px] font-bold uppercase tracking-wider text-slate-700 dark:text-slate-400">Experience Requirement</span>
                  <p className="font-bold text-[15.5px] text-slate-900 dark:text-white mt-1 leading-snug">
                    {job.experience_raw || (job.experience_min !== null ? `${job.experience_min} - ${job.experience_max ?? '+'} Years` : 'Not specified')}
                  </p>
                </div>
                <div className="p-4 rounded-2xl border border-slate-200/80 dark:border-slate-800 bg-white dark:bg-[#111726] shadow-2xs hover:border-slate-300 dark:hover:border-slate-700 transition-colors">
                  <span className="text-[12px] font-bold uppercase tracking-wider text-slate-700 dark:text-slate-400">ATS Provider</span>
                  <p className="font-bold text-[15.5px] text-slate-900 dark:text-white mt-1 leading-snug">
                    {job.ats_provider || 'Direct / Careers Portal'}
                  </p>
                </div>
                <div className="p-4 rounded-2xl border border-slate-200/80 dark:border-slate-800 bg-white dark:bg-[#111726] shadow-2xs hover:border-slate-300 dark:hover:border-slate-700 transition-colors">
                  <span className="text-[12px] font-bold uppercase tracking-wider text-slate-700 dark:text-slate-400">First Discovered</span>
                  <p className="font-bold text-[15.5px] text-slate-900 dark:text-white mt-1 leading-snug">
                    {new Date(job.first_seen_at).toLocaleDateString()}
                  </p>
                </div>
              </div>

              {/* Sources Aggregation */}
              <div className="mt-5">
                <h4 className="font-bold text-[16px] text-slate-900 dark:text-white mb-3">
                  Discovered Across Sources ({job.sources?.length || 1})
                </h4>
                <div className="space-y-2.5">
                  {job.sources?.map((src) => (
                    <div
                      key={src.id}
                      className="p-4 rounded-2xl border border-slate-200/80 dark:border-slate-800 bg-white dark:bg-[#111726] shadow-2xs flex items-center justify-between"
                    >
                      <div>
                        <span className="font-bold text-[14px] text-slate-900 dark:text-white">
                          {src.source_name}
                        </span>
                        <p className="text-[12px] font-medium text-slate-600 dark:text-slate-400 mt-0.5">
                          Last confirmed active: {new Date(src.last_seen_at).toLocaleDateString()}
                        </p>
                      </div>
                      {(src.source_apply_url || src.discovery_url) && (
                        <a
                          href={(src.source_apply_url || src.discovery_url)!}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-indigo-600 dark:text-indigo-400 hover:underline flex items-center gap-1.5 text-[13px] font-bold"
                        >
                          View Source Link
                          <ExternalLink className="h-3.5 w-3.5" />
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
                <h4 className="font-bold text-[15px] text-slate-900 dark:text-white mb-2.5">
                  Matched Target Skills ({job.matched_skills?.length || 0})
                </h4>
                <div className="flex flex-wrap gap-2">
                  {job.matched_skills?.map((skill, idx) => (
                    <span
                      key={idx}
                      className="inline-flex items-center gap-1.5 px-3 py-1 rounded-xl bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800/80 text-[12px] font-semibold"
                    >
                      <CheckCircle2 className="h-3.5 w-3.5" />
                      {skill}
                    </span>
                  ))}
                </div>
              </div>

              <div className="mt-4">
                <h4 className="font-bold text-[15px] text-slate-900 dark:text-white mb-2.5">
                  Role Tags
                </h4>
                <div className="flex flex-wrap gap-2">
                  {job.tags?.map((tag, idx) => (
                    <span
                      key={idx}
                      className="px-3 py-1 rounded-xl bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 text-[12px] font-medium"
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
              <div className="p-5 rounded-2xl border border-slate-200/80 dark:border-slate-800 bg-white dark:bg-[#111726] shadow-sm flex items-start gap-4">
                <CompanyAvatar name={job.company_name} size="lg" />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <h4 className="text-[16px] font-bold text-slate-900 dark:text-white">
                      {job.company_name}
                    </h4>
                    {job.company?.is_target && (
                      <span className="px-2 py-0.5 rounded-full text-[11px] font-bold bg-amber-50 text-amber-700 border border-amber-200">
                        Target List
                      </span>
                    )}
                  </div>
                  <p className="text-[12.5px] text-slate-500 mt-1">
                    Normalized key: <span className="font-mono">{job.company?.normalized_name || job.company_name.toLowerCase()}</span>
                  </p>
                  <div className="mt-3 flex gap-4">
                    {job.company?.website && (
                      <a
                        href={job.company.website}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-indigo-600 dark:text-indigo-400 hover:underline flex items-center gap-1 text-[12.5px] font-medium"
                      >
                        Company Website
                        <ExternalLink className="h-3.5 w-3.5" />
                      </a>
                    )}
                    {job.company?.career_url && (
                      <a
                        href={job.company.career_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-indigo-600 dark:text-indigo-400 hover:underline flex items-center gap-1 text-[12.5px] font-medium"
                      >
                        Official Careers Portal
                        <ExternalLink className="h-3.5 w-3.5" />
                      </a>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'description' && (
            <div className="p-5 rounded-2xl border border-slate-200/80 dark:border-slate-800 bg-slate-50/50 dark:bg-[#111726] text-[12.5px] leading-relaxed text-slate-700 dark:text-slate-300 font-mono whitespace-pre-wrap max-h-96 overflow-y-auto">
              {job.description || 'Full raw description not ingested for this job source.'}
            </div>
          )}
        </div>
      )}
    </Drawer>
  );
};
