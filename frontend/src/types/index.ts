/**
 * TypeScript definitions for Neighbourhood Offers API contracts and frontend state.
 */

export type UserRole = 'shopkeeper' | 'shopper' | 'counter';

export interface User {
  id: number;
  email: string;
  role: UserRole;
  created_at: string;
}

export interface AuthToken {
  access_token: string;
  token_type: string;
}

export interface Shop {
  id: number;
  name: string;
  address: string;
  city: string;
  latitude: number | null;
  longitude: number | null;
  owner_id: number;
  created_at: string;
  updated_at: string;
}

export type OfferStatus = 'draft' | 'active' | 'paused' | 'expired';
export type DiscountType = 'percentage' | 'fixed';

export interface Offer {
  id: number;
  shop_id: number;
  title: string;
  description: string | null;
  discount_type: DiscountType;
  discount_value: number;
  minimum_purchase: number | null;
  starts_at: string;
  expires_at: string;
  status: OfferStatus;
  original_text?: string | null;
  is_claimable?: boolean;
  shop_name?: string;
  created_at: string;
  updated_at: string;
}

export interface OfferCreateRequest {
  title: string;
  description?: string | null;
  discount_type: DiscountType;
  discount_value: number;
  minimum_purchase?: number | null;
  starts_at: string;
  expires_at: string;
  status?: OfferStatus;
  original_text?: string | null;
}

export interface OfferUpdateRequest {
  title?: string;
  description?: string | null;
  discount_type?: DiscountType;
  discount_value?: number;
  minimum_purchase?: number | null;
  starts_at?: string;
  expires_at?: string;
  status?: OfferStatus;
}

export type ClaimStatus = 'claimed' | 'redeemed' | 'expired' | 'cancelled';

export interface Claim {
  id: number;
  offer_id: number;
  shopper_id: number;
  code: string;
  status: ClaimStatus;
  claimed_at: string;
  expires_at: string;
  offer?: Offer;
  shop?: Shop;
}

export interface Redemption {
  id: number;
  claim_id: number;
  shop_id: number;
  redeemed_by_id: number;
  purchase_amount: number;
  discount_amount: number;
  redeemed_at: string;
  created_at: string;
  claim?: Claim;
  shop?: Shop;
}

export interface RedemptionRequest {
  claim_code: string;
  purchase_amount: number;
}

export interface RedemptionResponse {
  id: number;
  claim_id: number;
  claim_code: string;
  shop_id: number;
  purchase_amount: number;
  discount_amount: number;
  final_amount: number;
  points_deducted: number;
  remaining_points: number;
  redeemed_at: string;
}

export interface PointsBalance {
  shop_id: number;
  balance: number;
  updated_at: string;
}

export interface PointsTopUpRequest {
  amount: number;
  description?: string;
}

export type PointsTransactionType = 'top_up' | 'redemption' | 'adjustment';

export interface PointsTransaction {
  id: number;
  account_id: number;
  transaction_type: PointsTransactionType;
  amount: number;
  balance_after: number;
  description: string | null;
  redemption_id: number | null;
  created_at: string;
}

export interface BusyDayReport {
  date: string;
  redemptions: number;
  spend: number;
}

export interface MonthlyReport {
  shop_id: number;
  shop_name: string;
  month: string;
  total_spend: number;
  remaining_points: number;
  busy_days: BusyDayReport[];
}

export interface OfferParsedData {
  title?: string | null;
  description?: string | null;
  discount_type?: DiscountType | null;
  discount_value?: number | null;
  minimum_purchase?: number | null;
  starts_at?: string | null;
  expires_at?: string | null;
  conditions?: string | null;
}

export interface OfferParseResponse {
  original_text: string;
  parsed?: OfferParsedData | null;
  confidence?: number | null;
  needs_confirmation: boolean;
  warnings: string[];
  parser_type: 'ai' | 'fallback';
}

export interface APIError {
  status: number;
  message: string;
  detail?: string | Array<{ loc: (string | number)[]; msg: string; type: string }>;
}
