from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Numeric,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


if TYPE_CHECKING:
    from app.models.shop import Shop
    from app.models.points_transaction import PointsTransaction


class PointsAccount(Base):
    __tablename__ = "points_accounts"

    __table_args__ = (
        CheckConstraint(
            "balance >= 0",
            name="ck_points_accounts_balance_non_negative",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True,
    )

    shop_id: Mapped[int] = mapped_column(
        ForeignKey("shops.id"),
        unique=True,
        nullable=False,
        index=True,
    )

    balance: Mapped[float] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=0,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    shop: Mapped["Shop"] = relationship(
        "Shop",
        back_populates="points_account",
    )

    transactions: Mapped[list["PointsTransaction"]] = relationship(
        "PointsTransaction",
        back_populates="account",
        cascade="all, delete-orphan",
    )