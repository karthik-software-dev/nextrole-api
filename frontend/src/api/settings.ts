import { apiClient } from './client';
import type { ApifyTestResult, SettingsData, UpdateSettingsPayload } from '../types/settings';

export const getSettings = async (): Promise<SettingsData> => {
  const response = await apiClient.get<SettingsData>('/settings');
  return response.data;
};

export const updateSettings = async (payload: UpdateSettingsPayload): Promise<SettingsData> => {
  const response = await apiClient.put<SettingsData>('/settings', payload);
  return response.data;
};

export const testApifyToken = async (token: string): Promise<ApifyTestResult> => {
  const response = await apiClient.post<ApifyTestResult>('/settings/test-apify', { token });
  return response.data;
};
