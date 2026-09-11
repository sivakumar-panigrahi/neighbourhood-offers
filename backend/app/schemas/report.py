from typing import List
from pydantic import BaseModel, ConfigDict, Field


class BusyDayReport(BaseModel):
    date: str = Field(..., description="Date in YYYY-MM-DD format")
    redemptions: int = Field(..., ge=0, description="Total number of successful redemptions on this date")
    spend: float = Field(..., ge=0.0, description="Total platform spend (discount) in Rs on this date")

    model_config = ConfigDict(from_attributes=True)


class MonthlyReportResponse(BaseModel):
    shop_id: int = Field(..., description="ID of the shop")
    shop_name: str = Field(..., description="Name of the shop")
    month: str = Field(..., description="Reporting month in YYYY-MM format")
    total_spend: float = Field(..., ge=0.0, description="Total platform discount spend during the month")
    remaining_points: float = Field(..., ge=0.0, description="Current available points balance for the shop")
    busy_days: List[BusyDayReport] = Field(
        default_factory=list,
        description="List of active redemption days ordered by activity",
    )

    model_config = ConfigDict(from_attributes=True)
