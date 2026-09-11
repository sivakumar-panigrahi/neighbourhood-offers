import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_shopkeeper
from app.db.database import get_db
from app.models.user import User
from app.schemas.report import MonthlyReportResponse
from app.services import reporting_service, shop_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get(
    "/monthly",
    response_model=MonthlyReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Get monthly spend, remaining points, and busy days report for authenticated shopkeeper",
)
def get_monthly_report(
    month: Optional[str] = Query(
        None,
        description="Month in 'YYYY-MM' format (e.g. '2026-09'). Defaults to current UTC month if omitted.",
    ),
    current_user: User = Depends(get_current_shopkeeper),
    db: Session = Depends(get_db),
) -> MonthlyReportResponse:
    """
    Generate shopkeeper's monthly activity report.

    Returns:
    - total_spend: Total platform spend across all successful redemptions during the month.
    - remaining_points: Current shop points balance.
    - busy_days: Breakdown of days with redemptions, ordered by highest footfall/redemption count.
    """
    shop = shop_service.get_shop_by_owner(db, owner_id=current_user.id)
    if not shop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shopkeeper has not created a shop yet.",
        )

    return reporting_service.generate_monthly_report(
        db,
        shop_id=shop.id,
        shop_name=shop.name,
        month_str=month,
    )
