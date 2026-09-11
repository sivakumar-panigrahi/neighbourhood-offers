import { apiClient } from './client';
import type { Claim } from '../types';

export const claimsApi = {
  /**
   * List all claims belonging to the authenticated shopper.
   */
  getMyClaims: async (statusFilter?: string): Promise<Claim[]> => {
    return apiClient.get<Claim[]>('/claims/my', {
      params: statusFilter ? { status: statusFilter } : undefined,
    });
  },

  /**
   * Get single claim details by ID (shopper only).
   */
  getClaim: async (id: number): Promise<Claim> => {
    return apiClient.get<Claim>(`/claims/${id}`);
  },

  /**
   * Claim an active offer (shoppers only).
   */
  claimOffer: async (offerId: number): Promise<Claim> => {
    return apiClient.post<Claim>(`/offers/${offerId}/claim`);
  },
};
