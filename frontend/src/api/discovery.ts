import { apiClient } from './client';
import type { DiscoveryStatus, DiscoverySource, DiscoveryLog, SystemHealth } from '../types';

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

export const getDiscoveryLogs = async (sinceId: number = 0): Promise<DiscoveryLog[]> => {
  const response = await apiClient.get<DiscoveryLog[]>('/discovery/logs', { params: { since_id: sinceId } });
  return response.data;
};

export const clearDiscoveryLogs = async (): Promise<{ message: string }> => {
  const response = await apiClient.delete<{ message: string }>('/discovery/logs');
  return response.data;
};


