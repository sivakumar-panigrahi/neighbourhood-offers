from datetime import datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base, get_db
from app.main import app
from app.models.offer import Offer
from app.services.offer_service import (
    is_offer_active_and_claimable,
    is_offer_expired,
    refresh_offer_status,
)

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


def create_sample_shop(client: TestClient, token: str, name: str = "Test Shop") -> dict:
    """Helper to create a shop for a shopkeeper."""
    res = client.post(
        "/shops",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": name,
            "address": "123 Main St",
            "city": "Vijayawada",
            "latitude": 16.5062,
            "longitude": 80.6480,
        },
    )
    return res.json()


# =====================================================================
# SHOP MANAGEMENT TESTS
# =====================================================================

def test_shopkeeper_create_and_get_shop(client):
    """1 & 2. Shopkeeper can create and retrieve own shop."""
    sk_token = register_and_login(client, "rahul@test.com", "shopkeeper")

    # Create shop
    res = client.post(
        "/shops",
        headers={"Authorization": f"Bearer {sk_token}"},
        json={
            "name": "Rahul Fashion Store",
            "address": "MG Road",
            "city": "Vijayawada",
            "latitude": 16.5062,
            "longitude": 80.6480,
        },
    )
    assert res.status_code == 201
    shop_data = res.json()
    assert shop_data["name"] == "Rahul Fashion Store"
    assert shop_data["city"] == "Vijayawada"
    assert "id" in shop_data

    # Retrieve own shop
    get_res = client.get("/shops/me", headers={"Authorization": f"Bearer {sk_token}"})
    assert get_res.status_code == 200
    assert get_res.json()["name"] == "Rahul Fashion Store"


def test_duplicate_shop_creation_fails(client):
    """Duplicate shop creation by same shopkeeper returns 409 Conflict."""
    sk_token = register_and_login(client, "sk_dup@test.com", "shopkeeper")
    create_sample_shop(client, sk_token, "Shop 1")

    # Second creation attempt
    res = client.post(
        "/shops",
        headers={"Authorization": f"Bearer {sk_token}"},
        json={"name": "Shop 2", "address": "Road 2", "city": "City 2"},
    )
    assert res.status_code == 409
    assert "already owns a shop" in res.json()["detail"].lower()


def test_non_shopkeeper_cannot_create_or_get_shop(client):
    """3 & 4. Shopper and Counter cannot create or retrieve shop."""
    sh_token = register_and_login(client, "shopper@test.com", "shopper")
    ct_token = register_and_login(client, "counter@test.com", "counter")

    # Shopper attempt
    res_sh = client.post(
        "/shops",
        headers={"Authorization": f"Bearer {sh_token}"},
        json={"name": "Shopper Shop", "address": "Addr", "city": "City"},
    )
    assert res_sh.status_code == 403

    # Counter attempt
    res_ct = client.post(
        "/shops",
        headers={"Authorization": f"Bearer {ct_token}"},
        json={"name": "Counter Shop", "address": "Addr", "city": "City"},
    )
    assert res_ct.status_code == 403


# =====================================================================
# OFFER CREATION & VALIDATION TESTS
# =====================================================================

def test_shopkeeper_create_offer_defaults_to_draft(client):
    """5 & 8. Shopkeeper creates offer and it defaults to 'draft' status."""
    sk_token = register_and_login(client, "rahul2@test.com", "shopkeeper")
    create_sample_shop(client, sk_token, "Rahul Store")

    now = datetime.now(timezone.utc)
    res = client.post(
        "/offers",
        headers={"Authorization": f"Bearer {sk_token}"},
        json={
            "title": "20% Off Sarees",
            "description": "Flat 20% off on selected sarees",
            "discount_type": "percentage",
            "discount_value": 20,
            "minimum_purchase": 1500,
            "starts_at": (now - timedelta(hours=1)).isoformat(),
            "expires_at": (now + timedelta(days=7)).isoformat(),
        },
    )
    assert res.status_code == 201
    offer_data = res.json()
    assert offer_data["title"] == "20% Off Sarees"
    assert offer_data["status"] == "draft"
    assert offer_data["discount_type"] == "percentage"
    assert offer_data["discount_value"] == 20


def test_offer_creation_without_shop_fails(client):
    """Shopkeeper cannot create offer before creating a shop."""
    sk_token = register_and_login(client, "sk_noshop@test.com", "shopkeeper")
    now = datetime.now(timezone.utc)

    res = client.post(
        "/offers",
        headers={"Authorization": f"Bearer {sk_token}"},
        json={
            "title": "50% Off",
            "discount_type": "percentage",
            "discount_value": 50,
            "starts_at": now.isoformat(),
            "expires_at": (now + timedelta(days=5)).isoformat(),
        },
    )
    assert res.status_code == 400
    assert "must create a shop first" in res.json()["detail"].lower()


def test_shopper_and_counter_cannot_create_offer(client):
    """6 & 7. Shopper and Counter cannot create offers."""
    sh_token = register_and_login(client, "shopper_no_offer@test.com", "shopper")
    ct_token = register_and_login(client, "counter_no_offer@test.com", "counter")
    now = datetime.now(timezone.utc)

    payload = {
        "title": "Promo",
        "discount_type": "fixed",
        "discount_value": 100,
        "starts_at": now.isoformat(),
        "expires_at": (now + timedelta(days=1)).isoformat(),
    }

    assert client.post("/offers", headers={"Authorization": f"Bearer {sh_token}"}, json=payload).status_code == 403
    assert client.post("/offers", headers={"Authorization": f"Bearer {ct_token}"}, json=payload).status_code == 403


def test_offer_validation_errors(client):
    """9, 10, 11, 12, 13. Test all invalid inputs are rejected with 422."""
    sk_token = register_and_login(client, "sk_val@test.com", "shopkeeper")
    create_sample_shop(client, sk_token)
    now = datetime.now(timezone.utc)

    # 9. percentage > 100
    res = client.post(
        "/offers",
        headers={"Authorization": f"Bearer {sk_token}"},
        json={
            "title": "Invalid %",
            "discount_type": "percentage",
            "discount_value": 150,
            "starts_at": now.isoformat(),
            "expires_at": (now + timedelta(days=2)).isoformat(),
        },
    )
    assert res.status_code == 422

    # 10. percentage <= 0
    res = client.post(
        "/offers",
        headers={"Authorization": f"Bearer {sk_token}"},
        json={
            "title": "Invalid %",
            "discount_type": "percentage",
            "discount_value": 0,
            "starts_at": now.isoformat(),
            "expires_at": (now + timedelta(days=2)).isoformat(),
        },
    )
    assert res.status_code == 422

    # 11. fixed <= 0
    res = client.post(
        "/offers",
        headers={"Authorization": f"Bearer {sk_token}"},
        json={
            "title": "Invalid Fixed",
            "discount_type": "fixed",
            "discount_value": -10,
            "starts_at": now.isoformat(),
            "expires_at": (now + timedelta(days=2)).isoformat(),
        },
    )
    assert res.status_code == 422

    # 12. minimum_purchase < 0
    res = client.post(
        "/offers",
        headers={"Authorization": f"Bearer {sk_token}"},
        json={
            "title": "Invalid Min",
            "discount_type": "fixed",
            "discount_value": 50,
            "minimum_purchase": -50,
            "starts_at": now.isoformat(),
            "expires_at": (now + timedelta(days=2)).isoformat(),
        },
    )
    assert res.status_code == 422

    # 13. expires_at <= starts_at
    res = client.post(
        "/offers",
        headers={"Authorization": f"Bearer {sk_token}"},
        json={
            "title": "Invalid Dates",
            "discount_type": "fixed",
            "discount_value": 50,
            "starts_at": (now + timedelta(days=5)).isoformat(),
            "expires_at": (now + timedelta(days=2)).isoformat(),
        },
    )
    assert res.status_code == 422


# =====================================================================
# OWNERSHIP & ACCESS BOUNDARY TESTS (CRITICAL)
# =====================================================================

def test_shopkeeper_ownership_boundaries(client):
    """14, 15, 16, 17, 32. Rahul cannot view, update, activate, or pause Anitha's offer."""
    # Rahul setup
    rahul_token = register_and_login(client, "rahul@test.com", "shopkeeper")
    create_sample_shop(client, rahul_token, "Rahul Shop")
    now = datetime.now(timezone.utc)
    rahul_offer = client.post(
        "/offers",
        headers={"Authorization": f"Bearer {rahul_token}"},
        json={
            "title": "Rahul Offer",
            "discount_type": "fixed",
            "discount_value": 50,
            "starts_at": now.isoformat(),
            "expires_at": (now + timedelta(days=3)).isoformat(),
        },
    ).json()

    # Anitha setup
    anitha_token = register_and_login(client, "anitha@test.com", "shopkeeper")
    create_sample_shop(client, anitha_token, "Anitha Shop")
    anitha_offer = client.post(
        "/offers",
        headers={"Authorization": f"Bearer {anitha_token}"},
        json={
            "title": "Anitha Offer",
            "discount_type": "percentage",
            "discount_value": 30,
            "starts_at": now.isoformat(),
            "expires_at": (now + timedelta(days=3)).isoformat(),
        },
    ).json()

    # 14. Rahul lists own offers -> contains Rahul Offer, NOT Anitha Offer
    rahul_offers = client.get("/offers/my", headers={"Authorization": f"Bearer {rahul_token}"}).json()
    assert len(rahul_offers) == 1
    assert rahul_offers[0]["id"] == rahul_offer["id"]

    # 15. Rahul attempts to view Anitha's offer -> 403 Forbidden
    res_view = client.get(f"/offers/{anitha_offer['id']}", headers={"Authorization": f"Bearer {rahul_token}"})
    assert res_view.status_code == 403

    # 16. Rahul can update own offer -> 200 OK
    res_update_own = client.put(
        f"/offers/{rahul_offer['id']}",
        headers={"Authorization": f"Bearer {rahul_token}"},
        json={"title": "Rahul Offer Updated", "discount_type": "fixed", "discount_value": 75},
    )
    assert res_update_own.status_code == 200
    assert res_update_own.json()["title"] == "Rahul Offer Updated"

    # 17. Rahul attempts to update Anitha's offer -> 403 Forbidden
    res_update_other = client.put(
        f"/offers/{anitha_offer['id']}",
        headers={"Authorization": f"Bearer {rahul_token}"},
        json={"title": "Hacked Offer"},
    )
    assert res_update_other.status_code == 403

    # Rahul attempts to activate Anitha's offer -> 403 Forbidden
    res_act_other = client.post(
        f"/offers/{anitha_offer['id']}/activate",
        headers={"Authorization": f"Bearer {rahul_token}"},
    )
    assert res_act_other.status_code == 403

    # Rahul attempts to pause Anitha's offer -> 403 Forbidden
    res_pause_other = client.post(
        f"/offers/{anitha_offer['id']}/pause",
        headers={"Authorization": f"Bearer {rahul_token}"},
    )
    assert res_pause_other.status_code == 403


# =====================================================================
# OFFER LIFECYCLE TESTS (draft -> active -> paused -> active -> expired)
# =====================================================================

def test_offer_lifecycle_transitions(client):
    """18, 22, 24. Test valid lifecycle transitions (draft -> active -> paused -> active)."""
    sk_token = register_and_login(client, "lifecycle_sk@test.com", "shopkeeper")
    create_sample_shop(client, sk_token)
    now = datetime.now(timezone.utc)

    # 1. Create -> draft
    offer = client.post(
        "/offers",
        headers={"Authorization": f"Bearer {sk_token}"},
        json={
            "title": "Lifecycle Test",
            "discount_type": "percentage",
            "discount_value": 25,
            "starts_at": (now - timedelta(minutes=5)).isoformat(),
            "expires_at": (now + timedelta(days=2)).isoformat(),
        },
    ).json()
    assert offer["status"] == "draft"

    # 2. Activate: draft -> active
    res_act = client.post(f"/offers/{offer['id']}/activate", headers={"Authorization": f"Bearer {sk_token}"})
    assert res_act.status_code == 200
    assert res_act.json()["status"] == "active"

    # 3. Pause: active -> paused
    res_pause = client.post(f"/offers/{offer['id']}/pause", headers={"Authorization": f"Bearer {sk_token}"})
    assert res_pause.status_code == 200
    assert res_pause.json()["status"] == "paused"

    # 4. Resume: paused -> active
    res_resume = client.post(f"/offers/{offer['id']}/resume", headers={"Authorization": f"Bearer {sk_token}"})
    assert res_resume.status_code == 200
    assert res_resume.json()["status"] == "active"


def test_expired_offer_cannot_be_activated_or_resumed(client):
    """21, 25. Expired offers cannot be activated or resumed."""
    sk_token = register_and_login(client, "expired_test@test.com", "shopkeeper")
    create_sample_shop(client, sk_token)
    now = datetime.now(timezone.utc)

    # Offer created with an expiry in the past (using direct service or direct test)
    # Since API rejects expires_at <= starts_at, let's create a past window (starts -2 days, expires -1 day)
    res = client.post(
        "/offers",
        headers={"Authorization": f"Bearer {sk_token}"},
        json={
            "title": "Already Expired Offer",
            "discount_type": "fixed",
            "discount_value": 20,
            "starts_at": (now - timedelta(days=2)).isoformat(),
            "expires_at": (now - timedelta(days=1)).isoformat(),
        },
    )
    assert res.status_code == 201
    offer_id = res.json()["id"]

    # Attempt to activate expired offer -> 400 Bad Request
    res_act = client.post(f"/offers/{offer_id}/activate", headers={"Authorization": f"Bearer {sk_token}"})
    assert res_act.status_code == 400
    assert "expired" in res_act.json()["detail"].lower()

    # Attempt to resume expired offer -> 400 Bad Request
    res_res = client.post(f"/offers/{offer_id}/resume", headers={"Authorization": f"Bearer {sk_token}"})
    assert res_res.status_code == 400
    assert "expired" in res_res.json()["detail"].lower()


def test_invalid_lifecycle_transitions(client):
    """Test invalid transitions (e.g. pausing a draft offer)."""
    sk_token = register_and_login(client, "invalid_trans@test.com", "shopkeeper")
    create_sample_shop(client, sk_token)
    now = datetime.now(timezone.utc)

    offer = client.post(
        "/offers",
        headers={"Authorization": f"Bearer {sk_token}"},
        json={
            "title": "Draft Offer",
            "discount_type": "fixed",
            "discount_value": 10,
            "starts_at": now.isoformat(),
            "expires_at": (now + timedelta(days=1)).isoformat(),
        },
    ).json()

    # Attempt to pause draft offer -> 400
    res_pause = client.post(f"/offers/{offer['id']}/pause", headers={"Authorization": f"Bearer {sk_token}"})
    assert res_pause.status_code == 400

    # Attempt to resume draft offer -> 400
    res_resume = client.post(f"/offers/{offer['id']}/resume", headers={"Authorization": f"Bearer {sk_token}"})
    assert res_resume.status_code == 400


def test_shopper_and_counter_cannot_transition_offers(client):
    """19, 20, 23. Shopper and Counter cannot activate or pause offers."""
    sk_token = register_and_login(client, "sk_trans@test.com", "shopkeeper")
    create_sample_shop(client, sk_token)
    now = datetime.now(timezone.utc)

    offer = client.post(
        "/offers",
        headers={"Authorization": f"Bearer {sk_token}"},
        json={
            "title": "Offer",
            "discount_type": "fixed",
            "discount_value": 10,
            "starts_at": now.isoformat(),
            "expires_at": (now + timedelta(days=1)).isoformat(),
        },
    ).json()

    sh_token = register_and_login(client, "sh_trans@test.com", "shopper")
    ct_token = register_and_login(client, "ct_trans@test.com", "counter")

    # Shopper activate attempt -> 403
    assert client.post(f"/offers/{offer['id']}/activate", headers={"Authorization": f"Bearer {sh_token}"}).status_code == 403
    # Counter activate attempt -> 403
    assert client.post(f"/offers/{offer['id']}/activate", headers={"Authorization": f"Bearer {ct_token}"}).status_code == 403
    # Shopper pause attempt -> 403
    assert client.post(f"/offers/{offer['id']}/pause", headers={"Authorization": f"Bearer {sh_token}"}).status_code == 403
    # Counter pause attempt -> 403
    assert client.post(f"/offers/{offer['id']}/pause", headers={"Authorization": f"Bearer {ct_token}"}).status_code == 403


# =====================================================================
# CLAIMABILITY & EXPIRATION HELPER UNIT TESTS
# =====================================================================

def test_claimability_and_expiration_rules():
    """26, 27, 28. Comprehensive claimability helper tests."""
    now = datetime.now(timezone.utc)

    # Offer A: Active, currently valid -> CLAIMABLE
    offer_a = Offer(
        shop_id=1,
        title="Offer A",
        discount_type="percentage",
        discount_value=20,
        starts_at=now - timedelta(hours=1),
        expires_at=now + timedelta(hours=1),
        status="active",
    )
    assert is_offer_active_and_claimable(offer_a, now) is True
    assert is_offer_expired(offer_a, now) is False

    # Offer B: Active, future-start -> NOT claimable
    offer_b = Offer(
        shop_id=1,
        title="Offer B",
        discount_type="percentage",
        discount_value=20,
        starts_at=now + timedelta(hours=1),
        expires_at=now + timedelta(hours=2),
        status="active",
    )
    assert is_offer_active_and_claimable(offer_b, now) is False
    assert is_offer_expired(offer_b, now) is False

    # Offer C: Active, expired date -> NOT claimable, is_offer_expired is True
    offer_c = Offer(
        shop_id=1,
        title="Offer C",
        discount_type="percentage",
        discount_value=20,
        starts_at=now - timedelta(hours=2),
        expires_at=now - timedelta(hours=1),
        status="active",
    )
    assert is_offer_active_and_claimable(offer_c, now) is False
    assert is_offer_expired(offer_c, now) is True

    # Offer D: Paused with valid dates -> NOT claimable
    offer_d = Offer(
        shop_id=1,
        title="Offer D",
        discount_type="percentage",
        discount_value=20,
        starts_at=now - timedelta(hours=1),
        expires_at=now + timedelta(hours=1),
        status="paused",
    )
    assert is_offer_active_and_claimable(offer_d, now) is False

    # Offer E: Draft with valid dates -> NOT claimable
    offer_e = Offer(
        shop_id=1,
        title="Offer E",
        discount_type="percentage",
        discount_value=20,
        starts_at=now - timedelta(hours=1),
        expires_at=now + timedelta(hours=1),
        status="draft",
    )
    assert is_offer_active_and_claimable(offer_e, now) is False


def test_missing_offer_returns_404(client):
    """31. Accessing non-existent offer returns 404."""
    sk_token = register_and_login(client, "sk_404@test.com", "shopkeeper")
    res = client.get("/offers/999999", headers={"Authorization": f"Bearer {sk_token}"})
    assert res.status_code == 404


def test_unauthenticated_requests_return_401(client):
    """29. Unauthenticated requests return 401."""
    assert client.get("/shops/me").status_code == 401
    assert client.post("/shops", json={}).status_code == 401
    assert client.get("/offers/my").status_code == 401
    assert client.post("/offers", json={}).status_code == 401
