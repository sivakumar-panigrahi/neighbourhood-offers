from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class OfferCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255, description="Offer title")
    description: Optional[str] = Field(None, max_length=2000, description="Offer details")
    discount_type: Literal["percentage", "fixed"] = Field(
        ...,
        description="Discount type: percentage or fixed",
    )
    discount_value: float = Field(..., gt=0, description="Discount amount or percentage")
    minimum_purchase: Optional[float] = Field(
        None,
        ge=0,
        description="Minimum purchase amount required (optional)",
    )
    starts_at: datetime = Field(..., description="Offer validity start timestamp")
    expires_at: datetime = Field(..., description="Offer validity expiry timestamp")

    @model_validator(mode="after")
    def validate_offer_rules(self) -> "OfferCreate":
        # Percentage discount rule (0 < percentage <= 100)
        if self.discount_type == "percentage" and self.discount_value > 100:
            raise ValueError("Percentage discount cannot exceed 100%")

        # Expiry rule
        if self.expires_at <= self.starts_at:
            raise ValueError("expires_at must be later than starts_at")

        return self


class OfferUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    discount_type: Optional[Literal["percentage", "fixed"]] = None
    discount_value: Optional[float] = Field(None, gt=0)
    minimum_purchase: Optional[float] = Field(None, ge=0)
    starts_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None

    @model_validator(mode="after")
    def validate_update_rules(self) -> "OfferUpdate":
        if self.discount_type == "percentage" and self.discount_value is not None:
            if self.discount_value > 100:
                raise ValueError("Percentage discount cannot exceed 100%")

        if self.starts_at is not None and self.expires_at is not None:
            if self.expires_at <= self.starts_at:
                raise ValueError("expires_at must be later than starts_at")

        return self


class OfferResponse(BaseModel):
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
    original_text: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
