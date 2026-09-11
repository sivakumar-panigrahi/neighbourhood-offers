import { apiClient } from './client';
import type { Offer, OfferCreateRequest, OfferParseResponse, OfferUpdateRequest } from '../types';

export const offersApi = {
  /**
   * Browse active claimable offers across shops (for Shoppers).
   */
  getPublicOffers: async (params?: { search?: string; city?: string }): Promise<Offer[]> => {
    return apiClient.get<Offer[]>('/offers', { params });
  },

  /**
   * Get all offers owned by the authenticated shopkeeper.
   */
  getMyOffers: async (): Promise<Offer[]> => {
    return apiClient.get<Offer[]>('/offers/my');
  },

  /**
   * Get single offer details by ID.
   */
  getOffer: async (id: number): Promise<Offer> => {
    return apiClient.get<Offer>(`/offers/${id}`);
  },

  /**
   * Create a new offer in draft status.
   */
  createOffer: async (data: OfferCreateRequest): Promise<Offer> => {
    return apiClient.post<Offer>('/offers', data);
  },

  /**
   * Update existing draft/paused offer.
   */
  updateOffer: async (id: number, data: OfferUpdateRequest): Promise<Offer> => {
    return apiClient.put<Offer>(`/offers/${id}`, data);
  },

  /**
   * Transition offer from draft to active.
   */
  activateOffer: async (id: number): Promise<Offer> => {
    return apiClient.post<Offer>(`/offers/${id}/activate`);
  },

  /**
   * Transition offer from active to paused.
   */
  pauseOffer: async (id: number): Promise<Offer> => {
    return apiClient.post<Offer>(`/offers/${id}/pause`);
  },

  /**
   * Transition offer from paused to active.
   */
  resumeOffer: async (id: number): Promise<Offer> => {
    return apiClient.post<Offer>(`/offers/${id}/resume`);
  },

  /**
   * Natural-language offer parsing with AI / fallback engine.
   */
  parseOfferPrompt: async (text: string): Promise<OfferParseResponse> => {
    return apiClient.post<OfferParseResponse>('/offers/parse', { text });
  },
};
