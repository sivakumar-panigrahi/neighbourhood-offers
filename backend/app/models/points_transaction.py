from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


if TYPE_CHECKING:
    from app.models.points import PointsAccount
    from app.models.redemption import Redemption


class PointsTransaction(Base):
    __tablename__ = "points_transactions"

    __table_args__ = (
        CheckConstraint(
            "transaction_type IN ('top_up', 'redemption', 'adjustment')",
            name="ck_points_transactions_type",
        ),
        CheckConstraint(
            "amount != 0",
            name="ck_points_transactions_amount_non_zero",
        ),
        CheckConstraint(
            "balance_after >= 0",
            name="ck_points_transactions_balance_after_non_negative",
        ),
        Index(
            "ix_points_transactions_account_created_at",
            "account_id",
            "created_at",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True,
    )

    account_id: Mapped[int] = mapped_column(
        ForeignKey("points_accounts.id"),
        nullable=False,
        index=True,
    )

    transaction_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        index=True,
    )

    amount: Mapped[float] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    balance_after: Mapped[float] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    redemption_id: Mapped[int | None] = mapped_column(
        ForeignKey("redemptions.id"),
        nullable=True,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    account: Mapped["PointsAccount"] = relationship(
        "PointsAccount",
        back_populates="transactions",
    )

    redemption: Mapped["Redemption | None"] = relationship(
        "Redemption",
    )