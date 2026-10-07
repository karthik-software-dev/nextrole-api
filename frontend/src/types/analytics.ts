export interface AnalyticsKpiData {
  applications: number;
  applications_prev: number;
  applications_change_pct: number;
  applications_subtext?: string;
  interviews: number;
  interviews_prev: number;
  interviews_change_pct: number;
  interviews_subtext?: string;
  response_rate: number;
  response_rate_prev: number;
  response_rate_diff_pts: number;
  response_rate_subtext?: string;
  interview_conversion: number;
  interview_conversion_prev: number;
  interview_conversion_diff_pts: number;
  conversion_subtext?: string;
}

export interface MatchScoreBucket {
  range_label: string;
  count: number;
  percentage: number;
}

export interface SkillFrequency {
  skill: string;
  count: number;
}

export interface ExperienceDistribution {
  level: string;
  count: number;
}

export interface SalaryDistribution {
  bracket: string;
  count: number;
}

export interface ApplyChannelItem {
  channel: string;
  count: number;
  percentage: number;
  description: string;
}

export interface TopHiringCompany {
  name: string;
  active_jobs: number;
}

export interface LocationStatItem {
  name: string;
  count: number;
}

export interface JobTitleStat {
  title: string;
  count: number;
}

export interface WorkModeStat {
  mode: string;
  count: number;
  percentage: number;
}

export interface TechStackPairStat {
  pair: string;
  skill: string;
  count: number;
  percentage: number;
}

export interface JobIntelligence {
  match_scores: MatchScoreBucket[];
  top_skills: SkillFrequency[];
  experience_distribution?: ExperienceDistribution[];
  salary_distribution?: SalaryDistribution[];
  apply_channels?: ApplyChannelItem[];
  top_hiring_companies?: TopHiringCompany[];
  locations?: LocationStatItem[];
  top_job_titles?: JobTitleStat[];
  work_modes?: WorkModeStat[];
  tech_stack_pairs?: TechStackPairStat[];
}

export interface ApplicationTimelineItem {
  date: string;
  count: number;
}

export interface ApplicationStatusItem {
  status: string;
  count: number;
  percentage: number;
  color: string;
}

export interface ApplicationFunnelStep {
  stage: string;
  count: number;
  conversion_rate: number;
}

export interface ChannelYield {
  portal: string;
  applied: number;
  interviews: number;
  conversion_rate: number;
}

export interface ApplicationAnalytics {
  applications_over_time: ApplicationTimelineItem[];
  status_distribution: ApplicationStatusItem[];
  funnel: ApplicationFunnelStep[];
  channel_yield?: ChannelYield[];
  stale_applications_count?: number;
}

export interface SourceContributionItem {
  source: string;
  count: number;
  percentage: number;
}

export interface TierTriageItem {
  tier: string;
  label: string;
  count: number;
  percentage: number;
  color: string;
}

export interface ApplyGatewayItem {
  gateway: string;
  count: number;
  percentage: number;
  color: string;
}

export interface PipelineAnalytics {
  jobs_collected: number;
  jobs_normalized: number;
  duplicates_removed: number;
  relevant_jobs: number;
  actionable_jobs: number;
  filtering_efficiency_pct: number;
  filter_out_pct: number;
  relevance_rate_pct?: number;
  actionable_rate_pct?: number;
  dedup_ratio?: number;
  sources_breakdown?: SourceContributionItem[];
  tier_breakdown?: TierTriageItem[];
  gateways_breakdown?: ApplyGatewayItem[];
}

export type AgentPerformance = PipelineAnalytics;

export interface AnalyticsSummary {
  kpis: AnalyticsKpiData;
  job_intelligence: JobIntelligence;
  application_analytics: ApplicationAnalytics;
  agent_performance: PipelineAnalytics;
  pipeline_analytics?: PipelineAnalytics;
}
