from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_shopkeeper
from app.db.database import get_db
from app.models.user import User
from app.schemas.redemption import PointsBalanceResponse, PointsTopUpRequest, RedemptionResponse
from app.schemas.shop import ShopCreate, ShopResponse
from app.services import points_service, redemption_service, shop_service

router = APIRouter(prefix="/shops", tags=["Shops"])


@router.post(
    "",
    response_model=ShopResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new shop for the authenticated shopkeeper",
)
def create_shop(
    shop_in: ShopCreate,
    current_user: User = Depends(get_current_shopkeeper),
    db: Session = Depends(get_db),
) -> ShopResponse:
    """Create a shop owned by the current authenticated shopkeeper."""
    shop = shop_service.create_shop(db, shop_in, owner_id=current_user.id)
    return ShopResponse.model_validate(shop)


@router.get(
    "/me",
    response_model=ShopResponse,
    summary="Get authenticated shopkeeper's shop",
)
def get_my_shop(
    current_user: User = Depends(get_current_shopkeeper),
    db: Session = Depends(get_db),
) -> ShopResponse:
    """Retrieve the shop belonging to the current shopkeeper."""
    shop = shop_service.get_shop_by_owner(db, owner_id=current_user.id)
    if not shop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shopkeeper has not created a shop yet.",
        )
    return ShopResponse.model_validate(shop)


@router.get(
    "/me/points",
    response_model=PointsBalanceResponse,
    summary="Get current shopkeeper's points account balance",
)
def get_my_points_balance(
    current_user: User = Depends(get_current_shopkeeper),
    db: Session = Depends(get_db),
) -> PointsBalanceResponse:
    """Get the current points balance for the shopkeeper's shop."""
    shop = shop_service.get_shop_by_owner(db, owner_id=current_user.id)
    if not shop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shopkeeper has not created a shop yet.",
        )

    account = points_service.get_points_account(db, shop_id=shop.id)
    balance = float(account.balance) if account else 0.0
    return PointsBalanceResponse(shop_id=shop.id, balance=balance)


@router.post(
    "/me/points/top-up",
    response_model=PointsBalanceResponse,
    summary="Top up points for shopkeeper's shop",
)
def top_up_my_points(
    payload: PointsTopUpRequest,
    current_user: User = Depends(get_current_shopkeeper),
    db: Session = Depends(get_db),
) -> PointsBalanceResponse:
    """Top up points balance for shopkeeper's store."""
    shop = shop_service.get_shop_by_owner(db, owner_id=current_user.id)
    if not shop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shopkeeper has not created a shop yet.",
        )

    account = points_service.top_up_points(db, shop_id=shop.id, amount=payload.amount)
    return PointsBalanceResponse(shop_id=shop.id, balance=float(account.balance))


@router.get(
    "/me/redemptions",
    response_model=List[RedemptionResponse],
    summary="List all redemptions for the authenticated shopkeeper's shop",
)
def list_my_shop_redemptions(
    current_user: User = Depends(get_current_shopkeeper),
    db: Session = Depends(get_db),
) -> List[RedemptionResponse]:
    """Retrieve all redemptions that have occurred at the shopkeeper's shop."""
    shop = shop_service.get_shop_by_owner(db, owner_id=current_user.id)
    if not shop:
        return []

    redemptions = redemption_service.get_shop_redemptions(db, shop_id=shop.id)
    rem_points = float(shop.points_account.balance) if shop.points_account else 0.0

    return [
        RedemptionResponse(
            id=r.id,
            claim_id=r.claim_id,
            claim_code=r.claim.code,
            shop_id=r.shop_id,
            redeemed_by_id=r.redeemed_by_id,
            purchase_amount=float(r.purchase_amount),
            discount_amount=float(r.discount_amount),
            final_amount=float(r.purchase_amount - r.discount_amount),
            points_deducted=float(r.discount_amount),
            remaining_points=rem_points,
            redeemed_at=r.redeemed_at,
            created_at=r.created_at,
        )
        for r in redemptions
    ]

