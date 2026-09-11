from datetime import datetime, timezone
import logging
import secrets
import string
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.claim import Claim
from app.models.offer import Offer
from app.models.user import User
from app.services.offer_service import is_offer_active_and_claimable, is_offer_expired, refresh_offer_status

logger = logging.getLogger(__name__)

# Character set for user-friendly codes (excludes confusing chars 0, O, 1, I)
CODE_ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"


def _ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def generate_claim_code(db: Session, length: int = 6) -> str:
    """
    Generate a cryptographically random, unambiguous claim code in format 'NO-XXXXXX'.
    Guarantees database uniqueness by checking existing Claim records.
    """
    for _ in range(10):
        random_suffix = "".join(secrets.choice(CODE_ALPHABET) for _ in range(length))
        code = f"NO-{random_suffix}"
        # Check uniqueness in DB
        existing = db.query(Claim).filter(Claim.code == code).first()
        if not existing:
            return code

    # Fallback to longer suffix if collisions occur
    random_suffix = "".join(secrets.choice(CODE_ALPHABET) for _ in range(length + 2))
    return f"NO-{random_suffix}"


def is_claim_expired(claim: Claim, now: Optional[datetime] = None) -> bool:
    """Determine if a claim has expired based on current UTC time."""
    if claim.status == "expired":
        return True
    current_time = _ensure_utc(now) if now else datetime.now(timezone.utc)
    claim_expires_at = _ensure_utc(claim.expires_at)
    return current_time >= claim_expires_at


def refresh_claim_status(
    claim: Claim,
    db: Optional[Session] = None,
    now: Optional[datetime] = None,
) -> Claim:
    """Transition claim status to 'expired' if expiration time has passed."""
    if claim.status == "claimed" and is_claim_expired(claim, now):
        claim.status = "expired"
        if db:
            db.commit()
            db.refresh(claim)
    return claim


def create_claim(
    db: Session,
    offer: Offer,
    shopper: User,
    now: Optional[datetime] = None,
) -> Claim:
    """
    Create a new Claim for the authenticated shopper.

    Enforces:
    1. Shopper role check.
    2. Offer active & claimable validation.
    3. Duplicate claim policy (prevent multiple active claims or claiming already redeemed offers).
    4. Unique cryptographic claim code generation.
    5. Expiration bounded to offer expiration.
    """
    current_time = _ensure_utc(now) if now else datetime.now(timezone.utc)

    # 1. Role verification
    if shopper.role != "shopper":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only shoppers can claim offers.",
        )

    # 2. Offer validation & expiration refresh
    refresh_offer_status(offer, db, current_time)

    if is_offer_expired(offer, current_time):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Offer has expired and cannot be claimed.",
        )

    if offer.status == "draft":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Offer is in draft and is not currently available.",
        )

    if offer.status == "paused":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Offer is currently paused and not available.",
        )

    if not is_offer_active_and_claimable(offer, current_time):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Offer is not currently available for claiming.",
        )

    # 3. Duplicate claim prevention
    existing_claims = (
        db.query(Claim)
        .filter(Claim.shopper_id == shopper.id, Claim.offer_id == offer.id)
        .all()
    )

    for prev_claim in existing_claims:
        refresh_claim_status(prev_claim, db, current_time)
        if prev_claim.status == "claimed":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="You have already claimed this offer.",
            )
        if prev_claim.status == "redeemed":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="You have already redeemed this offer.",
            )

    # 4. Generate unique claim code
    code = generate_claim_code(db)

    # 5. Create claim record (expiration matches offer expiration)
    claim = Claim(
        offer_id=offer.id,
        shopper_id=shopper.id,
        code=code,
        status="claimed",
        claimed_at=current_time,
        expires_at=offer.expires_at,
    )

    db.add(claim)
    db.commit()
    db.refresh(claim)

    logger.info(f"Offer {offer.id} successfully claimed by shopper {shopper.id} with claim code {code}")
    return claim


def get_shopper_claims(
    db: Session,
    shopper_id: int,
    status_filter: Optional[str] = None,
    now: Optional[datetime] = None,
) -> List[Claim]:
    """Retrieve all claims belonging to the authenticated shopper with optional status filter."""
    query = db.query(Claim).filter(Claim.shopper_id == shopper_id)
    if status_filter:
        query = query.filter(Claim.status == status_filter)

    claims = query.order_by(Claim.claimed_at.desc()).all()

    # Refresh statuses for any claims that may have expired
    for claim in claims:
        refresh_claim_status(claim, db, now)

    return claims


def get_claim(
    db: Session,
    claim_id: int,
    now: Optional[datetime] = None,
) -> Optional[Claim]:
    """Retrieve single claim by ID with expiration evaluation."""
    claim = db.query(Claim).filter(Claim.id == claim_id).first()
    if claim:
        refresh_claim_status(claim, db, now)
    return claim


def get_claim_by_code(
    db: Session,
    code: str,
    now: Optional[datetime] = None,
) -> Optional[Claim]:
    """Retrieve claim by unique claim code (foundation for Phase 08 redemption)."""
    clean_code = code.strip().upper()
    claim = db.query(Claim).filter(Claim.code == clean_code).first()
    if claim:
        refresh_claim_status(claim, db, now)
    return claim
