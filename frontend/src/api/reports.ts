import { apiClient } from './client';
import type { MonthlyReport } from '../types';

export const reportsApi = {
  /**
   * Get monthly spend, remaining points, and busy days report for the shopkeeper's shop.
   */
  getMonthlyReport: async (month?: string): Promise<MonthlyReport> => {
    return apiClient.get<MonthlyReport>('/reports/monthly', {
      params: month ? { month } : undefined,
    });
  },
};
