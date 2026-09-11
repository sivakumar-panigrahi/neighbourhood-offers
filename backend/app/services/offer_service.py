from datetime import datetime, timezone
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.offer import Offer
from app.models.shop import Shop
from app.models.user import User
from app.schemas.offer import OfferCreate, OfferUpdate



def _ensure_utc(dt: datetime) -> datetime:
    """Ensure datetime is timezone-aware in UTC."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _sanitize_text(val: Optional[str]) -> Optional[str]:
    """Sanitize currency and special characters for cross-platform DB encoding safety."""
    if val is None:
        return None
    return val.replace("\u20b9", "Rs. ")


def is_offer_expired(offer: Offer, now: Optional[datetime] = None) -> bool:
    """Check if an offer is expired based on status or expiry timestamp."""
    if offer.status == "expired":
        return True
    current_time = _ensure_utc(now) if now else datetime.now(timezone.utc)
    offer_expires_at = _ensure_utc(offer.expires_at)
    return current_time >= offer_expires_at


def is_offer_active_and_claimable(offer: Offer, now: Optional[datetime] = None) -> bool:
    """
    Check if an offer is currently active and within valid claimable date window.
    
    Rule:
    - status == 'active'
    - starts_at <= current_time < expires_at
    """
    if offer.status != "active":
        return False
    current_time = _ensure_utc(now) if now else datetime.now(timezone.utc)
    offer_starts_at = _ensure_utc(offer.starts_at)
    offer_expires_at = _ensure_utc(offer.expires_at)
    return offer_starts_at <= current_time < offer_expires_at


def refresh_offer_status(
    offer: Offer,
    db: Optional[Session] = None,
    now: Optional[datetime] = None,
) -> Offer:
    """Evaluate and transition active/draft/paused offers to expired if past expires_at."""
    if offer.status in ("active", "draft", "paused") and is_offer_expired(offer, now):
        offer.status = "expired"
        if db:
            db.commit()
            db.refresh(offer)
    return offer


def create_offer(db: Session, offer_in: OfferCreate, shop_id: int) -> Offer:
    """Create a new offer in draft status."""
    starts_at_utc = _ensure_utc(offer_in.starts_at)
    expires_at_utc = _ensure_utc(offer_in.expires_at)

    offer = Offer(
        shop_id=shop_id,
        title=_sanitize_text(offer_in.title) or offer_in.title,
        description=_sanitize_text(offer_in.description),
        discount_type=offer_in.discount_type,
        discount_value=offer_in.discount_value,
        minimum_purchase=offer_in.minimum_purchase,
        starts_at=starts_at_utc,
        expires_at=expires_at_utc,
        status="draft",
    )
    db.add(offer)
    db.commit()
    db.refresh(offer)
    return offer


def get_offer(db: Session, offer_id: int) -> Optional[Offer]:
    """Fetch offer by ID and refresh expiration status if needed."""
    offer = db.query(Offer).filter(Offer.id == offer_id).first()
    if offer:
        refresh_offer_status(offer, db)
    return offer


def get_shopkeeper_offers(
    db: Session,
    shop_id: int,
    status_filter: Optional[str] = None,
) -> List[Offer]:
    """Retrieve all offers belonging to the shopkeeper's shop with optional status filter."""
    query = db.query(Offer).filter(Offer.shop_id == shop_id)
    if status_filter:
        query = query.filter(Offer.status == status_filter)
    offers = query.order_by(Offer.created_at.desc()).all()

    # Refresh statuses for all fetched offers
    for offer in offers:
        refresh_offer_status(offer, db)

    return offers


def get_public_claimable_offers(
    db: Session,
    city: Optional[str] = None,
    shop_id: Optional[int] = None,
    search: Optional[str] = None,
    now: Optional[datetime] = None,
) -> List[Offer]:
    """
    Retrieve all currently active and claimable offers for shoppers.
    Filters out draft, paused, expired, and future-start offers.
    """
    current_time = _ensure_utc(now) if now else datetime.now(timezone.utc)

    query = db.query(Offer).filter(
        Offer.status == "active",
        Offer.starts_at <= current_time,
        Offer.expires_at > current_time,
    )

    if shop_id is not None:
        query = query.filter(Offer.shop_id == shop_id)

    if city is not None and city.strip():
        query = query.join(Offer.shop).filter(Shop.city.ilike(f"%{city.strip()}%"))

    if search is not None and search.strip():
        term = f"%{search.strip()}%"
        query = query.filter((Offer.title.ilike(term)) | (Offer.description.ilike(term)))

    offers = query.order_by(Offer.created_at.desc()).all()

    # Re-verify through claimability helper to guarantee 100% adherence to domain rules
    claimable_offers = [o for o in offers if is_offer_active_and_claimable(o, current_time)]
    return claimable_offers



def update_offer(
    db: Session,
    offer: Offer,
    offer_in: OfferUpdate,
    current_user: User,
) -> Offer:
    """Update editable fields of an offer after verifying shopkeeper ownership."""
    if offer.shop.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to manage this offer.",
        )

    # Prepare updated field values
    new_starts_at = _ensure_utc(offer_in.starts_at) if offer_in.starts_at is not None else offer.starts_at
    new_expires_at = _ensure_utc(offer_in.expires_at) if offer_in.expires_at is not None else offer.expires_at

    if new_expires_at <= new_starts_at:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="expires_at must be later than starts_at",
        )

    new_discount_type = offer_in.discount_type if offer_in.discount_type is not None else offer.discount_type
    new_discount_value = offer_in.discount_value if offer_in.discount_value is not None else offer.discount_value

    if new_discount_type == "percentage" and new_discount_value > 100:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Percentage discount cannot exceed 100%",
        )

    if offer_in.title is not None:
        offer.title = offer_in.title
    if offer_in.description is not None:
        offer.description = offer_in.description
    if offer_in.discount_type is not None:
        offer.discount_type = offer_in.discount_type
    if offer_in.discount_value is not None:
        offer.discount_value = offer_in.discount_value
    if offer_in.minimum_purchase is not None:
        offer.minimum_purchase = offer_in.minimum_purchase
    if offer_in.starts_at is not None:
        offer.starts_at = new_starts_at
    if offer_in.expires_at is not None:
        offer.expires_at = new_expires_at

    db.commit()
    db.refresh(offer)
    return offer


def activate_offer(
    db: Session,
    offer: Offer,
    current_user: User,
) -> Offer:
    """Activate a draft or paused offer after verifying ownership and validity dates."""
    if offer.shop.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to manage this offer.",
        )

    refresh_offer_status(offer, db)

    if is_offer_expired(offer):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Offer has already expired and cannot be activated.",
        )

    if offer.status not in ("draft", "paused", "active"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot activate offer from '{offer.status}' status.",
        )

    offer.status = "active"
    db.commit()
    db.refresh(offer)
    return offer


def pause_offer(
    db: Session,
    offer: Offer,
    current_user: User,
) -> Offer:
    """Pause an active offer."""
    if offer.shop.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to manage this offer.",
        )

    refresh_offer_status(offer, db)

    if is_offer_expired(offer):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Offer has already expired and cannot be paused.",
        )

    if offer.status != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Only active offers can be paused. Current status is '{offer.status}'.",
        )

    offer.status = "paused"
    db.commit()
    db.refresh(offer)
    return offer


def resume_offer(
    db: Session,
    offer: Offer,
    current_user: User,
) -> Offer:
    """Resume a paused offer."""
    if offer.shop.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to manage this offer.",
        )

    refresh_offer_status(offer, db)

    if is_offer_expired(offer):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Offer has already expired and cannot be resumed.",
        )

    if offer.status != "paused":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Only paused offers can be resumed. Current status is '{offer.status}'.",
        )

    offer.status = "active"
    db.commit()
    db.refresh(offer)
    return offer
