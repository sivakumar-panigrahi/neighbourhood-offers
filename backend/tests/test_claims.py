from datetime import datetime, timedelta, timezone
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
from app.services.claim_service import is_claim_expired, refresh_claim_status

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


def create_shopkeeper_with_offer(
    client: TestClient,
    email: str = "sk_claims@test.com",
    offer_status: str = "active",
    start_offset_hours: int = -1,
    expiry_offset_days: int = 5,
    title: str = "Special 20% Off",
) -> tuple[str, dict, dict]:
    """Helper to create a shopkeeper, their shop, and an offer."""
    sk_token = register_and_login(client, email, "shopkeeper")
    shop_res = client.post(
        "/shops",
        headers={"Authorization": f"Bearer {sk_token}"},
        json={
            "name": "Shop Fashion",
            "address": "123 Market Rd",
            "city": "Vijayawada",
            "latitude": 16.5062,
            "longitude": 80.6480,
        },
    )
    shop = shop_res.json()

    now = datetime.now(timezone.utc)
    starts_at = now + timedelta(hours=start_offset_hours)
    expires_at = now + timedelta(days=expiry_offset_days)

    offer_res = client.post(
        "/offers",
        headers={"Authorization": f"Bearer {sk_token}"},
        json={
            "title": title,
            "description": "Test offer description",
            "discount_type": "percentage",
            "discount_value": 20,
            "minimum_purchase": 1000,
            "starts_at": starts_at.isoformat(),
            "expires_at": expires_at.isoformat(),
        },
    )
    offer = offer_res.json()

    if offer_status == "active":
        act_res = client.post(f"/offers/{offer['id']}/activate", headers={"Authorization": f"Bearer {sk_token}"})
        offer = act_res.json()
    elif offer_status == "paused":
        client.post(f"/offers/{offer['id']}/activate", headers={"Authorization": f"Bearer {sk_token}"})
        pause_res = client.post(f"/offers/{offer['id']}/pause", headers={"Authorization": f"Bearer {sk_token}"})
        offer = pause_res.json()

    return sk_token, shop, offer


# =====================================================================
# SHOPPER OFFER BROWSING TESTS (GET /offers)
# =====================================================================

def test_shopper_can_browse_active_offers_only(client):
    """1, 2, 3, 4, 5. Shoppers see active offers, while draft/paused/expired/future offers are hidden."""
    sk_token = register_and_login(client, "sk_browse@test.com", "shopkeeper")
    client.post(
        "/shops",
        headers={"Authorization": f"Bearer {sk_token}"},
        json={"name": "S1", "address": "123 Main Rd", "city": "Vijayawada"},
    )

    now = datetime.now(timezone.utc)

    # 1. Active currently valid offer -> SHOULD BE VISIBLE
    res_act = client.post(
        "/offers",
        headers={"Authorization": f"Bearer {sk_token}"},
        json={
            "title": "Active Offer",
            "discount_type": "percentage",
            "discount_value": 15,
            "starts_at": (now - timedelta(hours=1)).isoformat(),
            "expires_at": (now + timedelta(days=3)).isoformat(),
        },
    ).json()
    client.post(f"/offers/{res_act['id']}/activate", headers={"Authorization": f"Bearer {sk_token}"})

    # 2. Draft offer -> HIDDEN
    client.post(
        "/offers",
        headers={"Authorization": f"Bearer {sk_token}"},
        json={
            "title": "Draft Offer",
            "discount_type": "fixed",
            "discount_value": 100,
            "starts_at": (now - timedelta(hours=1)).isoformat(),
            "expires_at": (now + timedelta(days=3)).isoformat(),
        },
    )

    # 3. Paused offer -> HIDDEN
    res_paused = client.post(
        "/offers",
        headers={"Authorization": f"Bearer {sk_token}"},
        json={
            "title": "Paused Offer",
            "discount_type": "percentage",
            "discount_value": 25,
            "starts_at": (now - timedelta(hours=1)).isoformat(),
            "expires_at": (now + timedelta(days=3)).isoformat(),
        },
    ).json()
    client.post(f"/offers/{res_paused['id']}/activate", headers={"Authorization": f"Bearer {sk_token}"})
    client.post(f"/offers/{res_paused['id']}/pause", headers={"Authorization": f"Bearer {sk_token}"})

    # 4. Expired offer -> HIDDEN
    client.post(
        "/offers",
        headers={"Authorization": f"Bearer {sk_token}"},
        json={
            "title": "Expired Offer",
            "discount_type": "fixed",
            "discount_value": 50,
            "starts_at": (now - timedelta(days=3)).isoformat(),
            "expires_at": (now - timedelta(days=1)).isoformat(),
        },
    )

    # 5. Future-start offer -> HIDDEN
    res_future = client.post(
        "/offers",
        headers={"Authorization": f"Bearer {sk_token}"},
        json={
            "title": "Future Offer",
            "discount_type": "percentage",
            "discount_value": 30,
            "starts_at": (now + timedelta(days=2)).isoformat(),
            "expires_at": (now + timedelta(days=5)).isoformat(),
        },
    ).json()
    client.post(f"/offers/{res_future['id']}/activate", headers={"Authorization": f"Bearer {sk_token}"})

    # Shopper browses /offers
    shopper_token = register_and_login(client, "shopper_browse@test.com", "shopper")
    browse_res = client.get("/offers", headers={"Authorization": f"Bearer {shopper_token}"})
    assert browse_res.status_code == 200
    offers = browse_res.json()

    # Must contain ONLY the 1 active valid offer
    assert len(offers) == 1
    assert offers[0]["title"] == "Active Offer"
    assert offers[0]["status"] == "active"
    # Ensure internal shopkeeper details like original_text are not leaked
    assert "original_text" not in offers[0]


def test_shopper_filtering_on_offers(client):
    """Test city, shop_id, and search filtering on GET /offers."""
    sk_token = register_and_login(client, "sk_filt@test.com", "shopkeeper")
    shop1 = client.post(
        "/shops",
        headers={"Authorization": f"Bearer {sk_token}"},
        json={"name": "Saree Palace", "address": "Market Street", "city": "Vijayawada"},
    ).json()

    now = datetime.now(timezone.utc)
    o1 = client.post(
        "/offers",
        headers={"Authorization": f"Bearer {sk_token}"},
        json={
            "title": "Silk Sarees 20% Off",
            "discount_type": "percentage",
            "discount_value": 20,
            "starts_at": (now - timedelta(hours=1)).isoformat(),
            "expires_at": (now + timedelta(days=5)).isoformat(),
        },
    ).json()
    client.post(f"/offers/{o1['id']}/activate", headers={"Authorization": f"Bearer {sk_token}"})

    shopper_token = register_and_login(client, "shopper_filt@test.com", "shopper")

    # City filter
    res_city = client.get("/offers?city=Vijayawada", headers={"Authorization": f"Bearer {shopper_token}"}).json()
    assert len(res_city) == 1
    res_diff_city = client.get("/offers?city=Hyderabad", headers={"Authorization": f"Bearer {shopper_token}"}).json()
    assert len(res_diff_city) == 0

    # Search filter
    res_search = client.get("/offers?search=Sarees", headers={"Authorization": f"Bearer {shopper_token}"}).json()
    assert len(res_search) == 1
    assert res_search[0]["id"] == o1["id"]


# =====================================================================
# CLAIM CREATION TESTS (POST /offers/{offer_id}/claim)
# =====================================================================

def test_shopper_can_claim_active_offer(client):
    """8, 9, 10, 11, 12, 13, 14. Shopper claims active offer and receives unique code."""
    _, _, offer = create_shopkeeper_with_offer(client, "sk_claim1@test.com", offer_status="active")
    shopper_token = register_and_login(client, "shopper_claim1@test.com", "shopper")

    res = client.post(
        f"/offers/{offer['id']}/claim",
        headers={"Authorization": f"Bearer {shopper_token}"},
    )
    assert res.status_code == 201
    claim = res.json()

    assert claim["status"] == "claimed"
    assert claim["offer_id"] == offer["id"]
    assert "code" in claim
    assert claim["code"].startswith("NO-")
    assert len(claim["code"]) >= 8
    assert str(claim["id"]) != claim["code"]  # Code is not the database ID

    # Expiry is bounded by offer expiry
    assert claim["expires_at"] == offer["expires_at"]


def test_non_shopper_cannot_claim_offer(client):
    """6, 7. Shopkeeper and counter staff cannot claim offers (403 Forbidden)."""
    sk_token, _, offer = create_shopkeeper_with_offer(client, "sk_claim2@test.com", offer_status="active")
    counter_token = register_and_login(client, "counter_claim@test.com", "counter")

    # Shopkeeper attempt
    res_sk = client.post(f"/offers/{offer['id']}/claim", headers={"Authorization": f"Bearer {sk_token}"})
    assert res_sk.status_code == 403

    # Counter staff attempt
    res_ct = client.post(f"/offers/{offer['id']}/claim", headers={"Authorization": f"Bearer {counter_token}"})
    assert res_ct.status_code == 403

    # Unauthenticated attempt
    res_unauth = client.post(f"/offers/{offer['id']}/claim")
    assert res_unauth.status_code == 401


def test_duplicate_active_claim_returns_409(client):
    """12. Shopper cannot have duplicate active claims for the same offer."""
    _, _, offer = create_shopkeeper_with_offer(client, "sk_dup@test.com", offer_status="active")
    shopper_token = register_and_login(client, "shopper_dup@test.com", "shopper")

    # First claim -> 201 Created
    res1 = client.post(f"/offers/{offer['id']}/claim", headers={"Authorization": f"Bearer {shopper_token}"})
    assert res1.status_code == 201

    # Second claim -> 409 Conflict
    res2 = client.post(f"/offers/{offer['id']}/claim", headers={"Authorization": f"Bearer {shopper_token}"})
    assert res2.status_code == 409
    assert "already claimed" in res2.json()["detail"].lower()


def test_cannot_claim_draft_paused_expired_or_future_offers(client):
    """15, 16, 17, 18. Invalid offer states return 409 Conflict."""
    shopper_token = register_and_login(client, "shopper_invalid_claims@test.com", "shopper")

    # 1. Draft Offer
    _, _, draft_offer = create_shopkeeper_with_offer(client, "sk_draft@test.com", offer_status="draft")
    res_draft = client.post(f"/offers/{draft_offer['id']}/claim", headers={"Authorization": f"Bearer {shopper_token}"})
    assert res_draft.status_code == 409

    # 2. Paused Offer
    _, _, paused_offer = create_shopkeeper_with_offer(client, "sk_paused@test.com", offer_status="paused")
    res_paused = client.post(f"/offers/{paused_offer['id']}/claim", headers={"Authorization": f"Bearer {shopper_token}"})
    assert res_paused.status_code == 409

    # 3. Expired Offer
    sk_token = register_and_login(client, "sk_exp@test.com", "shopkeeper")
    client.post(
        "/shops",
        headers={"Authorization": f"Bearer {sk_token}"},
        json={"name": "Exp Shop", "address": "Market Road", "city": "Vijayawada"},
    )
    now = datetime.now(timezone.utc)
    exp_offer = client.post(
        "/offers",
        headers={"Authorization": f"Bearer {sk_token}"},
        json={
            "title": "Old Offer",
            "discount_type": "fixed",
            "discount_value": 50,
            "starts_at": (now - timedelta(days=5)).isoformat(),
            "expires_at": (now - timedelta(days=1)).isoformat(),
        },
    ).json()
    res_exp = client.post(f"/offers/{exp_offer['id']}/claim", headers={"Authorization": f"Bearer {shopper_token}"})
    assert res_exp.status_code == 409

    # 4. Future Offer
    fut_offer = client.post(
        "/offers",
        headers={"Authorization": f"Bearer {sk_token}"},
        json={
            "title": "Future Offer",
            "discount_type": "fixed",
            "discount_value": 50,
            "starts_at": (now + timedelta(days=2)).isoformat(),
            "expires_at": (now + timedelta(days=5)).isoformat(),
        },
    ).json()
    client.post(f"/offers/{fut_offer['id']}/activate", headers={"Authorization": f"Bearer {sk_token}"})
    res_fut = client.post(f"/offers/{fut_offer['id']}/claim", headers={"Authorization": f"Bearer {shopper_token}"})
    assert res_fut.status_code == 409


def test_claim_creation_does_not_mutate_points_or_redemptions(client):
    """19. Claiming an offer must NOT deduct points, create redemptions, or ledger records."""
    _, _, offer = create_shopkeeper_with_offer(client, "sk_nomut@test.com", offer_status="active")
    shopper_token = register_and_login(client, "shopper_nomut@test.com", "shopper")

    # Claim
    res = client.post(f"/offers/{offer['id']}/claim", headers={"Authorization": f"Bearer {shopper_token}"})
    assert res.status_code == 201

    # Verify directly in DB
    db = TestingSessionLocal()
    try:
        redemptions = db.scalars(select(Redemption)).all()
        assert len(redemptions) == 0, "Claim creation must not create a Redemption"

        transactions = db.scalars(select(PointsTransaction)).all()
        assert len(transactions) == 0, "Claim creation must not create PointsTransaction"
    finally:
        db.close()


# =====================================================================
# CLAIMS RETRIEVAL & ISOLATION TESTS (GET /claims/my, GET /claims/{id})
# =====================================================================

def test_shopper_can_view_own_claims_and_isolation(client):
    """9, 10, 11. Shopper can view own claims, but cannot view another shopper's claim (403)."""
    _, _, offer = create_shopkeeper_with_offer(client, "sk_iso@test.com", offer_status="active")

    # Shopper 1
    sh1_token = register_and_login(client, "shopper1@test.com", "shopper")
    claim1 = client.post(f"/offers/{offer['id']}/claim", headers={"Authorization": f"Bearer {sh1_token}"}).json()

    # Shopper 2
    sh2_token = register_and_login(client, "shopper2@test.com", "shopper")

    # Shopper 1 lists claims -> contains claim1
    sh1_claims = client.get("/claims/my", headers={"Authorization": f"Bearer {sh1_token}"}).json()
    assert len(sh1_claims) == 1
    assert sh1_claims[0]["id"] == claim1["id"]

    # Shopper 2 lists claims -> empty
    sh2_claims = client.get("/claims/my", headers={"Authorization": f"Bearer {sh2_token}"}).json()
    assert len(sh2_claims) == 0

    # Shopper 1 views single claim -> 200 OK
    res_sh1_view = client.get(f"/claims/{claim1['id']}", headers={"Authorization": f"Bearer {sh1_token}"})
    assert res_sh1_view.status_code == 200
    assert res_sh1_view.json()["code"] == claim1["code"]

    # Shopper 2 attempts to view Shopper 1's claim -> 403 Forbidden
    res_sh2_view = client.get(f"/claims/{claim1['id']}", headers={"Authorization": f"Bearer {sh2_token}"})
    assert res_sh2_view.status_code == 403


def test_claim_expiration_evaluation():
    """14. Test claim expiration helper functions."""
    now = datetime.now(timezone.utc)

    # Active non-expired claim
    c_active = Claim(
        offer_id=1,
        shopper_id=1,
        code="NO-123456",
        status="claimed",
        claimed_at=now - timedelta(hours=1),
        expires_at=now + timedelta(hours=2),
    )
    assert is_claim_expired(c_active, now) is False

    # Expired claim
    c_expired = Claim(
        offer_id=1,
        shopper_id=1,
        code="NO-654321",
        status="claimed",
        claimed_at=now - timedelta(days=2),
        expires_at=now - timedelta(days=1),
    )
    assert is_claim_expired(c_expired, now) is True

    # Refresh claim status
    refresh_claim_status(c_expired, now=now)
    assert c_expired.status == "expired"
