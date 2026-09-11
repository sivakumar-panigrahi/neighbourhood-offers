from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
import json
import logging
from typing import List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.claim import Claim
from app.models.idempotency import IdempotencyRecord
from app.models.offer import Offer
from app.models.points import PointsAccount
from app.models.points_transaction import PointsTransaction
from app.models.redemption import Redemption
from app.models.user import User
from app.schemas.redemption import RedemptionResponse
from app.services.claim_service import is_claim_expired
from app.services.offer_service import is_offer_active_and_claimable, refresh_offer_status

logger = logging.getLogger(__name__)


def calculate_discount(
    purchase_amount: Decimal,
    discount_type: str,
    discount_value: Decimal,
) -> Tuple[Decimal, Decimal]:
    """
    Calculate precise discount and final payable amounts using Decimal arithmetic.
    Discount is strictly capped at purchase_amount so final_amount is never negative.
    """
    if discount_type == "percentage":
        discount = (purchase_amount * discount_value / Decimal("100")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
    elif discount_type == "fixed":
        discount = discount_value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    else:
        discount = Decimal("0.00")

    # Discount cannot exceed the purchase amount
    discount_amount = min(max(Decimal("0.00"), discount), purchase_amount)
    final_amount = max(Decimal("0.00"), (purchase_amount - discount_amount).quantize(Decimal("0.01")))

    return discount_amount, final_amount


def redeem_claim(
    db: Session,
    claim_code: str,
    purchase_amount: float,
    counter_user: User,
    idempotency_key: Optional[str] = None,
) -> RedemptionResponse:
    """
    Execute atomic redemption of a shopper claim by counter staff.

    Enforces:
    1. Counter staff role check.
    2. Idempotency replay / collision prevention.
    3. Claim validity & expiration check with row-level locking.
    4. Offer validity & minimum purchase verification.
    5. Exact Decimal discount calculation (capped at purchase amount).
    6. Shop PointsAccount balance verification with row-level locking.
    7. Atomic commit of Redemption, Claim update, Points deduction, PointsTransaction, and IdempotencyRecord.
    """
    # 1. Role verification
    if counter_user.role != "counter":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only counter staff can redeem claims.",
        )

    if purchase_amount <= 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Purchase amount must be greater than zero.",
        )

    clean_code = claim_code.strip().upper()
    now = datetime.now(timezone.utc)
    dec_purchase = Decimal(str(purchase_amount)).quantize(Decimal("0.01"))

    # 2. Idempotency Key Handling
    if idempotency_key:
        clean_key = idempotency_key.strip()
        existing_record = (
            db.query(IdempotencyRecord)
            .filter(IdempotencyRecord.key == clean_key)
            .first()
        )
        if existing_record:
            if existing_record.user_id != counter_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Idempotency key belongs to another user.",
                )
            try:
                cached_data = json.loads(existing_record.response_body or "{}")
                cached_code = cached_data.get("claim_code")
                cached_amount = cached_data.get("purchase_amount")

                # Verify exact payload match
                if cached_code != clean_code or abs(float(cached_amount or 0) - float(dec_purchase)) > 0.001:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Idempotency key was already used for a different request.",
                    )

                logger.info(f"Returning cached idempotent response for key {clean_key}")
                return RedemptionResponse.model_validate(cached_data["response"])
            except (json.JSONDecodeError, KeyError):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Idempotency key conflict.",
                )

    try:
        # 3. Lock and retrieve Claim row
        claim = (
            db.query(Claim)
            .filter(Claim.code == clean_code)
            .with_for_update()
            .first()
        )
        if not claim:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Claim not found.",
            )

        # Check claim expiration
        if is_claim_expired(claim, now):
            claim.status = "expired"
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Claim has expired.",
            )

        if claim.status == "redeemed":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Claim has already been redeemed.",
            )

        if claim.status != "claimed":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Claim is not in a redeemable status: {claim.status}.",
            )

        # 4. Lock and validate Offer
        offer = db.query(Offer).filter(Offer.id == claim.offer_id).first()
        if not offer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Associated offer not found.",
            )

        refresh_offer_status(offer, db, now)
        if not is_offer_active_and_claimable(offer, now):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Associated offer is not currently active and claimable.",
            )

        # 5. Check Minimum Purchase
        if offer.minimum_purchase is not None:
            min_purchase_dec = Decimal(str(offer.minimum_purchase))
            if dec_purchase < min_purchase_dec:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Purchase amount ₹{dec_purchase} is less than minimum required ₹{min_purchase_dec}.",
                )

        # 6. Calculate Discount & Points Cost (1 Point = ₹1 Platform Spend)
        dec_disc_val = Decimal(str(offer.discount_value))
        discount_amount, final_amount = calculate_discount(
            dec_purchase, offer.discount_type, dec_disc_val
        )
        points_cost = discount_amount

        # 7. Lock and validate PointsAccount
        points_account = (
            db.query(PointsAccount)
            .filter(PointsAccount.shop_id == offer.shop_id)
            .with_for_update()
            .first()
        )
        if not points_account:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Shop does not have a points account configured.",
            )

        dec_balance = Decimal(str(points_account.balance))
        if dec_balance < points_cost:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Insufficient points balance. Required: {points_cost}, Available: {dec_balance}.",
            )

        # 8. Execute Atomic Transitions
        new_balance = float((dec_balance - points_cost).quantize(Decimal("0.01")))
        points_account.balance = new_balance

        redemption = Redemption(
            claim_id=claim.id,
            shop_id=offer.shop_id,
            redeemed_by_id=counter_user.id,
            purchase_amount=float(dec_purchase),
            discount_amount=float(discount_amount),
            redeemed_at=now,
        )
        db.add(redemption)
        db.flush()

        claim.status = "redeemed"
        claim.redeemed_at = now

        txn = PointsTransaction(
            account_id=points_account.id,
            transaction_type="redemption",
            amount=-float(points_cost),
            balance_after=new_balance,
            description=f"Redemption for claim {claim.code}",
            redemption_id=redemption.id,
        )
        db.add(txn)

        response_obj = RedemptionResponse(
            id=redemption.id,
            claim_id=claim.id,
            claim_code=claim.code,
            shop_id=offer.shop_id,
            redeemed_by_id=counter_user.id,
            purchase_amount=float(dec_purchase),
            discount_amount=float(discount_amount),
            final_amount=float(final_amount),
            points_deducted=float(points_cost),
            remaining_points=new_balance,
            redeemed_at=now,
            created_at=redemption.created_at,
        )

        # 9. Store Idempotency Record if key provided
        if idempotency_key:
            stored_payload = {
                "claim_code": clean_code,
                "purchase_amount": float(dec_purchase),
                "response": response_obj.model_dump(mode="json"),
            }
            idemp_rec = IdempotencyRecord(
                key=idempotency_key.strip(),
                user_id=counter_user.id,
                endpoint="/redemptions",
                response_status=201,
                response_body=json.dumps(stored_payload),
            )
            db.add(idemp_rec)

        db.commit()
        db.refresh(redemption)

        logger.info(
            f"Redemption {redemption.id} successful for claim {claim.code}."
            f" Discount: ₹{discount_amount}, Remaining Points: {new_balance}"
        )
        return response_obj

    except IntegrityError as e:
        db.rollback()
        logger.warning(f"IntegrityError during redemption: {e}")
        # Check if already redeemed or duplicate key
        if "unique" in str(e).lower() or "claims.code" in str(e).lower() or "claim_id" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Claim has already been redeemed.",
            )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Transaction conflict during redemption. Please retry.",
        )
    except Exception:
        db.rollback()
        raise


def get_redemption(db: Session, redemption_id: int) -> Optional[Redemption]:
    """Retrieve single redemption record by ID."""
    return db.query(Redemption).filter(Redemption.id == redemption_id).first()


def get_redemption_by_claim_code(db: Session, claim_code: str) -> Optional[Redemption]:
    """Retrieve redemption record by unique claim code."""
    clean_code = claim_code.strip().upper()
    return (
        db.query(Redemption)
        .join(Redemption.claim)
        .filter(Claim.code == clean_code)
        .first()
    )


def get_shop_redemptions(db: Session, shop_id: int) -> List[Redemption]:
    """Retrieve all redemptions for a given shop ordered by most recent."""
    return (
        db.query(Redemption)
        .filter(Redemption.shop_id == shop_id)
        .order_by(Redemption.redeemed_at.desc())
        .all()
    )
