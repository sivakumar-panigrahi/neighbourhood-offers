from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base, get_db
from app.main import app
from app.models.offer import Offer
from app.services.offer_parser import fallback_parser, parse_offer_text

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
# AUTHENTICATION & RBAC TESTS FOR PARSER
# =====================================================================

def test_shopkeeper_can_call_parse_endpoint(client):
    """1. Shopkeeper can access POST /offers/parse."""
    sk_token = register_and_login(client, "sk_parser@test.com", "shopkeeper")
    res = client.post(
        "/offers/parse",
        headers={"Authorization": f"Bearer {sk_token}"},
        json={"text": "flat 20% off all sarees till September 30, min bill 1500"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["original_text"] == "flat 20% off all sarees till September 30, min bill 1500"
    assert data["parsed"] is not None
    assert data["parsed"]["discount_type"] == "percentage"
    assert data["parsed"]["discount_value"] == 20.0
    assert data["parsed"]["minimum_purchase"] == 1500.0
    assert data["needs_confirmation"] is True
    assert data["parser_type"] in ["ai", "fallback"]


def test_shopper_cannot_call_parse_endpoint(client):
    """2. Shopper receives 403 Forbidden when calling POST /offers/parse."""
    sh_token = register_and_login(client, "shopper_parser@test.com", "shopper")
    res = client.post(
        "/offers/parse",
        headers={"Authorization": f"Bearer {sh_token}"},
        json={"text": "flat 20% off sarees"},
    )
    assert res.status_code == 403


def test_counter_cannot_call_parse_endpoint(client):
    """3. Counter staff receives 403 Forbidden when calling POST /offers/parse."""
    ct_token = register_and_login(client, "counter_parser@test.com", "counter")
    res = client.post(
        "/offers/parse",
        headers={"Authorization": f"Bearer {ct_token}"},
        json={"text": "flat 20% off sarees"},
    )
    assert res.status_code == 403


def test_unauthenticated_request_returns_401(client):
    """4. Unauthenticated request to /offers/parse returns 401 Unauthorized."""
    res = client.post(
        "/offers/parse",
        json={"text": "flat 20% off sarees"},
    )
    assert res.status_code == 401


# =====================================================================
# NATURAL-LANGUAGE PARSING UNIT / LOGIC TESTS
# =====================================================================

def test_percentage_discount_parsing():
    """5. '20% off' parses as percentage discount."""
    result = fallback_parser("flat 20% off all sarees")
    assert result.parsed is not None
    assert result.parsed.discount_type == "percentage"
    assert result.parsed.discount_value == 20.0
    assert result.parsed.conditions is not None
    assert "sarees" in result.parsed.conditions.lower()
    assert result.needs_confirmation is True


def test_fixed_discount_parsing():
    """6. '₹500 off' or '500 rupees discount' parses as fixed discount."""
    result1 = fallback_parser("Get ₹500 off on purchases above ₹3000 until September 30")
    assert result1.parsed is not None
    assert result1.parsed.discount_type == "fixed"
    assert result1.parsed.discount_value == 500.0
    assert result1.parsed.minimum_purchase == 3000.0

    result2 = fallback_parser("500 rupees discount on all shirts")
    assert result2.parsed is not None
    assert result2.parsed.discount_type == "fixed"
    assert result2.parsed.discount_value == 500.0


def test_minimum_purchase_extraction():
    """7. 'min bill 1500' and 'purchases above 2000' extract minimum_purchase."""
    res1 = fallback_parser("20% off on all items, min bill 1500")
    assert res1.parsed is not None
    assert res1.parsed.minimum_purchase == 1500.0

    res2 = fallback_parser("₹200 off on purchases above 2500")
    assert res2.parsed is not None
    assert res2.parsed.minimum_purchase == 2500.0


def test_combined_messy_input():
    """8. Combined messy natural language input parses all key fields."""
    text = "flat 20% off all sarees till September 30, min bill 1500"
    res = fallback_parser(text, current_time=datetime(2026, 9, 11, 10, 0, 0, tzinfo=timezone.utc))
    assert res.parsed is not None
    assert res.parsed.discount_type == "percentage"
    assert res.parsed.discount_value == 20.0
    assert res.parsed.minimum_purchase == 1500.0
    assert res.parsed.expires_at is not None
    assert res.parsed.expires_at.month == 9
    assert res.parsed.expires_at.day == 30
    assert res.needs_confirmation is True


def test_cultural_event_ambiguous_expiry_warning():
    """9 & 11. Ambiguous event dates (e.g., 'till Diwali') do not invent dates and add warning."""
    res = fallback_parser("flat 20% off all sarees till Diwali, min bill 1500")
    assert res.parsed is not None
    assert res.parsed.expires_at is None  # Must NOT invent date
    assert res.needs_confirmation is True
    assert any("diwali" in w.lower() or "expiry" in w.lower() for w in res.warnings)


def test_missing_expiry_date_generates_warning():
    """Missing expiry date generates warning and leaves expires_at as None."""
    res = fallback_parser("20 percent discount on shirts")
    assert res.parsed is not None
    assert res.parsed.discount_type == "percentage"
    assert res.parsed.discount_value == 20.0
    assert res.parsed.expires_at is None
    assert any("expiry" in w.lower() for w in res.warnings)


def test_invalid_percentage_warning():
    """10. Percentage exceeding 100 produces warning."""
    res = fallback_parser("150% off everything")
    assert any("cannot exceed 100" in w.lower() or "150" in w for w in res.warnings)


def test_unrecognizable_conversational_text():
    """Input with no offer information produces warning and parsed=None."""
    res = fallback_parser("hello how are you")
    assert res.parsed is None
    assert res.confidence == 0.0
    assert res.needs_confirmation is True
    assert any("could not identify" in w.lower() for w in res.warnings)


def test_weekday_relative_expiry():
    """'till Sunday' parses to upcoming Sunday."""
    fixed_now = datetime(2026, 9, 11, 10, 0, 0, tzinfo=timezone.utc)  # Friday
    res = fallback_parser("Buy any two shirts and get 20 percent discount till Sunday", current_time=fixed_now)
    assert res.parsed is not None
    assert res.parsed.expires_at is not None
    assert res.parsed.expires_at.weekday() == 6  # Sunday


# =====================================================================
# INTEGRATION: NO DB MUTATION & FULL WORKFLOW
# =====================================================================

def test_parser_does_not_create_database_row(client):
    """12 & 13. POST /offers/parse does NOT create an Offer database record."""
    sk_token = register_and_login(client, "sk_nodb@test.com", "shopkeeper")
    create_sample_shop(client, sk_token)

    # Call parse
    res = client.post(
        "/offers/parse",
        headers={"Authorization": f"Bearer {sk_token}"},
        json={"text": "flat 20% off all sarees till September 30, min bill 1500"},
    )
    assert res.status_code == 200

    # Query database to ensure no Offer rows were created
    db = TestingSessionLocal()
    try:
        offers = db.scalars(select(Offer)).all()
        assert len(offers) == 0
    finally:
        db.close()


def test_full_parse_and_confirm_lifecycle_workflow(client):
    """
    14. Full shopkeeper workflow:
    1. Parse text description -> gets structured draft suggestion
    2. Shopkeeper confirms/submits to POST /offers -> creates offer in 'draft' status
    3. Shopkeeper explicitly activates offer -> transitions to 'active' status
    """
    sk_token = register_and_login(client, "workflow_sk@test.com", "shopkeeper")
    shop = create_sample_shop(client, sk_token, "Workflow Store")

    # Step 1: Parse natural language
    parse_res = client.post(
        "/offers/parse",
        headers={"Authorization": f"Bearer {sk_token}"},
        json={"text": "flat 20% off all sarees till September 30, min bill 1500"},
    )
    assert parse_res.status_code == 200
    parsed = parse_res.json()["parsed"]
    assert parsed["discount_type"] == "percentage"
    assert parsed["discount_value"] == 20.0

    # Step 2: Shopkeeper confirms and creates offer via normal POST /offers
    create_payload = {
        "title": parsed["title"],
        "description": parsed["description"],
        "discount_type": parsed["discount_type"],
        "discount_value": parsed["discount_value"],
        "minimum_purchase": parsed["minimum_purchase"],
        "starts_at": parsed["starts_at"],
        "expires_at": parsed["expires_at"] or "2026-09-30T23:59:59Z",
    }
    create_res = client.post(
        "/offers",
        headers={"Authorization": f"Bearer {sk_token}"},
        json=create_payload,
    )
    assert create_res.status_code == 201
    offer_data = create_res.json()
    assert offer_data["status"] == "draft"
    assert offer_data["shop_id"] == shop["id"]
    offer_id = offer_data["id"]

    # Step 3: Shopkeeper explicitly activates offer
    activate_res = client.post(
        f"/offers/{offer_id}/activate",
        headers={"Authorization": f"Bearer {sk_token}"},
    )
    assert activate_res.status_code == 200
    assert activate_res.json()["status"] == "active"
