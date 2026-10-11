import { apiClient } from './client';
import type { DiscoveryStatus, DiscoverySource, SystemHealth } from '../types';

export const getSystemHealth = async (): Promise<SystemHealth> => {
  const response = await apiClient.get<SystemHealth>('/health');
  return response.data;
};

export const getDiscoveryStatus = async (): Promise<DiscoveryStatus> => {
  const response = await apiClient.get<DiscoveryStatus>('/discovery/status');
  return response.data;
};

export const getDiscoverySources = async (): Promise<DiscoverySource[]> => {
  const response = await apiClient.get<DiscoverySource[]>('/discovery/sources');
  return response.data;
};

export const triggerDiscoveryRun = async (params: { source?: string; location?: string; use_cache?: boolean } = {}): Promise<{ message: string; status: string }> => {
  const response = await apiClient.post<{ message: string; status: string }>('/discovery/run', params);
  return response.data;
};

