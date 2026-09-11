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
    from app.models.shop import Shop
    from app.models.claim import Claim


class Offer(Base):
    __tablename__ = "offers"

    __table_args__ = (
        CheckConstraint(
            "discount_type IN ('percentage', 'fixed')",
            name="ck_offers_discount_type",
        ),
        CheckConstraint(
            "status IN ('draft', 'active', 'paused', 'expired')",
            name="ck_offers_status",
        ),
        CheckConstraint(
            "discount_value >= 0",
            name="ck_offers_discount_value_non_negative",
        ),
        CheckConstraint(
            "minimum_purchase IS NULL OR minimum_purchase >= 0",
            name="ck_offers_minimum_purchase_non_negative",
        ),
        CheckConstraint(
            "expires_at > starts_at",
            name="ck_offers_expiry_after_start",
        ),
        Index(
            "ix_offers_status_expires_at",
            "status",
            "expires_at",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True,
    )

    shop_id: Mapped[int] = mapped_column(
        ForeignKey("shops.id"),
        nullable=False,
        index=True,
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    discount_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    discount_value: Mapped[float] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )

    minimum_purchase: Mapped[float | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
    )

    starts_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="draft",
        index=True,
    )

    original_text: Mapped[str | None] = mapped_column(
        Text,
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

    shop: Mapped["Shop"] = relationship(
        "Shop",
        back_populates="offers",
    )

    claims: Mapped[list["Claim"]] = relationship(
        "Claim",
        back_populates="offer",
        cascade="all, delete-orphan",
    )