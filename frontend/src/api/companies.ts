import { apiClient } from './client';
import type { Company, CompanyDetail, PaginatedResponse } from '../types';

export const getCompanies = async (params: { page?: number; page_size?: number; is_target?: boolean; search?: string; location?: string } = {}): Promise<PaginatedResponse<Company>> => {
  const response = await apiClient.get<PaginatedResponse<Company>>('/companies', { params });
  return response.data;
};

export const getCompanyById = async (companyId: number): Promise<CompanyDetail> => {
  const response = await apiClient.get<CompanyDetail>(`/companies/${companyId}`);
  return response.data;
};
