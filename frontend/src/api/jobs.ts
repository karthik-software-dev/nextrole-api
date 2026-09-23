import { apiClient } from './client';
import type { JobDetail, JobSummary, PaginatedResponse } from '../types';

export interface GetJobsParams {
  page?: number;
  page_size?: number;
  location?: string;
  tier?: string;
  is_remote?: boolean;
  max_exp?: number;
  min_score?: number;
  search?: string;
  tag?: string;
  active_only?: boolean;
}

export const getJobs = async (params: GetJobsParams = {}): Promise<PaginatedResponse<JobSummary>> => {
  const response = await apiClient.get<PaginatedResponse<JobSummary>>('/jobs', { params });
  return response.data;
};

export const getJobById = async (jobId: number): Promise<JobDetail> => {
  const response = await apiClient.get<JobDetail>(`/jobs/${jobId}`);
  return response.data;
};

export const deactivateJob = async (jobId: number): Promise<{ message: string; job_id: number; is_active: boolean }> => {
  const response = await apiClient.patch(`/jobs/${jobId}/deactivate`);
  return response.data;
};
