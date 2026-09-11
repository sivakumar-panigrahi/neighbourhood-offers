from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_shopkeeper, get_current_shopper, get_current_user
from app.db.database import get_db
from app.models.user import User
from app.schemas.claim import ClaimResponse, OfferPublicResponse
from app.schemas.offer import OfferCreate, OfferResponse, OfferUpdate
from app.services import claim_service, offer_service, shop_service

router = APIRouter(prefix="/offers", tags=["Offers"])


@router.get(
    "",
    response_model=List[OfferPublicResponse],
    summary="Browse all currently active and claimable offers",
)
def browse_active_offers(
    city: Optional[str] = Query(None, description="Filter offers by shop city"),
    shop_id: Optional[int] = Query(None, description="Filter offers by shop ID"),
    search: Optional[str] = Query(None, description="Search offers by title or description"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[OfferPublicResponse]:
    """
    Browse currently active, claimable offers.
    Never returns draft, paused, expired, or future-start offers.
    """
    offers = offer_service.get_public_claimable_offers(
        db,
        city=city,
        shop_id=shop_id,
        search=search,
    )
    return [OfferPublicResponse.model_validate(o) for o in offers]


@router.post(
    "",
    response_model=OfferResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new offer in draft status for current shopkeeper's shop",
)
def create_offer(
    offer_in: OfferCreate,
    current_user: User = Depends(get_current_shopkeeper),
    db: Session = Depends(get_db),
) -> OfferResponse:
    """Create a new draft offer associated with the authenticated shopkeeper's shop."""
    shop = shop_service.get_shop_by_owner(db, owner_id=current_user.id)
    if not shop:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You must create a shop first before creating offers.",
        )

    offer = offer_service.create_offer(db, offer_in, shop_id=shop.id)
    return OfferResponse.model_validate(offer)


@router.get(
    "/my",
    response_model=List[OfferResponse],
    summary="List all offers belonging to current shopkeeper's shop",
)
def list_my_offers(
    status: Optional[str] = Query(None, description="Filter offers by lifecycle status"),
    current_user: User = Depends(get_current_shopkeeper),
    db: Session = Depends(get_db),
) -> List[OfferResponse]:
    """Retrieve all offers belonging to the authenticated shopkeeper."""
    shop = shop_service.get_shop_by_owner(db, owner_id=current_user.id)
    if not shop:
        return []

    offers = offer_service.get_shopkeeper_offers(db, shop_id=shop.id, status_filter=status)
    return [OfferResponse.model_validate(o) for o in offers]


@router.get(
    "/{offer_id}",
    response_model=OfferResponse,
    summary="Get single offer details by ID",
)
def get_offer_detail(
    offer_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OfferResponse:
    """
    Retrieve a single offer by ID.
    - For shopkeepers: enforces ownership check (owner only).
    - For shoppers/counter: requires offer to be currently active and claimable.
    """
    offer = offer_service.get_offer(db, offer_id=offer_id)
    if not offer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Offer not found.",
        )

    if current_user.role == "shopkeeper":
        if offer.shop.owner_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to view this offer.",
            )
    elif current_user.role in ("shopper", "counter"):
        if not offer_service.is_offer_active_and_claimable(offer):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Offer not found or not currently available.",
            )

    return OfferResponse.model_validate(offer)


@router.post(
    "/{offer_id}/claim",
    response_model=ClaimResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Claim an active offer (Shoppers only)",
)
def claim_offer_endpoint(
    offer_id: int,
    current_user: User = Depends(get_current_shopper),
    db: Session = Depends(get_db),
) -> ClaimResponse:
    """
    Claim an active offer and generate a unique claim code.
    Requires shopper role and active claimable offer.
    """
    offer = offer_service.get_offer(db, offer_id=offer_id)
    if not offer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Offer not found.",
        )

    claim = claim_service.create_claim(db, offer=offer, shopper=current_user)
    return ClaimResponse.model_validate(claim)



@router.put(
    "/{offer_id}",
    response_model=OfferResponse,
    summary="Update offer fields (owner only)",
)
@router.patch(
    "/{offer_id}",
    response_model=OfferResponse,
    summary="Partially update offer fields (owner only)",
)
def update_offer_detail(
    offer_id: int,
    offer_in: OfferUpdate,
    current_user: User = Depends(get_current_shopkeeper),
    db: Session = Depends(get_db),
) -> OfferResponse:
    """Update editable attributes of an offer belonging to current shopkeeper."""
    offer = offer_service.get_offer(db, offer_id=offer_id)
    if not offer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Offer not found.",
        )

    updated_offer = offer_service.update_offer(db, offer, offer_in, current_user=current_user)
    return OfferResponse.model_validate(updated_offer)


@router.post(
    "/{offer_id}/activate",
    response_model=OfferResponse,
    summary="Activate a draft or paused offer",
)
def activate_offer_endpoint(
    offer_id: int,
    current_user: User = Depends(get_current_shopkeeper),
    db: Session = Depends(get_db),
) -> OfferResponse:
    """Transition an offer to active status."""
    offer = offer_service.get_offer(db, offer_id=offer_id)
    if not offer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Offer not found.",
        )

    activated_offer = offer_service.activate_offer(db, offer, current_user=current_user)
    return OfferResponse.model_validate(activated_offer)


@router.post(
    "/{offer_id}/pause",
    response_model=OfferResponse,
    summary="Pause an active offer",
)
def pause_offer_endpoint(
    offer_id: int,
    current_user: User = Depends(get_current_shopkeeper),
    db: Session = Depends(get_db),
) -> OfferResponse:
    """Transition an active offer to paused status."""
    offer = offer_service.get_offer(db, offer_id=offer_id)
    if not offer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Offer not found.",
        )

    paused_offer = offer_service.pause_offer(db, offer, current_user=current_user)
    return OfferResponse.model_validate(paused_offer)


@router.post(
    "/{offer_id}/resume",
    response_model=OfferResponse,
    summary="Resume a paused offer",
)
def resume_offer_endpoint(
    offer_id: int,
    current_user: User = Depends(get_current_shopkeeper),
    db: Session = Depends(get_db),
) -> OfferResponse:
    """Transition a paused offer back to active status."""
    offer = offer_service.get_offer(db, offer_id=offer_id)
    if not offer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Offer not found.",
        )

    resumed_offer = offer_service.resume_offer(db, offer, current_user=current_user)
    return OfferResponse.model_validate(resumed_offer)
