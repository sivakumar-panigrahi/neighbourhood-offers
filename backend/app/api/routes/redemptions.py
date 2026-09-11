import logging
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_counter, get_current_user
from app.db.database import get_db
from app.models.user import User
from app.schemas.redemption import RedemptionRequest, RedemptionResponse
from app.services import redemption_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/redemptions", tags=["Redemptions"])


@router.post(
    "",
    response_model=RedemptionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Redeem a shopper claim code at counter",
)
def redeem_claim_endpoint(
    payload: RedemptionRequest,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    current_user: User = Depends(get_current_counter),
    db: Session = Depends(get_db),
) -> RedemptionResponse:
    """
    Redeem a customer claim code at checkout.
    - Restricted strictly to Counter Staff role.
    - Deducts platform points atomically from the shop's PointsAccount.
    - Supports idempotent replays via Idempotency-Key HTTP header.
    """
    return redemption_service.redeem_claim(
        db,
        claim_code=payload.claim_code,
        purchase_amount=payload.purchase_amount,
        counter_user=current_user,
        idempotency_key=idempotency_key,
    )


@router.get(
    "/{redemption_id}",
    response_model=RedemptionResponse,
    summary="Get redemption details by redemption ID",
)
def get_redemption_endpoint(
    redemption_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RedemptionResponse:
    """Retrieve redemption record by ID (counter staff or owning shopkeeper)."""
    redemption = redemption_service.get_redemption(db, redemption_id=redemption_id)
    if not redemption:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Redemption not found.",
        )

    # Permission check: Counter staff or owning shopkeeper
    if current_user.role == "shopkeeper":
        if redemption.shop.owner_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to view this redemption.",
            )
    elif current_user.role != "counter":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view redemptions.",
        )

    # Compute remaining points for response
    rem_points = float(redemption.shop.points_account.balance) if redemption.shop.points_account else 0.0

    return RedemptionResponse(
        id=redemption.id,
        claim_id=redemption.claim_id,
        claim_code=redemption.claim.code,
        shop_id=redemption.shop_id,
        redeemed_by_id=redemption.redeemed_by_id,
        purchase_amount=float(redemption.purchase_amount),
        discount_amount=float(redemption.discount_amount),
        final_amount=float(redemption.purchase_amount - redemption.discount_amount),
        points_deducted=float(redemption.discount_amount),
        remaining_points=rem_points,
        redeemed_at=redemption.redeemed_at,
        created_at=redemption.created_at,
    )


@router.get(
    "/code/{claim_code}",
    response_model=RedemptionResponse,
    summary="Get redemption details by claim code (counter staff only)",
)
def get_redemption_by_code_endpoint(
    claim_code: str,
    current_user: User = Depends(get_current_counter),
    db: Session = Depends(get_db),
) -> RedemptionResponse:
    """Retrieve redemption record by claim code."""
    redemption = redemption_service.get_redemption_by_claim_code(db, claim_code=claim_code)
    if not redemption:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Redemption not found for the provided claim code.",
        )

    rem_points = float(redemption.shop.points_account.balance) if redemption.shop.points_account else 0.0

    return RedemptionResponse(
        id=redemption.id,
        claim_id=redemption.claim_id,
        claim_code=redemption.claim.code,
        shop_id=redemption.shop_id,
        redeemed_by_id=redemption.redeemed_by_id,
        purchase_amount=float(redemption.purchase_amount),
        discount_amount=float(redemption.discount_amount),
        final_amount=float(redemption.purchase_amount - redemption.discount_amount),
        points_deducted=float(redemption.discount_amount),
        remaining_points=rem_points,
        redeemed_at=redemption.redeemed_at,
        created_at=redemption.created_at,
    )
