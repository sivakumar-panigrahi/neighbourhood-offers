"""
Tests for Phase 10 — Realistic Seed / Demo Data Generator
"""

import pytest
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import verify_password
from app.db.database import Base
from app.models.claim import Claim
from app.models.offer import Offer
from app.models.points import PointsAccount
from app.models.points_transaction import PointsTransaction
from app.models.redemption import Redemption
from app.models.shop import Shop
from app.models.user import User
from scripts.seed import DEMO_PASSWORD, seed_database


TEST_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_engine,
)


@pytest.fixture(autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


def test_seed_creates_required_users_and_roles():
    """1, 2. Verifies seed creates all required demo users across all 3 roles with valid password hash."""
    db = TestingSessionLocal()
    try:
        seed_database(db, verbose=False)

        expected_users = [
            ("anitha.demo@example.com", "shopkeeper"),
            ("rahul.demo@example.com", "shopkeeper"),
            ("priya.demo@example.com", "shopper"),
            ("arjun.demo@example.com", "shopper"),
            ("ravi.demo@example.com", "counter"),
            ("meena.demo@example.com", "counter"),
        ]

        for email, role in expected_users:
            user = db.query(User).filter(User.email == email).first()
            assert user is not None, f"User {email} was not seeded"
            assert user.role == role, f"User {email} has unexpected role {user.role}"
            assert verify_password(DEMO_PASSWORD, user.hashed_password), f"Password verification failed for {email}"
    finally:
        db.close()


def test_seed_creates_shops_ownership_and_points():
    """3, 4, 5, 6. Verifies shops, ownership links, points accounts, and initial top-up transactions."""
    db = TestingSessionLocal()
    try:
        seed_database(db, verbose=False)

        anitha = db.query(User).filter(User.email == "anitha.demo@example.com").first()
        rahul = db.query(User).filter(User.email == "rahul.demo@example.com").first()

        shop_a = db.query(Shop).filter(Shop.owner_id == anitha.id).first()
        assert shop_a is not None
        assert "Anitha" in shop_a.name
        assert shop_a.city == "Vijayawada"

        shop_b = db.query(Shop).filter(Shop.owner_id == rahul.id).first()
        assert shop_b is not None
        assert "Rahul" in shop_b.name
        assert shop_b.city == "Vijayawada"

        # Points accounts
        acct_a = db.query(PointsAccount).filter(PointsAccount.shop_id == shop_a.id).first()
        assert acct_a is not None
        assert float(acct_a.balance) >= 0

        # Initial top-up transaction check
        topup_a = (
            db.query(PointsTransaction)
            .filter(
                PointsTransaction.account_id == acct_a.id,
                PointsTransaction.transaction_type == "top_up",
            )
            .first()
        )
        assert topup_a is not None
        assert float(topup_a.amount) == 5000.0
    finally:
        db.close()


def test_seed_creates_realistic_offers_and_lifecycles():
    """7, 8. Verifies offers exist across active, paused, draft, and expired lifecycles."""
    db = TestingSessionLocal()
    try:
        seed_database(db, verbose=False)

        anitha = db.query(User).filter(User.email == "anitha.demo@example.com").first()
        shop_a = db.query(Shop).filter(Shop.owner_id == anitha.id).first()

        offers_a = db.query(Offer).filter(Offer.shop_id == shop_a.id).all()
        statuses = {o.status for o in offers_a}

        assert "active" in statuses
        assert "paused" in statuses
        assert "draft" in statuses
        assert "expired" in statuses

        active_offers = [o for o in offers_a if o.status == "active"]
        assert len(active_offers) >= 3
    finally:
        db.close()


def test_seed_creates_claims_and_redemptions_consistency():
    """9, 10, 11, 12, 13. Verifies claims, redemptions, ledger transactions, and balance consistency."""
    db = TestingSessionLocal()
    try:
        seed_database(db, verbose=False)

        # Active unredeemed claims
        active_claims = db.query(Claim).filter(Claim.status == "claimed").all()
        assert len(active_claims) >= 3
        for c in active_claims:
            assert c.code.startswith("NO-")
            assert c.shopper_id is not None
            assert c.offer_id is not None

        # Redeemed claims and redemptions
        redemptions = db.query(Redemption).all()
        assert len(redemptions) >= 7

        for r in redemptions:
            claim = db.query(Claim).filter(Claim.id == r.claim_id).first()
            assert claim is not None
            assert claim.status == "redeemed"
            assert float(r.purchase_amount) > 0
            assert float(r.discount_amount) > 0
            assert r.redeemed_at is not None

            # Verify negative points transaction linked to this redemption
            txn = (
                db.query(PointsTransaction)
                .filter(PointsTransaction.redemption_id == r.id)
                .first()
            )
            assert txn is not None
            assert txn.transaction_type == "redemption"
            assert float(txn.amount) < 0
            assert abs(float(txn.amount)) == float(r.discount_amount)

        # Verify Points Ledger balance consistency for Shop A
        anitha = db.query(User).filter(User.email == "anitha.demo@example.com").first()
        shop_a = db.query(Shop).filter(Shop.owner_id == anitha.id).first()
        acct_a = db.query(PointsAccount).filter(PointsAccount.shop_id == shop_a.id).first()

        total_txns_sum = (
            db.query(func.sum(PointsTransaction.amount))
            .filter(PointsTransaction.account_id == acct_a.id)
            .scalar()
        )
        assert round(float(total_txns_sum), 2) == round(float(acct_a.balance), 2)
    finally:
        db.close()


def test_seed_idempotency():
    """14, 15, 16, 17. Running seed multiple times does not produce duplicates or change balances."""
    db = TestingSessionLocal()
    try:
        # Run 1
        summary_1 = seed_database(db, verbose=False)

        count_users_1 = db.query(User).count()
        count_shops_1 = db.query(Shop).count()
        count_offers_1 = db.query(Offer).count()
        count_claims_1 = db.query(Claim).count()
        count_redemptions_1 = db.query(Redemption).count()
        count_txns_1 = db.query(PointsTransaction).count()

        # Run 2
        summary_2 = seed_database(db, verbose=False)

        count_users_2 = db.query(User).count()
        count_shops_2 = db.query(Shop).count()
        count_offers_2 = db.query(Offer).count()
        count_claims_2 = db.query(Claim).count()
        count_redemptions_2 = db.query(Redemption).count()
        count_txns_2 = db.query(PointsTransaction).count()

        # Verification
        assert count_users_1 == count_users_2 == 6
        assert count_shops_1 == count_shops_2 == 2
        assert count_offers_1 == count_offers_2 == 10
        assert count_claims_1 == count_claims_2 == 10
        assert count_redemptions_1 == count_redemptions_2 == 7
        assert count_txns_1 == count_txns_2 == 9  # 2 topups + 7 redemptions

        assert summary_1["shop_a_balance"] == summary_2["shop_a_balance"] == 4200.0
        assert summary_1["shop_b_balance"] == summary_2["shop_b_balance"] == 2200.0
    finally:
        db.close()
