from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ShopCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Shop name")
    address: str = Field(..., min_length=1, max_length=500, description="Shop street address")
    city: str = Field(..., min_length=1, max_length=100, description="City")
    latitude: Optional[float] = Field(None, description="Latitude coordinate")
    longitude: Optional[float] = Field(None, description="Longitude coordinate")


class ShopResponse(BaseModel):
    id: int
    name: str
    address: str
    city: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    owner_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
