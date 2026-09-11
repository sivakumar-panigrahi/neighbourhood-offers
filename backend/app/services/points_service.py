from decimal import Decimal
import logging
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.points import PointsAccount
from app.models.points_transaction import PointsTransaction

logger = logging.getLogger(__name__)


def get_points_account(db: Session, shop_id: int) -> Optional[PointsAccount]:
    """Retrieve PointsAccount for a given shop ID."""
    return db.query(PointsAccount).filter(PointsAccount.shop_id == shop_id).first()


def top_up_points(
    db: Session,
    shop_id: int,
    amount: float,
    description: Optional[str] = None,
) -> PointsAccount:
    """
    Top up points balance for a shop's PointsAccount.
    Acquires row-level lock, updates balance, and logs positive PointsTransaction.
    """
    if amount <= 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Top-up amount must be greater than zero.",
        )

    account = (
        db.query(PointsAccount)
        .filter(PointsAccount.shop_id == shop_id)
        .with_for_update()
        .first()
    )

    if not account:
        account = PointsAccount(shop_id=shop_id, balance=0.0)
        db.add(account)
        db.flush()

    dec_balance = Decimal(str(account.balance))
    dec_amount = Decimal(str(amount)).quantize(Decimal("0.01"))
    new_balance = float((dec_balance + dec_amount).quantize(Decimal("0.01")))

    account.balance = new_balance

    txn = PointsTransaction(
        account_id=account.id,
        transaction_type="top_up",
        amount=float(dec_amount),
        balance_after=new_balance,
        description=description or f"Preload top-up of {dec_amount} points",
    )
    db.add(txn)
    db.commit()
    db.refresh(account)

    logger.info(f"Points top-up of {dec_amount} for shop {shop_id}. New balance: {new_balance}")
    return account
