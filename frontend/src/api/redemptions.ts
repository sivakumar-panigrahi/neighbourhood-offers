import { apiClient } from './client';
import type { RedemptionRequest, RedemptionResponse } from '../types';

export const redemptionsApi = {
  /**
   * Redeem a shopper claim code at counter checkout.
   */
  createRedemption: async (
    payload: RedemptionRequest,
    idempotencyKey?: string,
  ): Promise<RedemptionResponse> => {
    return apiClient.post<RedemptionResponse>('/redemptions', payload, {
      headers: idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : undefined,
    });
  },

  /**
   * Lookup redemption record by ID.
   */
  getRedemption: async (id: number): Promise<RedemptionResponse> => {
    return apiClient.get<RedemptionResponse>(`/redemptions/${id}`);
  },

  /**
   * Lookup redemption record by claim code.
   */
  getRedemptionByCode: async (claimCode: string): Promise<RedemptionResponse> => {
    return apiClient.get<RedemptionResponse>(`/redemptions/code/${claimCode}`);
  },
};
