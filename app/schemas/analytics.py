from datetime import date
from pydantic import BaseModel, Field


class AnalyticsKpiData(BaseModel):
    applications: int = Field(..., description="Total applications submitted in the period")
    applications_prev: int = Field(0, description="Applications submitted in previous period")
    applications_change_pct: float = Field(0.0, description="Relative percentage change in applications")
    applications_subtext: str = Field("", description="Meaningful breakdown text for applications")
    
    interviews: int = Field(..., description="Applications in interview/offer stage in the period")
    interviews_prev: int = Field(0, description="Applications in interview stage in previous period")
    interviews_change_pct: float = Field(0.0, description="Relative percentage change in interviews")
    interviews_subtext: str = Field("", description="Meaningful breakdown text for interviews")
    
    response_rate: float = Field(..., description="Positive response rate (interview+offer / submitted) %")
    response_rate_prev: float = Field(0.0, description="Response rate in previous period %")
    response_rate_diff_pts: float = Field(0.0, description="Percentage-point difference in response rate")
    response_rate_subtext: str = Field("", description="Meaningful breakdown text for response rate")
    
    interview_conversion: float = Field(..., description="Interview-to-offer conversion rate %")
    interview_conversion_prev: float = Field(0.0, description="Interview conversion rate in previous period %")
    interview_conversion_diff_pts: float = Field(0.0, description="Percentage-point difference in conversion rate")
    conversion_subtext: str = Field("", description="Meaningful breakdown text for conversion rate")


class MatchScoreBucketOut(BaseModel):
    range_label: str
    count: int
    percentage: float


class SkillFrequencyOut(BaseModel):
    skill: str
    count: int


class ExperienceDistributionOut(BaseModel):
    level: str
    count: int


class SalaryDistributionOut(BaseModel):
    bracket: str
    count: int


class JobIntelligenceOut(BaseModel):
    match_scores: list[MatchScoreBucketOut]
    top_skills: list[SkillFrequencyOut]
    experience_distribution: list[ExperienceDistributionOut]
    salary_distribution: list[SalaryDistributionOut]


class ApplicationTimelineItemOut(BaseModel):
    date: str
    count: int


class ApplicationStatusItemOut(BaseModel):
    status: str
    count: int
    percentage: float
    color: str


class ApplicationFunnelStepOut(BaseModel):
    stage: str
    count: int
    conversion_rate: float


class ApplicationAnalyticsOut(BaseModel):
    applications_over_time: list[ApplicationTimelineItemOut]
    status_distribution: list[ApplicationStatusItemOut]
    funnel: list[ApplicationFunnelStepOut]


class AgentPerformanceOut(BaseModel):
    jobs_collected: int
    jobs_normalized: int
    duplicates_removed: int
    relevant_jobs: int
    actionable_jobs: int
    filtering_efficiency_pct: float
    filter_out_pct: float
    relevance_rate_pct: float = 0.0
    actionable_rate_pct: float = 0.0


class AnalyticsSummaryOut(BaseModel):
    kpis: AnalyticsKpiData
    job_intelligence: JobIntelligenceOut
    application_analytics: ApplicationAnalyticsOut
    agent_performance: AgentPerformanceOut
