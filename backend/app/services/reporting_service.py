from datetime import datetime, timezone
from decimal import Decimal
import logging
import re
from typing import Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.redemption import Redemption
from app.schemas.report import BusyDayReport, MonthlyReportResponse
from app.services import points_service

logger = logging.getLogger(__name__)


def parse_and_validate_month(
    month_str: Optional[str],
) -> Tuple[int, int, str, datetime, datetime]:
    """
    Parse and validate a 'YYYY-MM' formatted string into UTC month boundaries.
    Defaults to current UTC month if month_str is omitted.
    Returns: (year, month, formatted_month, start_date_utc, next_month_start_utc)
    """
    if month_str is None or not month_str.strip():
        now = datetime.now(timezone.utc)
        year, month = now.year, now.month
    else:
        clean_month = month_str.strip()
        if not re.match(r"^\d{4}-(?:0[1-9]|1[0-2])$", clean_month):
            raise HTTPException(
                status_code=422,
                detail="Invalid month format. Expected 'YYYY-MM' with 2-digit month 01-12 (e.g. 2026-09).",
            )
        try:
            parts = clean_month.split("-")
            year = int(parts[0])
            month = int(parts[1])
            if year < 1000 or year > 9999 or month < 1 or month > 12:
                raise ValueError()
        except ValueError:
            raise HTTPException(
                status_code=422,
                detail="Invalid year or month value.",
            )

    start_date = datetime(year, month, 1, 0, 0, 0, tzinfo=timezone.utc)
    if month == 12:
        next_start_date = datetime(year + 1, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    else:
        next_start_date = datetime(year, month + 1, 1, 0, 0, 0, tzinfo=timezone.utc)

    formatted_month = f"{year:04d}-{month:02d}"
    return year, month, formatted_month, start_date, next_start_date


def generate_monthly_report(
    db: Session,
    shop_id: int,
    shop_name: str,
    month_str: Optional[str] = None,
) -> MonthlyReportResponse:
    """
    Generate the shopkeeper's monthly spend and busy-days report.

    Calculates:
    - total_spend: total platform discount spend during the month [start, next_start).
    - remaining_points: shop's current available PointsAccount balance.
    - busy_days: list of active redemption dates, ordered by:
        1. redemptions count DESC
        2. spend DESC
        3. date DESC
    """
    year, month, formatted_month, start_date, next_start_date = parse_and_validate_month(month_str)

    # 1. Current remaining points balance
    points_acct = points_service.get_points_account(db, shop_id=shop_id)
    remaining_points = float(points_acct.balance) if points_acct else 0.0

    # 2. Total monthly spend (sum of discount_amount for successful redemptions)
    total_spend_query = (
        db.query(func.coalesce(func.sum(Redemption.discount_amount), 0.0))
        .filter(
            Redemption.shop_id == shop_id,
            Redemption.redeemed_at >= start_date,
            Redemption.redeemed_at < next_start_date,
        )
        .scalar()
    )
    total_spend = float(Decimal(str(total_spend_query or 0)).quantize(Decimal("0.01")))

    # 3. Group successful redemptions by calendar date
    busy_days_rows = (
        db.query(
            func.date(Redemption.redeemed_at).label("day_date"),
            func.count(Redemption.id).label("redemptions_count"),
            func.sum(Redemption.discount_amount).label("day_spend"),
        )
        .filter(
            Redemption.shop_id == shop_id,
            Redemption.redeemed_at >= start_date,
            Redemption.redeemed_at < next_start_date,
        )
        .group_by(func.date(Redemption.redeemed_at))
        .order_by(
            func.count(Redemption.id).desc(),
            func.sum(Redemption.discount_amount).desc(),
            func.date(Redemption.redeemed_at).desc(),
        )
        .all()
    )

    busy_days = []
    for row in busy_days_rows:
        day_str = str(row.day_date)
        day_spend = float(Decimal(str(row.day_spend or 0)).quantize(Decimal("0.01")))
        busy_days.append(
            BusyDayReport(
                date=day_str,
                redemptions=int(row.redemptions_count),
                spend=day_spend,
            )
        )

    return MonthlyReportResponse(
        shop_id=shop_id,
        shop_name=shop_name,
        month=formatted_month,
        total_spend=total_spend,
        remaining_points=remaining_points,
        busy_days=busy_days,
    )
