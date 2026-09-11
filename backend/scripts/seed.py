"""
Neighbourhood Offers — Seed / Demo Data Generator
=================================================
Populates the database with realistic, deterministic demo data for all roles:
- Shopkeepers (Anitha, Rahul)
- Shoppers (Priya, Arjun)
- Counter Staff (Ravi, Meena)
- Shops with geographical locations & preloaded points accounts
- Offers across multiple lifecycle stages (Active, Paused, Draft, Expired)
- Active shopper claims and completed redemptions
- Immutable points ledger entries (top-ups & redemption deductions)

Idempotent: Safe to execute repeatedly without generating duplicate records.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import logging
import os
import sys
from typing import Dict, List, Optional, Tuple

# Ensure backend directory is in path when running script directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy.orm import Session

from app.core.security import get_password_hash
from app.db.database import SessionLocal
from app.models.claim import Claim
from app.models.offer import Offer
from app.models.points import PointsAccount
from app.models.points_transaction import PointsTransaction
from app.models.redemption import Redemption
from app.models.shop import Shop
from app.models.user import User

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("seed")

DEMO_PASSWORD = "DemoPassword123!"

# Demo Users Definition
DEMO_USERS = [
    {
        "email": "anitha.demo@example.com",
        "role": "shopkeeper",
        "name": "Anitha",
    },
    {
        "email": "rahul.demo@example.com",
        "role": "shopkeeper",
        "name": "Rahul",
    },
    {
        "email": "priya.demo@example.com",
        "role": "shopper",
        "name": "Priya",
    },
    {
        "email": "arjun.demo@example.com",
        "role": "shopper",
        "name": "Arjun",
    },
    {
        "email": "ravi.demo@example.com",
        "role": "counter",
        "name": "Ravi",
    },
    {
        "email": "meena.demo@example.com",
        "role": "counter",
        "name": "Meena",
    },
]


def seed_database(db: Session, verbose: bool = True) -> Dict[str, any]:
    """
    Seed the database idempotently with demo users, shops, points, offers, claims, and redemptions.
    Returns a summary dictionary of seeded entities.
    """
    now = datetime.now(timezone.utc)
    hashed_pwd = get_password_hash(DEMO_PASSWORD)

    # -------------------------------------------------------------
    # 1. SEED USERS
    # -------------------------------------------------------------
    users: Dict[str, User] = {}
    for user_info in DEMO_USERS:
        email = user_info["email"]
        user = db.query(User).filter(User.email == email).first()
        if not user:
            user = User(
                email=email,
                hashed_password=hashed_pwd,
                role=user_info["role"],
            )
            db.add(user)
            db.flush()
        users[email] = user

    # -------------------------------------------------------------
    # 2. SEED SHOPS
    # -------------------------------------------------------------
    shops_data = [
        {
            "owner_email": "anitha.demo@example.com",
            "name": "Anitha's Grocery",
            "address": "Shop #12, MG Road, Governorpet",
            "city": "Vijayawada",
            "latitude": 16.5062,
            "longitude": 80.6480,
            "initial_points": Decimal("5000.00"),
        },
        {
            "owner_email": "rahul.demo@example.com",
            "name": "Rahul's Fashion Corner",
            "address": "45-1-8 Eluru Road, Besant Road Junction",
            "city": "Vijayawada",
            "latitude": 16.5131,
            "longitude": 80.6325,
            "initial_points": Decimal("3000.00"),
        },
    ]

    shops: Dict[str, Shop] = {}
    points_accounts: Dict[int, PointsAccount] = {}

    for s_info in shops_data:
        owner = users[s_info["owner_email"]]
        shop = db.query(Shop).filter(Shop.owner_id == owner.id).first()
        if not shop:
            shop = Shop(
                name=s_info["name"],
                owner_id=owner.id,
                address=s_info["address"],
                city=s_info["city"],
                latitude=s_info["latitude"],
                longitude=s_info["longitude"],
            )
            db.add(shop)
            db.flush()
        shops[s_info["owner_email"]] = shop

        # Seed PointsAccount & initial top-up transaction
        acct = db.query(PointsAccount).filter(PointsAccount.shop_id == shop.id).first()
        if not acct:
            acct = PointsAccount(
                shop_id=shop.id,
                balance=s_info["initial_points"],
            )
            db.add(acct)
            db.flush()

            # Record initial top-up transaction in points ledger
            topup_txn = PointsTransaction(
                account_id=acct.id,
                transaction_type="top_up",
                amount=float(s_info["initial_points"]),
                balance_after=float(s_info["initial_points"]),
                description=f"Initial preloaded demo points for {shop.name}",
            )
            db.add(topup_txn)
            db.flush()
        points_accounts[shop.id] = acct

    # -------------------------------------------------------------
    # 3. SEED OFFERS
    # -------------------------------------------------------------
    starts_active = now - timedelta(days=10)
    expires_active = now + timedelta(days=30)
    starts_expired = now - timedelta(days=45)
    expires_expired = now - timedelta(days=15)

    offers_data = [
        # Anitha's Grocery (Shop A)
        {
            "shop_key": "anitha.demo@example.com",
            "title": "20% OFF on groceries",
            "description": "Get 20% discount on all daily grocery and pantry staples.",
            "discount_type": "percentage",
            "discount_value": Decimal("20.00"),
            "minimum_purchase": Decimal("500.00"),
            "status": "active",
            "starts_at": starts_active,
            "expires_at": expires_active,
            "original_text": "20% discount on all daily groceries on purchase above 500",
        },
        {
            "shop_key": "anitha.demo@example.com",
            "title": "Rs.100 OFF on bills above Rs.1000",
            "description": "Flat Rs.100 instant cashback discount for bulk household purchases.",
            "discount_type": "fixed",
            "discount_value": Decimal("100.00"),
            "minimum_purchase": Decimal("1000.00"),
            "status": "active",
            "starts_at": starts_active,
            "expires_at": expires_active,
            "original_text": "flat 100 off on total bill exceeding 1000",
        },
        {
            "shop_key": "anitha.demo@example.com",
            "title": "15% OFF on fresh produce",
            "description": "Farm-fresh organic fruits and vegetables with 15% discount.",
            "discount_type": "percentage",
            "discount_value": Decimal("15.00"),
            "minimum_purchase": Decimal("300.00"),
            "status": "active",
            "starts_at": starts_active,
            "expires_at": expires_active,
            "original_text": "15% off fresh vegetables and fruits min 300",
        },
        {
            "shop_key": "anitha.demo@example.com",
            "title": "Weekend Dairy Special - Paused",
            "description": "Weekend special 10% discount on milk and paneer (temporarily paused).",
            "discount_type": "percentage",
            "discount_value": Decimal("10.00"),
            "minimum_purchase": Decimal("200.00"),
            "status": "paused",
            "starts_at": starts_active,
            "expires_at": expires_active,
            "original_text": "10% off dairy products on weekends",
        },
        {
            "shop_key": "anitha.demo@example.com",
            "title": "Festival Hamper Bundle - Draft",
            "description": "Upcoming festive season grocery gift hampers.",
            "discount_type": "fixed",
            "discount_value": Decimal("250.00"),
            "minimum_purchase": Decimal("1500.00"),
            "status": "draft",
            "starts_at": starts_active,
            "expires_at": expires_active,
            "original_text": "draft diwali gift hamper 250 off on 1500",
        },
        {
            "shop_key": "anitha.demo@example.com",
            "title": "Monsoon Harvest Clearance - Expired",
            "description": "Previous seasonal harvest discount now concluded.",
            "discount_type": "percentage",
            "discount_value": Decimal("25.00"),
            "minimum_purchase": Decimal("400.00"),
            "status": "expired",
            "starts_at": starts_expired,
            "expires_at": expires_expired,
            "original_text": "25% off monsoon harvest clearance expired",
        },
        # Rahul's Fashion Corner (Shop B)
        {
            "shop_key": "rahul.demo@example.com",
            "title": "15% OFF on men's wear",
            "description": "Exclusive discount on formal shirts, trousers, and ethnic kurtas.",
            "discount_type": "percentage",
            "discount_value": Decimal("15.00"),
            "minimum_purchase": Decimal("800.00"),
            "status": "active",
            "starts_at": starts_active,
            "expires_at": expires_active,
            "original_text": "15% off on men's apparel above 800",
        },
        {
            "shop_key": "rahul.demo@example.com",
            "title": "Rs.500 OFF on bills above Rs.3000",
            "description": "Festive wardrobe upgrade savings: flat Rs.500 off on grand shopping.",
            "discount_type": "fixed",
            "discount_value": Decimal("500.00"),
            "minimum_purchase": Decimal("3000.00"),
            "status": "active",
            "starts_at": starts_active,
            "expires_at": expires_active,
            "original_text": "flat 500 off when shopping above 3000",
        },
        {
            "shop_key": "rahul.demo@example.com",
            "title": "10% OFF on selected accessories",
            "description": "Belts, wallets, and watches with 10% instant discount.",
            "discount_type": "percentage",
            "discount_value": Decimal("10.00"),
            "minimum_purchase": Decimal("400.00"),
            "status": "active",
            "starts_at": starts_active,
            "expires_at": expires_active,
            "original_text": "10% off accessories minimum 400",
        },
        {
            "shop_key": "rahul.demo@example.com",
            "title": "Ethnic Wedding Collection - Paused",
            "description": "Silk sherwanis and sarees discount (paused for stock replenishment).",
            "discount_type": "percentage",
            "discount_value": Decimal("20.00"),
            "minimum_purchase": Decimal("2000.00"),
            "status": "paused",
            "starts_at": starts_active,
            "expires_at": expires_active,
            "original_text": "20% off ethnic wedding collection paused",
        },
    ]

    offers: Dict[Tuple[int, str], Offer] = {}
    for o_info in offers_data:
        shop = shops[o_info["shop_key"]]
        offer = (
            db.query(Offer)
            .filter(Offer.shop_id == shop.id, Offer.title == o_info["title"])
            .first()
        )
        if not offer:
            offer = Offer(
                shop_id=shop.id,
                title=o_info["title"],
                description=o_info["description"],
                discount_type=o_info["discount_type"],
                discount_value=o_info["discount_value"],
                minimum_purchase=o_info["minimum_purchase"],
                status=o_info["status"],
                starts_at=o_info["starts_at"],
                expires_at=o_info["expires_at"],
                original_text=o_info["original_text"],
            )
            db.add(offer)
            db.flush()
        offers[(shop.id, o_info["title"])] = offer

    # -------------------------------------------------------------
    # 4. SEED CLAIMS & REDEMPTIONS (DYNAMIC CURRENT & PREVIOUS DATES)
    # -------------------------------------------------------------
    # Dynamic dates within the current UTC month for rich reporting
    curr_year = now.year
    curr_month = now.month
    day_limit = max(1, now.day)

    # Days in the current month (safe within [1, day_limit])
    day_1 = max(1, min(day_limit, 2))
    day_2 = max(1, min(day_limit, 5))
    day_3 = max(1, min(day_limit, 8))

    date_curr_1 = datetime(curr_year, curr_month, day_1, 10, 30, tzinfo=timezone.utc)
    date_curr_2 = datetime(curr_year, curr_month, day_2, 14, 15, tzinfo=timezone.utc)
    date_curr_3 = datetime(curr_year, curr_month, day_3, 18, 45, tzinfo=timezone.utc)

    # Previous month date (e.g. 15th of previous month)
    prev_year = curr_year if curr_month > 1 else curr_year - 1
    prev_month = curr_month - 1 if curr_month > 1 else 12
    date_prev = datetime(prev_year, prev_month, 15, 11, 0, tzinfo=timezone.utc)

    shop_a = shops["anitha.demo@example.com"]
    shop_b = shops["rahul.demo@example.com"]

    offer_a_groceries = offers[(shop_a.id, "20% OFF on groceries")]
    offer_a_bills = offers[(shop_a.id, "Rs.100 OFF on bills above Rs.1000")]
    offer_a_produce = offers[(shop_a.id, "15% OFF on fresh produce")]

    offer_b_mens = offers[(shop_b.id, "15% OFF on men's wear")]
    offer_b_bills = offers[(shop_b.id, "Rs.500 OFF on bills above Rs.3000")]

    shopper_priya = users["priya.demo@example.com"]
    shopper_arjun = users["arjun.demo@example.com"]
    counter_ravi = users["ravi.demo@example.com"]
    counter_meena = users["meena.demo@example.com"]

    # Active Claims (Unredeemed)
    active_claims_data = [
        {
            "code": "NO-DEMOACT1",
            "offer": offer_a_groceries,
            "shopper": shopper_priya,
            "claimed_at": now - timedelta(hours=2),
            "expires_at": now + timedelta(days=2),
        },
        {
            "code": "NO-DEMOACT2",
            "offer": offer_a_bills,
            "shopper": shopper_arjun,
            "claimed_at": now - timedelta(hours=1),
            "expires_at": now + timedelta(days=3),
        },
        {
            "code": "NO-DEMOACT3",
            "offer": offer_b_mens,
            "shopper": shopper_priya,
            "claimed_at": now - timedelta(hours=3),
            "expires_at": now + timedelta(days=2),
        },
    ]

    for ac in active_claims_data:
        claim = db.query(Claim).filter(Claim.code == ac["code"]).first()
        if not claim:
            claim = Claim(
                offer_id=ac["offer"].id,
                shopper_id=ac["shopper"].id,
                code=ac["code"],
                status="claimed",
                claimed_at=ac["claimed_at"],
                expires_at=ac["expires_at"],
            )
            db.add(claim)
            db.flush()

    # Redeemed Claims & Completed Redemptions
    redemptions_data = [
        # Shop A — Current Month Day 1 (2 redemptions on date_curr_1)
        {
            "claim_code": "NO-DEMORDM1",
            "offer": offer_a_groceries,
            "shopper": shopper_priya,
            "shop": shop_a,
            "counter": counter_ravi,
            "purchase_amount": Decimal("1000.00"),
            "discount_amount": Decimal("200.00"),  # 20% of 1000
            "redeemed_at": date_curr_1,
        },
        {
            "claim_code": "NO-DEMORDM2",
            "offer": offer_a_produce,
            "shopper": shopper_arjun,
            "shop": shop_a,
            "counter": counter_ravi,
            "purchase_amount": Decimal("600.00"),
            "discount_amount": Decimal("90.00"),  # 15% of 600
            "redeemed_at": date_curr_1 + timedelta(hours=2),
        },
        # Shop A — Current Month Day 2 (1 redemption on date_curr_2)
        {
            "claim_code": "NO-DEMORDM3",
            "offer": offer_a_bills,
            "shopper": shopper_priya,
            "shop": shop_a,
            "counter": counter_meena,
            "purchase_amount": Decimal("1500.00"),
            "discount_amount": Decimal("100.00"),  # Flat 100
            "redeemed_at": date_curr_2,
        },
        # Shop A — Current Month Day 3 (1 redemption on date_curr_3)
        {
            "claim_code": "NO-DEMORDM4",
            "offer": offer_a_groceries,
            "shopper": shopper_arjun,
            "shop": shop_a,
            "counter": counter_ravi,
            "purchase_amount": Decimal("1250.00"),
            "discount_amount": Decimal("250.00"),  # 20% of 1250
            "redeemed_at": date_curr_3,
        },
        # Shop A — Previous Month (Boundary testing)
        {
            "claim_code": "NO-DEMORDM5",
            "offer": offer_a_groceries,
            "shopper": shopper_priya,
            "shop": shop_a,
            "counter": counter_ravi,
            "purchase_amount": Decimal("800.00"),
            "discount_amount": Decimal("160.00"),  # 20% of 800
            "redeemed_at": date_prev,
        },
        # Shop B — Current Month Day 2 (1 redemption on date_curr_2)
        {
            "claim_code": "NO-DEMORDM6",
            "offer": offer_b_mens,
            "shopper": shopper_arjun,
            "shop": shop_b,
            "counter": counter_meena,
            "purchase_amount": Decimal("2000.00"),
            "discount_amount": Decimal("300.00"),  # 15% of 2000
            "redeemed_at": date_curr_2,
        },
        # Shop B — Current Month Day 3 (1 redemption on date_curr_3)
        {
            "claim_code": "NO-DEMORDM7",
            "offer": offer_b_bills,
            "shopper": shopper_priya,
            "shop": shop_b,
            "counter": counter_meena,
            "purchase_amount": Decimal("4000.00"),
            "discount_amount": Decimal("500.00"),  # Flat 500
            "redeemed_at": date_curr_3,
        },
    ]

    for r_info in redemptions_data:
        claim_code = r_info["claim_code"]
        claim = db.query(Claim).filter(Claim.code == claim_code).first()
        if not claim:
            # Create redeemed claim
            claim = Claim(
                offer_id=r_info["offer"].id,
                shopper_id=r_info["shopper"].id,
                code=claim_code,
                status="redeemed",
                claimed_at=r_info["redeemed_at"] - timedelta(hours=3),
                expires_at=r_info["redeemed_at"] + timedelta(days=1),
            )
            db.add(claim)
            db.flush()

            # Create Redemption record
            redemption = Redemption(
                claim_id=claim.id,
                shop_id=r_info["shop"].id,
                redeemed_by_id=r_info["counter"].id,
                purchase_amount=r_info["purchase_amount"],
                discount_amount=r_info["discount_amount"],
                redeemed_at=r_info["redeemed_at"],
            )
            db.add(redemption)
            db.flush()

            # Deduct points from PointsAccount & record PointsTransaction
            acct = (
                db.query(PointsAccount)
                .filter(PointsAccount.shop_id == r_info["shop"].id)
                .with_for_update()
                .first()
            )
            disc_amt = r_info["discount_amount"]
            cur_bal = Decimal(str(acct.balance))
            new_bal = float(max(Decimal("0.00"), cur_bal - disc_amt))
            acct.balance = new_bal

            txn = PointsTransaction(
                account_id=acct.id,
                transaction_type="redemption",
                amount=-float(disc_amt),
                balance_after=new_bal,
                redemption_id=redemption.id,
                description=f"Redemption discount for claim {claim_code}",
                created_at=r_info["redeemed_at"],
            )
            db.add(txn)
            db.flush()

    db.commit()

    # -------------------------------------------------------------
    # 5. SUMMARY OUTPUT
    # -------------------------------------------------------------
    summary = {
        "users": len(users),
        "shops": len(shops),
        "offers": len(offers),
        "active_claims": len(active_claims_data),
        "redemptions": len(redemptions_data),
        "shop_a_balance": float(points_accounts[shop_a.id].balance),
        "shop_b_balance": float(points_accounts[shop_b.id].balance),
    }

    if verbose:
        print("\n" + "=" * 50)
        print("   NEIGHBOURHOOD OFFERS -- DEMO DATA READY")
        print("=" * 50)
        print("\nDEMO CREDENTIALS (Shared Password: DemoPassword123!)")
        print("-" * 50)
        for user_info in DEMO_USERS:
            print(f"  [{user_info['role'].upper():<10}] {user_info['name']:<8} -> {user_info['email']}")

        print("\nSHOPS & POINTS BALANCES")
        print("-" * 50)
        for s_info in shops_data:
            s_owner = users[s_info["owner_email"]]
            s_obj = shops[s_info["owner_email"]]
            s_pts = db.query(PointsAccount).filter(PointsAccount.shop_id == s_obj.id).first()
            print(f"  * {s_obj.name} ({s_obj.city}) | Owner: {s_owner.email} | Points: {s_pts.balance:.2f}")

        print("\nOFFERS CREATED")
        print("-" * 50)
        for (sh_id, title), off in offers.items():
            print(f"  * [{off.status.upper():<7}] {off.title} ({off.discount_type}: {off.discount_value})")

        print("\nACTIVE CLAIMS")
        print("-" * 50)
        for ac in active_claims_data:
            print(f"  * Code: {ac['code']} | Shopper: {ac['shopper'].email} | Offer: {ac['offer'].title}")

        print("\nREDEMPTIONS & REPORTING DATA")
        print("-" * 50)
        print(f"  * Seeded {len(redemptions_data)} redemptions across multiple dates for dynamic monthly reporting.")
        print(f"  * Current Month: {curr_year:04d}-{curr_month:02d} with active spend & footfall.")
        print(f"  * Previous Month: {prev_year:04d}-{prev_month:02d} for date boundary filtering.")
        print("=" * 50 + "\n")

    return summary


def main():
    """Main execution point for `python -m scripts.seed`."""
    db = SessionLocal()
    try:
        seed_database(db, verbose=True)
    finally:
        db.close()


if __name__ == "__main__":
    main()
