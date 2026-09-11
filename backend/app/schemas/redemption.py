from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class RedemptionRequest(BaseModel):
    claim_code: str = Field(..., min_length=1, max_length=50, description="Unique claim code to redeem")
    purchase_amount: float = Field(..., gt=0, description="Total purchase amount before discount")


class RedemptionResponse(BaseModel):
    id: int
    claim_id: int
    claim_code: str
    shop_id: int
    redeemed_by_id: int
    purchase_amount: float
    discount_amount: float
    final_amount: float
    points_deducted: float
    remaining_points: float
    redeemed_at: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PointsBalanceResponse(BaseModel):
    shop_id: int
    balance: float

    model_config = ConfigDict(from_attributes=True)


class PointsTopUpRequest(BaseModel):
    amount: float = Field(..., gt=0, description="Points amount to top up")


class PointsTransactionResponse(BaseModel):
    id: int
    account_id: int
    transaction_type: str
    amount: float
    balance_after: float
    description: Optional[str] = None
    redemption_id: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
