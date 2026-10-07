import axios from 'axios';

export const API_BASE_URL = import.meta.env.VITE_API_URL || '/api/v1';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 15000,
});

apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('nextrole_token');
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const isLoginEndpoint = error.config?.url?.includes('/auth/login');
    if (error.response?.status === 401 && !isLoginEndpoint && !window.location.pathname.includes('/login')) {
      localStorage.removeItem('nextrole_token');
      localStorage.removeItem('nextrole_user');
      window.location.href = '/login';
    }
    const message = error.response?.data?.detail || error.message || 'An unexpected error occurred';
    console.error(`[API Error] ${error.config?.url}:`, message);
    return Promise.reject(new Error(message));
  }
);

