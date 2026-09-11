import { apiClient } from './client';
import type { PointsBalance, PointsTopUpRequest, RedemptionResponse, Shop } from '../types';

export const shopsApi = {
  /**
   * Get shop profile for the authenticated shopkeeper.
   */
  getMyShop: async (): Promise<Shop> => {
    return apiClient.get<Shop>('/shops/me');
  },

  /**
   * Create a shop profile for the shopkeeper.
   */
  createShop: async (data: { name: string; address: string; city: string; latitude?: number; longitude?: number }): Promise<Shop> => {
    return apiClient.post<Shop>('/shops', data);
  },

  /**
   * Get current points account balance for the shop.
   */
  getMyPoints: async (): Promise<PointsBalance> => {
    return apiClient.get<PointsBalance>('/shops/me/points');
  },

  /**
   * Top up points for the shop's account (preload emulation).
   */
  topUpPoints: async (payload: PointsTopUpRequest): Promise<PointsBalance> => {
    return apiClient.post<PointsBalance>('/shops/me/points/top-up', payload);
  },

  /**
   * Get list of all completed redemptions for the shop.
   */
  getMyRedemptions: async (): Promise<RedemptionResponse[]> => {
    return apiClient.get<RedemptionResponse[]>('/shops/me/redemptions');
  },
};
