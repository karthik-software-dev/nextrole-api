import type { ExperienceDistribution, SalaryDistribution } from './analytics';

export interface PaginationMeta {
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface PaginatedResponse<T> {
  items: T[];
  meta: PaginationMeta;
}

export interface JobSource {
  id: number;
  source_name: string;
  source_job_id: string | null;
  discovery_url: string | null;
  source_apply_url: string | null;
  source_posted_at: string | null;
  first_seen_at: string;
  last_seen_at: string;
}

export interface JobCompany {
  id: number;
  name: string;
  normalized_name: string;
  website: string | null;
  career_url: string | null;
  ats_provider: string | null;
  is_target: boolean;
}

export interface JobSummary {
  id: number;
  company_id: number;
  company_name: string;
  title: string;
  location: string | null;
  city: string | null;
  location_bucket: string;
  is_remote: boolean;
  experience_min: number | null;
  experience_max: number | null;
  experience_raw: string | null;
  salary_raw: string | null;
  salary_min?: number | null;
  salary_max?: number | null;
  currency?: string | null;
  canonical_apply_url: string | null;
  apply_type: string;
  ats_provider: string | null;
  relevance_score: number;
  matched_skills: string[];
  priority_score: number;
  priority_tier: string;
  match_percentage?: number;
  status: string;
  application_status?: string | null;
  source_count: number;
  is_active: boolean;
  tags: string[];
  description_snippet?: string | null;
  first_seen_at: string;
  last_seen_at: string;
}

export interface FilterCountItem {
  key: string;
  label: string;
  count: number;
}

export interface FilterCounts {
  total_active?: number;
  work_modes: FilterCountItem[];
  locations: FilterCountItem[];
  experience_buckets: FilterCountItem[];
  salary_buckets: FilterCountItem[];
  tiers?: FilterCountItem[];
  sources?: FilterCountItem[];
  application_statuses?: FilterCountItem[];
  freshness_buckets?: FilterCountItem[];
}

export interface JobDetail extends JobSummary {
  description: string | null;
  company: JobCompany | null;
  sources: JobSource[];
  application_status: string | null;
  metadata_json: Record<string, any>;
}

export interface Company {
  id: number;
  name: string;
  normalized_name: string;
  website: string | null;
  career_url: string | null;
  ats_provider: string | null;
  is_target: boolean;
  is_active: boolean;
  active_jobs_count: number;
  created_at: string;
}

export interface CompanyDetail extends Company {
  open_jobs: JobSummary[];
  metadata_json: Record<string, any>;
}

export interface ApplicationHistory {
  id: number;
  previous_status: string | null;
  new_status: string;
  changed_at: string;
  note: string | null;
}

export interface Application {
  id: number;
  user_id: number;
  job_id: number;
  status: string;
  applied_at: string | null;
  resume_version: string | null;
  portal_type: string | null;
  notes: string | null;
  follow_up_date: string | null;
  is_active: boolean;
  job: JobSummary | null;
  history: ApplicationHistory[];
  created_at: string;
  updated_at: string;
}

export interface DiscoveryTrendItem {
  date: string;
  count: number;
}

export interface LocationStatItem {
  name: string;
  count: number;
}

export interface RecentActivityItem {
  id: string;
  title: string;
  description?: string | null;
  timestamp: string;
  activity_type: string;
}

export interface DailyCadenceRun {
  run_number: number;
  time_slot: string;
  label: string;
  status: 'completed' | 'active' | 'scheduled';
  jobs_collected: number;
  cumulative_jobs: number;
  runner: string;
}

export interface TopHiringCompany {
  name: string;
  job_count: number;
  locations: string[];
  is_remote: boolean;
}

export interface DedupEfficiency {
  canonical_jobs: number;
  multi_source_jobs: number;
  duplicates_filtered: number;
  suppression_rate_pct: number;
}

export interface DashboardSummary {
  total_jobs: number;
  active_jobs: number;
  inactive_jobs: number;
  tier1_jobs: number;
  tier2_jobs: number;
  total_companies: number;
  total_sources: number;
  location_breakdown: {
    bangalore: number;
    chennai: number;
    remote?: number;
    abroad?: number;
    other: number;
  };
  application_breakdown: {
    drafted: number;
    applied: number;
    under_review: number;
    interviewing: number;
    offered: number;
    rejected: number;
  };
  sources_breakdown?: Array<{
    name: string;
    count: number;
  }>;
  new_jobs?: number;
  discovery_trend?: DiscoveryTrendItem[];
  locations_breakdown?: LocationStatItem[];
  recent_activities?: RecentActivityItem[];
  experience_distribution?: ExperienceDistribution[];
  salary_distribution?: SalaryDistribution[];
  daily_cadence?: DailyCadenceRun[];
  top_hiring_companies?: TopHiringCompany[];
  dedup_efficiency?: DedupEfficiency | null;
  latest_pipeline?: PipelineRunInfo | null;
}

export interface PipelineRunInfo {
  id?: number;
  pipeline_id?: string;
  pipeline_iid?: string;
  pipeline_url?: string;
  source?: string;
  status?: string;
  triggered_by?: string;
  jobs_collected?: number;
  jobs_synced?: number;
  duration_seconds?: number | null;
  started_at?: string;
  completed_at?: string | null;
}

export interface DiscoveryStatus {
  is_running: boolean;
  last_run_at: string | null;
  last_status: string;
  last_jobs_found: number;
  last_jobs_synced: number;
  last_error: string | null;
  last_duration_seconds?: number;
  total_runs?: number;
  latest_pipeline?: PipelineRunInfo | null;
}

export interface DiscoveryLog {
  id: string;
  timestamp: string;
  level: string;
  tag: string;
  message: string;
}

export interface DiscoverySource {
  id: number;
  name: string;
  slug: string;
  engine_type: string;
  status: 'Active' | 'Integrated' | 'Standby' | 'Blocked' | string;
  last_yield: number;
  latency: string;
  ats_detection: string;
  enabled: boolean;
  priority: string;
  total_scraped?: number;
  tier1_count?: number;
  last_synced_at?: string | null;
}

export interface NotificationItem {
  id: number;
  title: string;
  message: string;
  type: 'discovery' | 'job' | 'application' | 'system' | string;
  is_read: boolean;
  link: string | null;
  created_at: string;
}

export interface NotificationListResponse {
  items: NotificationItem[];
  unread_count: number;
}

export interface SystemHealth {
  status: string;
  database: string;
  version: string;
  memory_rss_mb: number | null;
}

export * from './analytics';
export * from './settings';


