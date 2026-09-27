import { apiClient } from './client';
import type { NotificationListResponse } from '../types';

export const getNotifications = async (limit: number = 30): Promise<NotificationListResponse> => {
  const response = await apiClient.get<NotificationListResponse>('/notifications', {
    params: { limit },
  });
  return response.data;
};

export const markNotificationRead = async (id: number): Promise<void> => {
  await apiClient.post(`/notifications/${id}/read`);
};

export const markAllNotificationsRead = async (): Promise<void> => {
  await apiClient.post('/notifications/mark-all-read');
};
