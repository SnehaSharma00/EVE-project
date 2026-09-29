from datetime import UTC, datetime

from fastapi.testclient import TestClient


def get_auth_headers(client: TestClient) -> dict[str, str]:
    email = f"testadmin_{datetime.now(UTC).timestamp()}@example.com"
    client.post(
        "/api/v1/auth/signup",
        json={"email": email, "password": "Password123!", "full_name": "Admin User"},
    )
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "Password123!"},
    )
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_create_and_get_test(client: TestClient):
    headers = get_auth_headers(client)
    payload = {
        "name": "Lipid Profile Panel",
        "description": "Cholesterol, Triglycerides, HDL, LDL",
        "category": "Biochemistry",
        "is_active": True,
    }
    create_res = client.post("/api/v1/tests", json=payload, headers=headers)
    assert create_res.status_code == 201
    test_data = create_res.json()
    assert test_data["name"] == "Lipid Profile Panel"
    assert test_data["category"] == "Biochemistry"
    test_id = test_data["id"]

    # Get by ID
    get_res = client.get(f"/api/v1/tests/{test_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == test_id


def test_get_invalid_test(client: TestClient):
    res = client.get("/api/v1/tests/99999")
    assert res.status_code == 404
    data = res.json()
    assert data["success"] is False
    assert data["error"]["code"] == "DIAGNOSTICTEST_NOT_FOUND"


def test_list_tests_filter_category(client: TestClient):
    headers = get_auth_headers(client)
    client.post(
        "/api/v1/tests",
        json={
            "name": "Thyroid Stimulating Hormone (TSH)",
            "description": "Thyroid functioning test",
            "category": "Endocrinology",
        },
        headers=headers,
    )
    client.post(
        "/api/v1/tests",
        json={
            "name": "Vitamin D3",
            "description": "25-hydroxy vitamin D test",
            "category": "Endocrinology",
        },
        headers=headers,
    )

    res = client.get("/api/v1/tests?category=Endocrinology")
    assert res.status_code == 200
    tests = res.json()
    assert len(tests) >= 2
    assert all(t["category"] == "Endocrinology" for t in tests)
