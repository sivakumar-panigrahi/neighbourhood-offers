from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


if TYPE_CHECKING:
    from app.models.offer import Offer
    from app.models.user import User
    from app.models.redemption import Redemption


class Claim(Base):
    __tablename__ = "claims"

    __table_args__ = (
        CheckConstraint(
            "status IN ('claimed', 'redeemed', 'expired', 'cancelled')",
            name="ck_claims_status",
        ),
        Index(
            "ix_claims_shopper_status",
            "shopper_id",
            "status",
        ),
        Index(
            "ix_claims_offer_status",
            "offer_id",
            "status",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True,
    )

    offer_id: Mapped[int] = mapped_column(
        ForeignKey("offers.id"),
        nullable=False,
        index=True,
    )

    shopper_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="claimed",
        index=True,
    )

    claimed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    redeemed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
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

    offer: Mapped["Offer"] = relationship(
        "Offer",
        back_populates="claims",
    )

    shopper: Mapped["User"] = relationship(
        "User",
        back_populates="claims",
        foreign_keys=[shopper_id],
    )

    redemption: Mapped["Redemption | None"] = relationship(
        "Redemption",
        back_populates="claim",
        uselist=False,
        cascade="all, delete-orphan",
    )