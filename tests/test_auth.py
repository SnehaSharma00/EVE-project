from datetime import timedelta

from fastapi.testclient import TestClient

from app.core.security import create_access_token


def test_signup_success(client: TestClient):
    payload = {
        "email": "patient@example.com",
        "password": "SecurePassword123!",
        "full_name": "Jane Doe",
        "role": "PATIENT",
    }
    response = client.post("/api/v1/auth/signup", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "patient@example.com"
    assert data["full_name"] == "Jane Doe"
    assert data["role"] == "PATIENT"
    assert data["is_active"] is True
    assert "id" in data
    assert "password" not in data
    assert "password_hash" not in data


def test_signup_duplicate_email(client: TestClient):
    payload = {
        "email": "duplicate@example.com",
        "password": "SecurePassword123!",
        "full_name": "John Doe",
    }
    # First signup
    res1 = client.post("/api/v1/auth/signup", json=payload)
    assert res1.status_code == 201

    # Second signup with same email
    res2 = client.post("/api/v1/auth/signup", json=payload)
    assert res2.status_code == 409
    data = res2.json()
    assert data["success"] is False
    assert data["error"]["code"] == "DUPLICATE_USER"


def test_login_success(client: TestClient):
    signup_payload = {
        "email": "login_user@example.com",
        "password": "CorrectPassword123!",
        "full_name": "Login User",
    }
    client.post("/api/v1/auth/signup", json=signup_payload)

    login_payload = {
        "email": "login_user@example.com",
        "password": "CorrectPassword123!",
    }
    response = client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "login_user@example.com"


def test_login_invalid_password(client: TestClient):
    signup_payload = {
        "email": "wrongpass@example.com",
        "password": "CorrectPassword123!",
        "full_name": "Wrong Pass User",
    }
    client.post("/api/v1/auth/signup", json=signup_payload)

    login_payload = {
        "email": "wrongpass@example.com",
        "password": "WrongPassword123!",
    }
    response = client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == 401
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "INVALID_CREDENTIALS"


def test_login_nonexistent_user(client: TestClient):
    login_payload = {
        "email": "nonexistent@example.com",
        "password": "SomePassword123!",
    }
    response = client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == 401
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "INVALID_CREDENTIALS"


def test_me_endpoint_authenticated(client: TestClient):
    signup_payload = {
        "email": "profile@example.com",
        "password": "Password123!",
        "full_name": "Profile User",
    }
    client.post("/api/v1/auth/signup", json=signup_payload)

    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "profile@example.com", "password": "Password123!"},
    )
    token = login_res.json()["access_token"]

    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "profile@example.com"
    assert data["full_name"] == "Profile User"


def test_me_endpoint_unauthorized_missing_token(client: TestClient):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "INVALID_TOKEN"


def test_me_endpoint_invalid_token(client: TestClient):
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer totally_invalid_token_string"},
    )
    assert response.status_code == 401
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "INVALID_TOKEN"


def test_me_endpoint_expired_token(client: TestClient):
    signup_payload = {
        "email": "expired@example.com",
        "password": "Password123!",
        "full_name": "Expired Token User",
    }
    res = client.post("/api/v1/auth/signup", json=signup_payload)
    user_id = res.json()["id"]

    expired_token = create_access_token(
        {"sub": str(user_id), "email": "expired@example.com"},
        expires_delta=timedelta(minutes=-10),
    )

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert response.status_code == 401
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "TOKEN_EXPIRED"
