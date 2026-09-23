import { apiClient } from './client';
import type { DiscoveryStatus } from '../types';

export const getDiscoveryStatus = async (): Promise<DiscoveryStatus> => {
  const response = await apiClient.get<DiscoveryStatus>('/discovery/status');
  return response.data;
};

export const triggerDiscoveryRun = async (params: { source?: string; location?: string; use_cache?: boolean } = {}): Promise<{ message: string; status: string }> => {
  const response = await apiClient.post<{ message: string; status: string }>('/discovery/run', params);
  return response.data;
};
