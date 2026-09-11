from datetime import datetime, timedelta, timezone
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base, get_db
from app.main import app
from app.models.claim import Claim
from app.models.points import PointsAccount
from app.models.points_transaction import PointsTransaction
from app.models.redemption import Redemption
from app.services.redemption_service import calculate_discount

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


def setup_complete_flow(
    client: TestClient,
    discount_type: str = "percentage",
    discount_value: float = 20.0,
    minimum_purchase: float = 1000.0,
    initial_points: float = 5000.0,
    offer_status: str = "active",
) -> dict:
    """Setup full shopkeeper, shop, points, active offer, shopper, and claim."""
    now = datetime.now(timezone.utc)
    ts = int(now.timestamp() * 1000)

    # 1. Shopkeeper & Shop
    sk_token = register_and_login(client, f"sk_{ts}@test.com", "shopkeeper")
    shop = client.post(
        "/shops",
        headers={"Authorization": f"Bearer {sk_token}"},
        json={"name": "Test Shop", "address": "123 Market Rd", "city": "Vijayawada"},
    ).json()

    # 2. Top-up shopkeeper points
    if initial_points > 0:
        client.post(
            "/shops/me/points/top-up",
            headers={"Authorization": f"Bearer {sk_token}"},
            json={"amount": initial_points},
        )

    # 3. Create Offer
    offer = client.post(
        "/offers",
        headers={"Authorization": f"Bearer {sk_token}"},
        json={
            "title": "Promo Offer",
            "description": "Promo Details",
            "discount_type": discount_type,
            "discount_value": discount_value,
            "minimum_purchase": minimum_purchase,
            "starts_at": (now - timedelta(hours=1)).isoformat(),
            "expires_at": (now + timedelta(days=5)).isoformat(),
        },
    ).json()

    if offer_status == "active":
        client.post(f"/offers/{offer['id']}/activate", headers={"Authorization": f"Bearer {sk_token}"})
    elif offer_status == "paused":
        client.post(f"/offers/{offer['id']}/activate", headers={"Authorization": f"Bearer {sk_token}"})
        client.post(f"/offers/{offer['id']}/pause", headers={"Authorization": f"Bearer {sk_token}"})

    # 4. Shopper & Claim
    sh_token = register_and_login(client, f"sh_{ts}@test.com", "shopper")
    claim_res = client.post(f"/offers/{offer['id']}/claim", headers={"Authorization": f"Bearer {sh_token}"})
    claim = claim_res.json() if claim_res.status_code == 201 else None

    # 5. Counter Staff
    ct_token = register_and_login(client, f"ct_{ts}@test.com", "counter")

    return {
        "sk_token": sk_token,
        "sh_token": sh_token,
        "ct_token": ct_token,
        "shop": shop,
        "offer": offer,
        "claim": claim,
    }


# =====================================================================
# DISCOUNT CALCULATION UNIT TESTS
# =====================================================================

def test_calculate_discount_percentage():
    """5. Percentage discount calculation."""
    # 20% on 2000 -> 400 discount, 1600 final
    disc, final = calculate_discount(Decimal("2000.00"), "percentage", Decimal("20.00"))
    assert disc == Decimal("400.00")
    assert final == Decimal("1600.00")


def test_calculate_discount_fixed():
    """6. Fixed discount calculation."""
    # 500 off on 2000 -> 500 discount, 1500 final
    disc, final = calculate_discount(Decimal("2000.00"), "fixed", Decimal("500.00"))
    assert disc == Decimal("500.00")
    assert final == Decimal("1500.00")


def test_calculate_discount_capped_at_purchase_amount():
    """7 & 8. Fixed discount exceeding purchase amount is capped; final is never negative."""
    # 1000 off on 600 purchase -> discount = 600, final = 0
    disc, final = calculate_discount(Decimal("600.00"), "fixed", Decimal("1000.00"))
    assert disc == Decimal("600.00")
    assert final == Decimal("0.00")

    # 100% off on 1000 purchase -> discount = 1000, final = 0
    disc100, final100 = calculate_discount(Decimal("1000.00"), "percentage", Decimal("100.00"))
    assert disc100 == Decimal("1000.00")
    assert final100 == Decimal("0.00")


# =====================================================================
# REDEMPTION ENGINE CORE TESTS
# =====================================================================

def test_counter_can_redeem_valid_claim(client):
    """1, 18, 19, 20, 21, 22, 23, 24. Successful redemption flow and ledger updates."""
    data = setup_complete_flow(client, discount_type="percentage", discount_value=20.0, initial_points=5000.0)
    ct_token = data["ct_token"]
    claim_code = data["claim"]["code"]

    # Execute redemption
    res = client.post(
        "/redemptions",
        headers={"Authorization": f"Bearer {ct_token}", "Idempotency-Key": "test-redemption-1"},
        json={"claim_code": claim_code, "purchase_amount": 2000.0},
    )
    assert res.status_code == 201
    red_data = res.json()

    # Validate financial calculations
    assert red_data["purchase_amount"] == 2000.0
    assert red_data["discount_amount"] == 400.0
    assert red_data["final_amount"] == 1600.0
    assert red_data["points_deducted"] == 400.0
    assert red_data["remaining_points"] == 4600.0
    assert red_data["claim_code"] == claim_code

    # Verify DB state directly
    db = TestingSessionLocal()
    try:
        # 1. Claim status
        claim_db = db.scalar(select(Claim).where(Claim.code == claim_code))
        assert claim_db.status == "redeemed"
        assert claim_db.redeemed_at is not None

        # 2. Redemption record
        red_db = db.scalar(select(Redemption).where(Redemption.id == red_data["id"]))
        assert red_db is not None
        assert float(red_db.purchase_amount) == 2000.0
        assert float(red_db.discount_amount) == 400.0

        # 3. Points account balance
        acct_db = db.scalar(select(PointsAccount).where(PointsAccount.shop_id == data["shop"]["id"]))
        assert float(acct_db.balance) == 4600.0

        # 4. Points transactions
        txns = db.scalars(select(PointsTransaction).where(PointsTransaction.account_id == acct_db.id).order_by(PointsTransaction.created_at.asc())).all()
        # Expect top_up (+5000) and redemption (-400)
        assert len(txns) == 2
        assert txns[0].transaction_type == "top_up"
        assert float(txns[0].amount) == 5000.0

        assert txns[1].transaction_type == "redemption"
        assert float(txns[1].amount) == -400.0
        assert float(txns[1].balance_after) == 4600.0
        assert txns[1].redemption_id == red_db.id
    finally:
        db.close()


def test_shopper_and_shopkeeper_cannot_redeem(client):
    """2, 3, 4. Shoppers, Shopkeepers, and Unauthenticated cannot redeem claims (403/401)."""
    data = setup_complete_flow(client)
    claim_code = data["claim"]["code"]
    payload = {"claim_code": claim_code, "purchase_amount": 2000.0}

    # Shopper attempt -> 403
    res_sh = client.post("/redemptions", headers={"Authorization": f"Bearer {data['sh_token']}"}, json=payload)
    assert res_sh.status_code == 403

    # Shopkeeper attempt -> 403
    res_sk = client.post("/redemptions", headers={"Authorization": f"Bearer {data['sk_token']}"}, json=payload)
    assert res_sk.status_code == 403

    # Unauthenticated attempt -> 401
    res_unauth = client.post("/redemptions", json=payload)
    assert res_unauth.status_code == 401


def test_minimum_purchase_failure(client):
    """9. Redemption below minimum purchase is rejected with 409 and no points deducted."""
    data = setup_complete_flow(client, minimum_purchase=1500.0, initial_points=5000.0)
    ct_token = data["ct_token"]
    claim_code = data["claim"]["code"]

    # Purchase amount 1000 is below 1500
    res = client.post(
        "/redemptions",
        headers={"Authorization": f"Bearer {ct_token}"},
        json={"claim_code": claim_code, "purchase_amount": 1000.0},
    )
    assert res.status_code == 409
    assert "minimum required" in res.json()["detail"].lower()

    # Verify zero points deducted and no redemption created
    db = TestingSessionLocal()
    try:
        assert db.scalar(select(PointsAccount).where(PointsAccount.shop_id == data["shop"]["id"])).balance == 5000.0
        assert len(db.scalars(select(Redemption)).all()) == 0
        assert db.scalar(select(Claim).where(Claim.code == claim_code)).status == "claimed"
    finally:
        db.close()


def test_insufficient_points_balance_rejection(client):
    """15, 16, 17. Insufficient points balance rejects redemption with 409 and zero state mutation."""
    data = setup_complete_flow(client, discount_type="fixed", discount_value=500.0, initial_points=300.0)
    ct_token = data["ct_token"]
    claim_code = data["claim"]["code"]

    # Discount requires 500 points, shop has only 300
    res = client.post(
        "/redemptions",
        headers={"Authorization": f"Bearer {ct_token}"},
        json={"claim_code": claim_code, "purchase_amount": 2000.0},
    )
    assert res.status_code == 409
    assert "insufficient points" in res.json()["detail"].lower()

    # Invariants verification
    db = TestingSessionLocal()
    try:
        assert db.scalar(select(PointsAccount).where(PointsAccount.shop_id == data["shop"]["id"])).balance == 300.0
        assert len(db.scalars(select(Redemption)).all()) == 0
        assert db.scalar(select(Claim).where(Claim.code == claim_code)).status == "claimed"
    finally:
        db.close()


def test_cannot_redeem_already_redeemed_claim(client):
    """14. A claim cannot be redeemed twice."""
    data = setup_complete_flow(client, initial_points=5000.0)
    ct_token = data["ct_token"]
    claim_code = data["claim"]["code"]

    # 1. First redemption -> 201
    res1 = client.post(
        "/redemptions",
        headers={"Authorization": f"Bearer {ct_token}"},
        json={"claim_code": claim_code, "purchase_amount": 2000.0},
    )
    assert res1.status_code == 201

    # 2. Second redemption with different key -> 409 Conflict
    res2 = client.post(
        "/redemptions",
        headers={"Authorization": f"Bearer {ct_token}"},
        json={"claim_code": claim_code, "purchase_amount": 2000.0},
    )
    assert res2.status_code == 409
    assert "already been redeemed" in res2.json()["detail"].lower()

    # Points deducted only once (400 pts deducted from 5000 -> 4600)
    db = TestingSessionLocal()
    try:
        assert db.scalar(select(PointsAccount).where(PointsAccount.shop_id == data["shop"]["id"])).balance == 4600.0
        assert len(db.scalars(select(Redemption)).all()) == 1
    finally:
        db.close()


def test_cannot_redeem_expired_claim(client):
    """10. Expired claim cannot be redeemed."""
    data = setup_complete_flow(client, initial_points=5000.0)
    ct_token = data["ct_token"]
    claim_code = data["claim"]["code"]

    # Manually expire claim in DB
    db = TestingSessionLocal()
    try:
        c = db.scalar(select(Claim).where(Claim.code == claim_code))
        c.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
        db.commit()
    finally:
        db.close()

    res = client.post(
        "/redemptions",
        headers={"Authorization": f"Bearer {ct_token}"},
        json={"claim_code": claim_code, "purchase_amount": 2000.0},
    )
    assert res.status_code == 409
    assert "expired" in res.json()["detail"].lower()


# =====================================================================
# IDEMPOTENCY TESTS
# =====================================================================

def test_idempotent_retry_returns_same_response_without_duplicate_deduction(client):
    """26, 27. Exact retry with same Idempotency-Key returns cached response without deducting points again."""
    data = setup_complete_flow(client, initial_points=5000.0)
    ct_token = data["ct_token"]
    claim_code = data["claim"]["code"]
    idemp_key = "idemp-unique-12345"
    payload = {"claim_code": claim_code, "purchase_amount": 2000.0}

    # First attempt
    res1 = client.post(
        "/redemptions",
        headers={"Authorization": f"Bearer {ct_token}", "Idempotency-Key": idemp_key},
        json=payload,
    )
    assert res1.status_code == 201
    data1 = res1.json()

    # Second attempt with exact same key & payload
    res2 = client.post(
        "/redemptions",
        headers={"Authorization": f"Bearer {ct_token}", "Idempotency-Key": idemp_key},
        json=payload,
    )
    assert res2.status_code == 201
    data2 = res2.json()

    assert data1["id"] == data2["id"]
    assert data1["discount_amount"] == data2["discount_amount"]
    assert data1["remaining_points"] == data2["remaining_points"]

    # Verify points deducted only ONCE and only ONE redemption row
    db = TestingSessionLocal()
    try:
        assert db.scalar(select(PointsAccount).where(PointsAccount.shop_id == data["shop"]["id"])).balance == 4600.0
        assert len(db.scalars(select(Redemption)).all()) == 1
        red_txns = db.scalars(select(PointsTransaction).where(PointsTransaction.transaction_type == "redemption")).all()
        assert len(red_txns) == 1
    finally:
        db.close()


def test_idempotency_key_mismatched_payload_rejected(client):
    """28. Reusing same Idempotency-Key with different request returns 409 Conflict."""
    data = setup_complete_flow(client, initial_points=5000.0)
    ct_token = data["ct_token"]
    claim_code = data["claim"]["code"]
    idemp_key = "idemp-mismatch-key"

    # First request
    res1 = client.post(
        "/redemptions",
        headers={"Authorization": f"Bearer {ct_token}", "Idempotency-Key": idemp_key},
        json={"claim_code": claim_code, "purchase_amount": 2000.0},
    )
    assert res1.status_code == 201

    # Second request reusing same key with different amount
    res2 = client.post(
        "/redemptions",
        headers={"Authorization": f"Bearer {ct_token}", "Idempotency-Key": idemp_key},
        json={"claim_code": claim_code, "purchase_amount": 3500.0},
    )
    assert res2.status_code == 409
    assert "different request" in res2.json()["detail"].lower()


# =====================================================================
# SHOPKEEPER POINTS & REDEMPTION HISTORY TESTS
# =====================================================================

def test_shopkeeper_points_and_redemption_history(client):
    """31, 32, 33, 34. Shopkeeper points endpoints and history isolation."""
    data = setup_complete_flow(client, initial_points=5000.0)
    sk_token = data["sk_token"]
    ct_token = data["ct_token"]
    claim_code = data["claim"]["code"]

    # Shopkeeper checks points
    res_pts = client.get("/shops/me/points", headers={"Authorization": f"Bearer {sk_token}"})
    assert res_pts.status_code == 200
    assert res_pts.json()["balance"] == 5000.0

    # Counter redeems claim
    client.post(
        "/redemptions",
        headers={"Authorization": f"Bearer {ct_token}"},
        json={"claim_code": claim_code, "purchase_amount": 2000.0},
    )

    # Shopkeeper views redemptions
    res_reds = client.get("/shops/me/redemptions", headers={"Authorization": f"Bearer {sk_token}"})
    assert res_reds.status_code == 200
    reds = res_reds.json()
    assert len(reds) == 1
    assert reds[0]["claim_code"] == claim_code
    assert reds[0]["discount_amount"] == 400.0

    # Another shopkeeper checks their redemptions -> 0
    sk2_token = register_and_login(client, "sk2_reds@test.com", "shopkeeper")
    client.post("/shops", headers={"Authorization": f"Bearer {sk2_token}"}, json={"name": "S2", "address": "A2", "city": "C2"})
    res_reds2 = client.get("/shops/me/redemptions", headers={"Authorization": f"Bearer {sk2_token}"})
    assert res_reds2.status_code == 200
    assert len(res_reds2.json()) == 0


def test_counter_redemption_lookups(client):
    """25. Counter can retrieve redemption by ID or claim code."""
    data = setup_complete_flow(client, initial_points=5000.0)
    ct_token = data["ct_token"]
    claim_code = data["claim"]["code"]

    # Redeem
    res = client.post(
        "/redemptions",
        headers={"Authorization": f"Bearer {ct_token}"},
        json={"claim_code": claim_code, "purchase_amount": 2000.0},
    )
    red_id = res.json()["id"]

    # Lookup by ID
    get_id = client.get(f"/redemptions/{red_id}", headers={"Authorization": f"Bearer {ct_token}"})
    assert get_id.status_code == 200
    assert get_id.json()["claim_code"] == claim_code

    # Lookup by Claim Code
    get_code = client.get(f"/redemptions/code/{claim_code}", headers={"Authorization": f"Bearer {ct_token}"})
    assert get_code.status_code == 200
    assert get_code.json()["id"] == red_id
