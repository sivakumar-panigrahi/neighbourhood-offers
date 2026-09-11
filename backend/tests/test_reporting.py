from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base, get_db
from app.main import app
from app.models.claim import Claim
from app.models.offer import Offer
from app.models.points import PointsAccount
from app.models.redemption import Redemption
from app.models.shop import Shop
from app.models.user import User

# Test DB setup
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


@pytest.fixture
def client():
    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def register_and_login(client: TestClient, email: str, role: str) -> str:
    """Helper to register and login a user and return the JWT token."""
    client.post(
        "/auth/register",
        json={"email": email, "password": "password123", "role": role},
    )
    res = client.post(
        "/auth/login",
        data={"username": email, "password": "password123"},
    )
    return res.json()["access_token"]


# =====================================================================
# REPORTING AUTHENTICATION & ACCESS CONTROL
# =====================================================================

def test_shopkeeper_can_access_report_and_rbac_enforcement(client):
    """1, 2, 3, 4. Shopkeeper has access; Shopper & Counter get 403; Unauthenticated gets 401."""
    sk_token = register_and_login(client, "sk_rep@test.com", "shopkeeper")
    client.post("/shops", headers={"Authorization": f"Bearer {sk_token}"}, json={"name": "Rep Shop", "address": "123 St", "city": "Vijayawada"})

    sh_token = register_and_login(client, "shopper_rep@test.com", "shopper")
    ct_token = register_and_login(client, "counter_rep@test.com", "counter")

    # 1. Shopkeeper -> 200 OK
    res_sk = client.get("/reports/monthly", headers={"Authorization": f"Bearer {sk_token}"})
    assert res_sk.status_code == 200
    report = res_sk.json()
    assert "total_spend" in report
    assert "remaining_points" in report
    assert "busy_days" in report
    assert report["shop_name"] == "Rep Shop"

    # 2. Shopper -> 403 Forbidden
    res_sh = client.get("/reports/monthly", headers={"Authorization": f"Bearer {sh_token}"})
    assert res_sh.status_code == 403

    # 3. Counter -> 403 Forbidden
    res_ct = client.get("/reports/monthly", headers={"Authorization": f"Bearer {ct_token}"})
    assert res_ct.status_code == 403

    # 4. Unauthenticated -> 401 Unauthorized
    res_unauth = client.get("/reports/monthly")
    assert res_unauth.status_code == 401


def test_shopkeeper_without_shop_returns_404(client):
    """5. Shopkeeper who has not created a shop yet receives 404 Not Found."""
    sk_token = register_and_login(client, "sk_noshop_rep@test.com", "shopkeeper")
    res = client.get("/reports/monthly", headers={"Authorization": f"Bearer {sk_token}"})
    assert res.status_code == 404
    assert "not created a shop" in res.json()["detail"].lower()


# =====================================================================
# MONTH PARAMETER VALIDATION TESTS
# =====================================================================

def test_month_parameter_validation(client):
    """18, 19. Validates month format YYYY-MM and rejects malformed values."""
    sk_token = register_and_login(client, "sk_val_rep@test.com", "shopkeeper")
    client.post("/shops", headers={"Authorization": f"Bearer {sk_token}"}, json={"name": "Val Shop", "address": "123 St", "city": "VJA"})

    # Valid formats
    assert client.get("/reports/monthly?month=2026-09", headers={"Authorization": f"Bearer {sk_token}"}).status_code == 200
    assert client.get("/reports/monthly?month=2025-01", headers={"Authorization": f"Bearer {sk_token}"}).status_code == 200
    assert client.get("/reports/monthly?month=2030-12", headers={"Authorization": f"Bearer {sk_token}"}).status_code == 200

    # Invalid formats / values
    assert client.get("/reports/monthly?month=2026", headers={"Authorization": f"Bearer {sk_token}"}).status_code == 422
    assert client.get("/reports/monthly?month=09-2026", headers={"Authorization": f"Bearer {sk_token}"}).status_code == 422
    assert client.get("/reports/monthly?month=2026-9", headers={"Authorization": f"Bearer {sk_token}"}).status_code == 422
    assert client.get("/reports/monthly?month=September-2026", headers={"Authorization": f"Bearer {sk_token}"}).status_code == 422
    assert client.get("/reports/monthly?month=2026-13", headers={"Authorization": f"Bearer {sk_token}"}).status_code == 422
    assert client.get("/reports/monthly?month=2026-00", headers={"Authorization": f"Bearer {sk_token}"}).status_code == 422
    assert client.get("/reports/monthly?month=abc", headers={"Authorization": f"Bearer {sk_token}"}).status_code == 422


# =====================================================================
# REPORT CALCULATION, BOUNDARIES, AND BUSY DAYS
# =====================================================================

def test_monthly_report_calculations_and_busy_days(client):
    """
    6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 20.
    Comprehensive business-rule test:
    - Initial Points: 5000
    - September 10: 3 redemptions (₹100, ₹200, ₹100 -> spend ₹400)
    - September 15: 2 redemptions (₹250, ₹50 -> spend ₹300)
    - October 05: 1 redemption (₹500 -> spend ₹500)
    
    September Report:
    - Total spend: ₹700
    - Remaining points: 3800 (current balance after all redemptions)
    - Busy days:
      1. 2026-09-10 (3 redemptions, ₹400 spend)
      2. 2026-09-15 (2 redemptions, ₹300 spend)
    - October redemption excluded from September report.
    """
    sk_token = register_and_login(client, "sk_calc@test.com", "shopkeeper")
    shop_res = client.post(
        "/shops",
        headers={"Authorization": f"Bearer {sk_token}"},
        json={"name": "Anitha's Grocery", "address": "MG Road", "city": "Vijayawada"},
    ).json()
    shop_id = shop_res["id"]

    # Top up 5000 points
    client.post("/shops/me/points/top-up", headers={"Authorization": f"Bearer {sk_token}"}, json={"amount": 5000.0})

    # Create dummy users for foreign keys
    db = TestingSessionLocal()
    try:
        user_shopper = User(email="shopper_rep_calc@test.com", hashed_password="pw", role="shopper")
        user_counter = User(email="counter_rep_calc@test.com", hashed_password="pw", role="counter")
        db.add_all([user_shopper, user_counter])
        db.flush()

        offer = Offer(
            shop_id=shop_id,
            title="Promo",
            discount_type="percentage",
            discount_value=20.0,
            starts_at=datetime(2026, 9, 1, 0, 0, 0, tzinfo=timezone.utc),
            expires_at=datetime(2026, 10, 31, 23, 59, 59, tzinfo=timezone.utc),
            status="active",
        )
        db.add(offer)
        db.flush()

        # Helper to seed redemption
        def seed_redemption(code_suffix: str, discount: float, purchase: float, redeemed_dt: datetime):
            claim = Claim(
                offer_id=offer.id,
                shopper_id=user_shopper.id,
                code=f"NO-{code_suffix}",
                status="redeemed",
                claimed_at=redeemed_dt,
                expires_at=offer.expires_at,
                redeemed_at=redeemed_dt,
            )
            db.add(claim)
            db.flush()

            red = Redemption(
                claim_id=claim.id,
                shop_id=shop_id,
                redeemed_by_id=user_counter.id,
                purchase_amount=purchase,
                discount_amount=discount,
                redeemed_at=redeemed_dt,
            )
            db.add(red)
            db.flush()

        # September 10 redemptions (3 redemptions, total spend 400)
        seed_redemption("SEP10A", 100.0, 500.0, datetime(2026, 9, 10, 10, 30, 0, tzinfo=timezone.utc))
        seed_redemption("SEP10B", 200.0, 1000.0, datetime(2026, 9, 10, 14, 0, 0, tzinfo=timezone.utc))
        seed_redemption("SEP10C", 100.0, 500.0, datetime(2026, 9, 10, 18, 45, 0, tzinfo=timezone.utc))

        # September 15 redemptions (2 redemptions, total spend 300)
        seed_redemption("SEP15A", 250.0, 1250.0, datetime(2026, 9, 15, 11, 0, 0, tzinfo=timezone.utc))
        seed_redemption("SEP15B", 50.0, 250.0, datetime(2026, 9, 15, 16, 20, 0, tzinfo=timezone.utc))

        # October 5 redemption (1 redemption, total spend 500)
        seed_redemption("OCT05A", 500.0, 2500.0, datetime(2026, 10, 5, 12, 0, 0, tzinfo=timezone.utc))

        # Update remaining points: 5000 - 400 - 300 - 500 = 3800
        acct = db.query(PointsAccount).filter(PointsAccount.shop_id == shop_id).first()
        acct.balance = 3800.0
        db.commit()
    finally:
        db.close()

    # Request September 2026 Report
    res_sep = client.get("/reports/monthly?month=2026-09", headers={"Authorization": f"Bearer {sk_token}"})
    assert res_sep.status_code == 200
    rep_sep = res_sep.json()

    assert rep_sep["shop_id"] == shop_id
    assert rep_sep["shop_name"] == "Anitha's Grocery"
    assert rep_sep["month"] == "2026-09"
    assert rep_sep["total_spend"] == 700.0  # 400 + 300
    assert rep_sep["remaining_points"] == 3800.0  # Current live balance

    # Validate Busy Days Ordering
    busy_days = rep_sep["busy_days"]
    assert len(busy_days) == 2

    # Primary: September 10 has 3 redemptions
    assert busy_days[0]["date"] == "2026-09-10"
    assert busy_days[0]["redemptions"] == 3
    assert busy_days[0]["spend"] == 400.0

    # Secondary: September 15 has 2 redemptions
    assert busy_days[1]["date"] == "2026-09-15"
    assert busy_days[1]["redemptions"] == 2
    assert busy_days[1]["spend"] == 300.0

    # Request October 2026 Report
    res_oct = client.get("/reports/monthly?month=2026-10", headers={"Authorization": f"Bearer {sk_token}"})
    assert res_oct.status_code == 200
    rep_oct = res_oct.json()
    assert rep_oct["total_spend"] == 500.0
    assert len(rep_oct["busy_days"]) == 1
    assert rep_oct["busy_days"][0]["date"] == "2026-10-05"

    # Request Month with No Redemptions (August 2026)
    res_aug = client.get("/reports/monthly?month=2026-08", headers={"Authorization": f"Bearer {sk_token}"})
    assert res_aug.status_code == 200
    rep_aug = res_aug.json()
    assert rep_aug["total_spend"] == 0.0
    assert rep_aug["busy_days"] == []
    assert rep_aug["remaining_points"] == 3800.0


# =====================================================================
# CROSS-SHOP DATA ISOLATION TEST
# =====================================================================

def test_cross_shop_reporting_isolation(client):
    """17. Shopkeeper A and Shopkeeper B reports are completely isolated."""
    # Shop A
    sk_a_token = register_and_login(client, "sk_a@test.com", "shopkeeper")
    shop_a = client.post("/shops", headers={"Authorization": f"Bearer {sk_a_token}"}, json={"name": "Shop A", "address": "A St", "city": "VJA"}).json()
    client.post("/shops/me/points/top-up", headers={"Authorization": f"Bearer {sk_a_token}"}, json={"amount": 5000.0})

    # Shop B
    sk_b_token = register_and_login(client, "sk_b@test.com", "shopkeeper")
    shop_b = client.post("/shops", headers={"Authorization": f"Bearer {sk_b_token}"}, json={"name": "Shop B", "address": "B St", "city": "VJA"}).json()
    client.post("/shops/me/points/top-up", headers={"Authorization": f"Bearer {sk_b_token}"}, json={"amount": 3000.0})

    db = TestingSessionLocal()
    try:
        user_shopper = User(email="shopper_iso@test.com", hashed_password="pw", role="shopper")
        user_counter = User(email="counter_iso@test.com", hashed_password="pw", role="counter")
        db.add_all([user_shopper, user_counter])
        db.flush()

        offer_a = Offer(
            shop_id=shop_a["id"],
            title="Offer A",
            discount_type="fixed",
            discount_value=100.0,
            starts_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
            expires_at=datetime(2026, 9, 30, tzinfo=timezone.utc),
            status="active",
        )
        offer_b = Offer(
            shop_id=shop_b["id"],
            title="Offer B",
            discount_type="fixed",
            discount_value=300.0,
            starts_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
            expires_at=datetime(2026, 9, 30, tzinfo=timezone.utc),
            status="active",
        )
        db.add_all([offer_a, offer_b])
        db.flush()

        # Seed 1 redemption for Shop A (spend ₹100 on Sep 12)
        claim_a = Claim(offer_id=offer_a.id, shopper_id=user_shopper.id, code="NO-ISOA1", status="redeemed", claimed_at=datetime(2026, 9, 12, tzinfo=timezone.utc), expires_at=offer_a.expires_at, redeemed_at=datetime(2026, 9, 12, tzinfo=timezone.utc))
        db.add(claim_a)
        db.flush()
        red_a = Redemption(claim_id=claim_a.id, shop_id=shop_a["id"], redeemed_by_id=user_counter.id, purchase_amount=500.0, discount_amount=100.0, redeemed_at=datetime(2026, 9, 12, tzinfo=timezone.utc))
        db.add(red_a)

        # Seed 2 redemptions for Shop B (spend ₹600 total on Sep 12 and Sep 18)
        claim_b1 = Claim(offer_id=offer_b.id, shopper_id=user_shopper.id, code="NO-ISOB1", status="redeemed", claimed_at=datetime(2026, 9, 12, tzinfo=timezone.utc), expires_at=offer_b.expires_at, redeemed_at=datetime(2026, 9, 12, tzinfo=timezone.utc))
        claim_b2 = Claim(offer_id=offer_b.id, shopper_id=user_shopper.id, code="NO-ISOB2", status="redeemed", claimed_at=datetime(2026, 9, 18, tzinfo=timezone.utc), expires_at=offer_b.expires_at, redeemed_at=datetime(2026, 9, 18, tzinfo=timezone.utc))
        db.add_all([claim_b1, claim_b2])
        db.flush()
        red_b1 = Redemption(claim_id=claim_b1.id, shop_id=shop_b["id"], redeemed_by_id=user_counter.id, purchase_amount=1000.0, discount_amount=300.0, redeemed_at=datetime(2026, 9, 12, tzinfo=timezone.utc))
        red_b2 = Redemption(claim_id=claim_b2.id, shop_id=shop_b["id"], redeemed_by_id=user_counter.id, purchase_amount=1000.0, discount_amount=300.0, redeemed_at=datetime(2026, 9, 18, tzinfo=timezone.utc))
        db.add_all([red_b1, red_b2])

        db.commit()
    finally:
        db.close()

    # Shopkeeper A request
    rep_a = client.get("/reports/monthly?month=2026-09", headers={"Authorization": f"Bearer {sk_a_token}"}).json()
    assert rep_a["shop_id"] == shop_a["id"]
    assert rep_a["total_spend"] == 100.0
    assert len(rep_a["busy_days"]) == 1
    assert rep_a["busy_days"][0]["redemptions"] == 1

    # Shopkeeper B request
    rep_b = client.get("/reports/monthly?month=2026-09", headers={"Authorization": f"Bearer {sk_b_token}"}).json()
    assert rep_b["shop_id"] == shop_b["id"]
    assert rep_b["total_spend"] == 600.0
    assert len(rep_b["busy_days"]) == 2
    assert rep_b["busy_days"][0]["redemptions"] == 1
