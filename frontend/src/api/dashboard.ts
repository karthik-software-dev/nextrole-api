import { apiClient } from './client';
import type { DashboardSummary } from '../types';

export interface DashboardQueryParams {
  range?: string;
  start_date?: string;
  end_date?: string;
}

export const getDashboardSummary = async (params?: DashboardQueryParams): Promise<DashboardSummary> => {
  const response = await apiClient.get<DashboardSummary>('/dashboard/summary', { params });
  return response.data;
};

