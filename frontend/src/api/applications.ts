import { apiClient } from './client';
import type { Application } from '../types';

export interface CreateApplicationPayload {
  job_id: number;
  user_id?: number;
  resume_version?: string;
  portal_type?: string;
  notes?: string;
  initial_status?: string;
}

export interface UpdateApplicationPayload {
  status?: string;
  resume_version?: string;
  portal_type?: string;
  notes?: string;
  follow_up_date?: string;
  note_for_history?: string;
}

export const getApplications = async (params: { status?: string; user_id?: number } = {}): Promise<Application[]> => {
  const response = await apiClient.get<Application[]>('/applications', { params });
  return response.data;
};

export const getApplicationById = async (appId: number): Promise<Application> => {
  const response = await apiClient.get<Application>(`/applications/${appId}`);
  return response.data;
};

export const createApplication = async (payload: CreateApplicationPayload): Promise<Application> => {
  const response = await apiClient.post<Application>('/applications', payload);
  return response.data;
};

export const updateApplication = async (appId: number, payload: UpdateApplicationPayload): Promise<Application> => {
  const response = await apiClient.patch<Application>(`/applications/${appId}`, payload);
  return response.data;
};

export const deleteApplicationByJobId = async (jobId: number): Promise<void> => {
  await apiClient.delete(`/applications/job/${jobId}`);
};
