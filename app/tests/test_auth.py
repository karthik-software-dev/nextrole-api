import pytest
from fastapi.testclient import TestClient

from config import ADMIN_EMAIL, ADMIN_INITIAL_PASSWORD
from core.security import hash_password
from server import app
from storage.database import get_db
from storage.models import User

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_admin_user():
    """Ensures test admin user is available with expected hashed credentials."""
    with get_db() as session:
        user = session.query(User).filter(User.email == ADMIN_EMAIL).first()
        if not user:
            user = User(
                name="Rahul Karthik",
                email=ADMIN_EMAIL,
                target_role="Senior Python Backend Engineer",
                hashed_password=hash_password(ADMIN_INITIAL_PASSWORD),
                is_active=True,
            )
            session.add(user)
        else:
            user.hashed_password = hash_password(ADMIN_INITIAL_PASSWORD)
            user.is_active = True
        session.commit()
    yield


def test_login_successful():
    response = client.post(
        "/api/v1/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_INITIAL_PASSWORD},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == ADMIN_EMAIL


def test_login_invalid_password():
    response = client.post(
        "/api/v1/auth/login",
        json={"email": ADMIN_EMAIL, "password": "wrong_password_123"},
    )
    assert response.status_code == 401
    assert "Invalid email or password" in response.json()["detail"]


def test_login_unknown_user():
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "nonexistent_user@example.com", "password": "any_password"},
    )
    assert response.status_code == 401
    assert "Invalid email or password" in response.json()["detail"]


def test_auth_me_with_token():
    # Login first
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_INITIAL_PASSWORD},
    )
    token = login_res.json()["access_token"]

    # Request /me
    me_res = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_res.status_code == 200
    assert me_res.json()["email"] == ADMIN_EMAIL


def test_auth_me_unauthorized():
    # No auth header
    res = client.get("/api/v1/auth/me")
    assert res.status_code == 401

    # Bad token
    bad_res = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid_garbage_token"},
    )
    assert bad_res.status_code == 401


def test_logout():
    response = client.post("/api/v1/auth/logout")
    assert response.status_code == 200
    assert "message" in response.json()
