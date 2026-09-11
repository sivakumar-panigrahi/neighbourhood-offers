import pytest
from datetime import timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import (
    create_access_token,
    get_password_hash,
    verify_password,
)
from app.db.database import Base, get_db
from app.main import app
from app.models.user import User

# In-memory database for isolated authentication tests
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
    """Create all tables before each test and drop them after."""
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def client():
    """FastAPI TestClient with overridden get_db dependency."""
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


def test_password_security():
    """Verify password hashing and verification functions."""
    raw_pwd = "superSecretPassword123"
    hashed = get_password_hash(raw_pwd)

    assert hashed != raw_pwd
    assert verify_password(raw_pwd, hashed) is True
    assert verify_password("wrongPassword", hashed) is False


def test_user_registration_success(client):
    """1. Registration succeeds and returns safe user data without password hash."""
    response = client.post(
        "/auth/register",
        json={
            "email": "shopper@test.com",
            "password": "password123",
            "role": "shopper",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "shopper@test.com"
    assert data["role"] == "shopper"
    assert "id" in data
    assert "hashed_password" not in data
    assert "password" not in data


def test_duplicate_registration_fails(client):
    """2. Duplicate registration with same email returns HTTP 409 Conflict."""
    payload = {
        "email": "duplicate@test.com",
        "password": "password123",
        "role": "shopper",
    }
    res1 = client.post("/auth/register", json=payload)
    assert res1.status_code == 201

    res2 = client.post("/auth/register", json=payload)
    assert res2.status_code == 409
    assert "already registered" in res2.json()["detail"].lower()


def test_login_success(client):
    """3. Login succeeds with correct credentials and returns JWT Bearer token."""
    client.post(
        "/auth/register",
        json={
            "email": "login_test@example.com",
            "password": "mySecurePassword",
            "role": "shopkeeper",
        },
    )

    response = client.post(
        "/auth/login",
        data={
            "username": "login_test@example.com",
            "password": "mySecurePassword",
        },
    )
    assert response.status_code == 200
    token_data = response.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"


def test_login_wrong_password_fails(client):
    """4. Login fails with incorrect password returning HTTP 401 Unauthorized."""
    client.post(
        "/auth/register",
        json={
            "email": "user@example.com",
            "password": "correctPassword",
            "role": "shopper",
        },
    )

    response = client.post(
        "/auth/login",
        data={
            "username": "user@example.com",
            "password": "incorrectPassword",
        },
    )
    assert response.status_code == 401
    assert "incorrect" in response.json()["detail"].lower()


def test_login_nonexistent_user_fails(client):
    """5. Login fails for non-existent email returning generic HTTP 401."""
    response = client.post(
        "/auth/login",
        data={
            "username": "doesnotexist@example.com",
            "password": "anyPassword123",
        },
    )
    assert response.status_code == 401
    assert "incorrect" in response.json()["detail"].lower()


def test_get_me_with_valid_token(client):
    """6. GET /auth/me returns current user info with valid Bearer token."""
    client.post(
        "/auth/register",
        json={
            "email": "rahul@example.com",
            "password": "securepassword",
            "role": "shopkeeper",
        },
    )
    login_res = client.post(
        "/auth/login",
        data={"username": "rahul@example.com", "password": "securepassword"},
    )
    token = login_res.json()["access_token"]

    response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    user_data = response.json()
    assert user_data["email"] == "rahul@example.com"
    assert user_data["role"] == "shopkeeper"
    assert "hashed_password" not in user_data


def test_get_me_unauthenticated_fails(client):
    """7. GET /auth/me fails without token returning HTTP 401."""
    response = client.get("/auth/me")
    assert response.status_code == 401


def test_get_me_invalid_token_fails(client):
    """8. GET /auth/me fails with invalid/tampered token returning HTTP 401."""
    response = client.get(
        "/auth/me",
        headers={"Authorization": "Bearer invalid.tampered.token"},
    )
    assert response.status_code == 401


def test_get_me_expired_token_fails(client):
    """9. GET /auth/me fails with expired token returning HTTP 401."""
    expired_token = create_access_token(
        data={"sub": "1", "role": "shopper"},
        expires_delta=timedelta(seconds=-10),
    )
    response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert response.status_code == 401


def test_rbac_shopkeeper_access(client):
    """10. Shopkeeper role access: Shopkeeper allowed (200), Shopper & Counter forbidden (403)."""
    # Create shopkeeper
    reg_sk = client.post("/auth/register", json={"email": "sk@test.com", "password": "password123", "role": "shopkeeper"})
    assert reg_sk.status_code == 201
    sk_token = client.post("/auth/login", data={"username": "sk@test.com", "password": "password123"}).json()["access_token"]

    # Create shopper
    reg_sh = client.post("/auth/register", json={"email": "sh@test.com", "password": "password123", "role": "shopper"})
    assert reg_sh.status_code == 201
    sh_token = client.post("/auth/login", data={"username": "sh@test.com", "password": "password123"}).json()["access_token"]

    # Create counter
    reg_ct = client.post("/auth/register", json={"email": "ct@test.com", "password": "password123", "role": "counter"})
    assert reg_ct.status_code == 201
    ct_token = client.post("/auth/login", data={"username": "ct@test.com", "password": "password123"}).json()["access_token"]

    # Shopkeeper accesses shopkeeper test route -> 200
    res_sk = client.get("/auth/test/shopkeeper", headers={"Authorization": f"Bearer {sk_token}"})
    assert res_sk.status_code == 200
    assert res_sk.json()["role"] == "shopkeeper"

    # Shopper accesses shopkeeper test route -> 403
    res_sh = client.get("/auth/test/shopkeeper", headers={"Authorization": f"Bearer {sh_token}"})
    assert res_sh.status_code == 403

    # Counter accesses shopkeeper test route -> 403
    res_ct = client.get("/auth/test/shopkeeper", headers={"Authorization": f"Bearer {ct_token}"})
    assert res_ct.status_code == 403


def test_rbac_shopper_access(client):
    """11. Shopper role access: Shopper allowed (200), Shopkeeper & Counter forbidden (403)."""
    client.post("/auth/register", json={"email": "shopper2@test.com", "password": "password123", "role": "shopper"})
    sh_token = client.post("/auth/login", data={"username": "shopper2@test.com", "password": "password123"}).json()["access_token"]

    client.post("/auth/register", json={"email": "shopkeeper2@test.com", "password": "password123", "role": "shopkeeper"})
    sk_token = client.post("/auth/login", data={"username": "shopkeeper2@test.com", "password": "password123"}).json()["access_token"]

    res_sh = client.get("/auth/test/shopper", headers={"Authorization": f"Bearer {sh_token}"})
    assert res_sh.status_code == 200

    res_sk = client.get("/auth/test/shopper", headers={"Authorization": f"Bearer {sk_token}"})
    assert res_sk.status_code == 403


def test_rbac_counter_access(client):
    """12. Counter role access: Counter allowed (200), Shopper & Shopkeeper forbidden (403)."""
    client.post("/auth/register", json={"email": "counter2@test.com", "password": "password123", "role": "counter"})
    ct_token = client.post("/auth/login", data={"username": "counter2@test.com", "password": "password123"}).json()["access_token"]

    client.post("/auth/register", json={"email": "shopper3@test.com", "password": "password123", "role": "shopper"})
    sh_token = client.post("/auth/login", data={"username": "shopper3@test.com", "password": "password123"}).json()["access_token"]

    res_ct = client.get("/auth/test/counter", headers={"Authorization": f"Bearer {ct_token}"})
    assert res_ct.status_code == 200

    res_sh = client.get("/auth/test/counter", headers={"Authorization": f"Bearer {sh_token}"})
    assert res_sh.status_code == 403
