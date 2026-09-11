from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class ClaimOfferSummary(BaseModel):
    id: int
    shop_id: int
    title: str
    description: Optional[str] = None
    discount_type: str
    discount_value: float
    minimum_purchase: Optional[float] = None
    starts_at: datetime
    expires_at: datetime
    status: str
    shop_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ClaimResponse(BaseModel):
    id: int
    offer_id: int
    shopper_id: int
    code: str = Field(..., description="Unique claim code (e.g. NO-7K4P9X)")
    status: str = Field(..., description="Claim status: claimed, redeemed, expired, cancelled")
    claimed_at: datetime
    expires_at: datetime
    redeemed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    offer: Optional[ClaimOfferSummary] = None

    model_config = ConfigDict(from_attributes=True)


class OfferPublicResponse(BaseModel):
    id: int
    shop_id: int
    title: str
    description: Optional[str] = None
    discount_type: str
    discount_value: float
    minimum_purchase: Optional[float] = None
    starts_at: datetime
    expires_at: datetime
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
