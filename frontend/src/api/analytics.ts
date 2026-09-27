import { apiClient } from './client';
import type { AnalyticsSummary } from '../types';

export interface AnalyticsQueryParams {
  range?: string;
  start_date?: string;
  end_date?: string;
}

export const getAnalyticsSummary = async (params?: AnalyticsQueryParams): Promise<AnalyticsSummary> => {
  const response = await apiClient.get<AnalyticsSummary>('/analytics/summary', { params });
  return response.data;
};
