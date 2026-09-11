from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


if TYPE_CHECKING:
    from app.models.claim import Claim
    from app.models.shop import Shop
    from app.models.user import User


class Redemption(Base):
    __tablename__ = "redemptions"

    __table_args__ = (
        CheckConstraint(
            "purchase_amount >= 0",
            name="ck_redemptions_purchase_amount_non_negative",
        ),
        CheckConstraint(
            "discount_amount >= 0",
            name="ck_redemptions_discount_amount_non_negative",
        ),
        Index(
            "ix_redemptions_shop_redeemed_at",
            "shop_id",
            "redeemed_at",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True,
    )

    claim_id: Mapped[int] = mapped_column(
        ForeignKey("claims.id"),
        unique=True,
        nullable=False,
        index=True,
    )

    shop_id: Mapped[int] = mapped_column(
        ForeignKey("shops.id"),
        nullable=False,
        index=True,
    )

    redeemed_by_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    purchase_amount: Mapped[float] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )

    discount_amount: Mapped[float] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )

    redeemed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    claim: Mapped["Claim"] = relationship(
        "Claim",
        back_populates="redemption",
    )

    shop: Mapped["Shop"] = relationship(
        "Shop",
    )

    redeemed_by: Mapped["User"] = relationship(
        "User",
        foreign_keys=[redeemed_by_id],
    )