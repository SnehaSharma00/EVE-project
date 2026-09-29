from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient


def get_auth_headers(client: TestClient) -> dict[str, str]:
    email = f"admin_{datetime.now(UTC).timestamp()}@example.com"
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


def test_create_and_get_centre(client: TestClient):
    headers = get_auth_headers(client)
    payload = {
        "name": "EVE Central Diagnostic Lab",
        "address": "123 Healthcare Ave",
        "city": "Bengaluru",
        "state": "Karnataka",
        "latitude": 12.9716,
        "longitude": 77.5946,
        "is_active": True,
    }
    create_res = client.post("/api/v1/centres", json=payload, headers=headers)
    assert create_res.status_code == 201
    centre_data = create_res.json()
    assert centre_data["name"] == "EVE Central Diagnostic Lab"
    assert centre_data["city"] == "Bengaluru"
    centre_id = centre_data["id"]

    # Get by ID
    get_res = client.get(f"/api/v1/centres/{centre_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == centre_id


def test_get_invalid_centre(client: TestClient):
    response = client.get("/api/v1/centres/99999")
    assert response.status_code == 404
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "DIAGNOSTICCENTRE_NOT_FOUND"


def test_list_centres_filter_city(client: TestClient):
    headers = get_auth_headers(client)
    client.post(
        "/api/v1/centres",
        json={
            "name": "Mumbai Diagnostics",
            "address": "456 Marine Drive",
            "city": "Mumbai",
            "state": "Maharashtra",
        },
        headers=headers,
    )
    client.post(
        "/api/v1/centres",
        json={
            "name": "Delhi Health Hub",
            "address": "789 Ring Road",
            "city": "Delhi",
            "state": "Delhi",
        },
        headers=headers,
    )

    res = client.get("/api/v1/centres?city=Mumbai")
    assert res.status_code == 200
    centres = res.json()
    assert len(centres) >= 1
    assert all("mumbai" in c["city"].lower() for c in centres)


def test_update_centre(client: TestClient):
    headers = get_auth_headers(client)
    create_res = client.post(
        "/api/v1/centres",
        json={
            "name": "Old Centre Name",
            "address": "100 MG Road",
            "city": "Pune",
            "state": "Maharashtra",
        },
        headers=headers,
    )
    centre_id = create_res.json()["id"]

    patch_res = client.patch(
        f"/api/v1/centres/{centre_id}",
        json={"name": "New Updated Centre Name"},
        headers=headers,
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["name"] == "New Updated Centre Name"


def test_centre_test_association_and_duplicate(client: TestClient):
    headers = get_auth_headers(client)
    centre_res = client.post(
        "/api/v1/centres",
        json={
            "name": "Diagnostic Centre X",
            "address": "123 Main St",
            "city": "Chennai",
            "state": "Tamil Nadu",
        },
        headers=headers,
    )
    centre_id = centre_res.json()["id"]

    test_res = client.post(
        "/api/v1/tests",
        json={
            "name": "Complete Blood Count (CBC)",
            "description": "Comprehensive blood panel",
            "category": "Hematology",
        },
        headers=headers,
    )
    test_id = test_res.json()["id"]

    # Add test to centre
    add_res = client.post(
        f"/api/v1/centres/{centre_id}/tests",
        json={"test_id": test_id, "price": 499.00},
        headers=headers,
    )
    assert add_res.status_code == 201
    assert Decimal(str(add_res.json()["price"])) == Decimal("499.00")

    # Duplicate association attempt
    dup_res = client.post(
        f"/api/v1/centres/{centre_id}/tests",
        json={"test_id": test_id, "price": 550.00},
        headers=headers,
    )
    assert dup_res.status_code == 409
    assert dup_res.json()["error"]["code"] == "DUPLICATE_CENTRE_TEST"

    # List centre tests
    list_res = client.get(f"/api/v1/centres/{centre_id}/tests")
    assert list_res.status_code == 200
    assert len(list_res.json()) >= 1


def test_appointment_slots(client: TestClient):
    headers = get_auth_headers(client)
    centre_res = client.post(
        "/api/v1/centres",
        json={
            "name": "Slot Diagnostic Centre",
            "address": "100 Slot Way",
            "city": "Hyderabad",
            "state": "Telangana",
        },
        headers=headers,
    )
    centre_id = centre_res.json()["id"]

    # Future slot creation
    future_dt = (datetime.now(UTC) + timedelta(days=2)).isoformat()
    slot_res = client.post(
        f"/api/v1/centres/{centre_id}/slots",
        json={"appointment_datetime": future_dt, "is_available": True},
        headers=headers,
    )
    assert slot_res.status_code == 201
    assert slot_res.json()["is_available"] is True

    # Past slot creation -> validation error
    past_dt = (datetime.now(UTC) - timedelta(days=1)).isoformat()
    past_slot_res = client.post(
        f"/api/v1/centres/{centre_id}/slots",
        json={"appointment_datetime": past_dt, "is_available": True},
        headers=headers,
    )
    assert past_slot_res.status_code == 422
    assert past_slot_res.json()["error"]["code"] == "PAST_APPOINTMENT_DATE"

    # List slots
    slots_res = client.get(f"/api/v1/centres/{centre_id}/slots")
    assert slots_res.status_code == 200
    assert len(slots_res.json()) >= 1
