import { apiClient } from './client';

export interface AuthUser {
  id: number;
  name: string;
  email: string;
  target_role: string;
  is_active: boolean;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: AuthUser;
}

export async function loginApi(credentials: LoginRequest): Promise<LoginResponse> {
  const response = await apiClient.post<LoginResponse>('/auth/login', credentials);
  return response.data;
}

export async function getMeApi(): Promise<AuthUser> {
  const response = await apiClient.get<AuthUser>('/auth/me');
  return response.data;
}

export async function logoutApi(): Promise<{ message: string }> {
  const response = await apiClient.post<{ message: string }>('/auth/logout');
  return response.data;
}
