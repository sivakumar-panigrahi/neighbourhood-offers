from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.points import PointsAccount
from app.models.shop import Shop
from app.schemas.shop import ShopCreate


def create_shop(db: Session, shop_in: ShopCreate, owner_id: int) -> Shop:
    """Create a shop for the authenticated shopkeeper."""
    existing_shop = db.query(Shop).filter(Shop.owner_id == owner_id).first()
    if existing_shop:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Shopkeeper already owns a shop. Only one shop per shopkeeper is allowed.",
        )

    shop = Shop(
        owner_id=owner_id,
        name=shop_in.name,
        address=shop_in.address,
        city=shop_in.city,
        latitude=shop_in.latitude,
        longitude=shop_in.longitude,
    )
    db.add(shop)
    db.flush()

    # Automatically initialize points account for the new shop with 0 balance
    points_account = PointsAccount(shop_id=shop.id, balance=0.0)
    db.add(points_account)

    db.commit()
    db.refresh(shop)
    return shop


def get_shop_by_owner(db: Session, owner_id: int) -> Optional[Shop]:
    """Retrieve shop owned by the given user ID."""
    return db.query(Shop).filter(Shop.owner_id == owner_id).first()


def get_shop_by_id(db: Session, shop_id: int) -> Optional[Shop]:
    """Retrieve shop by shop ID."""
    return db.query(Shop).filter(Shop.id == shop_id).first()
