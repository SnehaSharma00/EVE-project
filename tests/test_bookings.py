from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient


def get_authenticated_user(client: TestClient, email_prefix: str = "user"):
    email = f"{email_prefix}_{datetime.now(UTC).timestamp()}@example.com"
    client.post(
        "/api/v1/auth/signup",
        json={"email": email, "password": "Password123!", "full_name": "Test Patient"},
    )
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "Password123!"},
    )
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}, email


def setup_centre_test_and_slot(client: TestClient, headers: dict[str, str]):
    # 1. Create Centre
    c_res = client.post(
        "/api/v1/centres",
        json={
            "name": "Apollo Diagnostics",
            "address": "45 Green Way",
            "city": "Bengaluru",
            "state": "Karnataka",
        },
        headers=headers,
    )
    centre_id = c_res.json()["id"]

    # 2. Create Test
    t_res = client.post(
        "/api/v1/tests",
        json={
            "name": "HbA1c Diabetes Test",
            "description": "Glycated hemoglobin test",
            "category": "Diabetology",
        },
        headers=headers,
    )
    test_id = t_res.json()["id"]

    # 3. Associate with price
    ct_res = client.post(
        f"/api/v1/centres/{centre_id}/tests",
        json={"test_id": test_id, "price": 650.00},
        headers=headers,
    )
    centre_test_id = ct_res.json()["id"]

    # 4. Create future slot
    future_time = (datetime.now(UTC) + timedelta(days=3)).isoformat()
    slot_res = client.post(
        f"/api/v1/centres/{centre_id}/slots",
        json={"appointment_datetime": future_time, "is_available": True},
        headers=headers,
    )
    slot_id = slot_res.json()["id"]

    return centre_id, test_id, centre_test_id, slot_id


def test_create_booking_success(client: TestClient):
    headers, _ = get_authenticated_user(client, "patient1")
    _, _, centre_test_id, slot_id = setup_centre_test_and_slot(client, headers)

    booking_payload = {
        "centre_test_id": centre_test_id,
        "appointment_slot_id": slot_id,
    }
    response = client.post("/api/v1/bookings", json=booking_payload, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "PENDING"
    assert data["booking_reference"].startswith("BKG-")
    assert Decimal(str(data["amount"])) == Decimal("650.00")
    assert data["centre_test_id"] == centre_test_id
    assert data["appointment_slot_id"] == slot_id


def test_duplicate_slot_booking_conflict(client: TestClient):
    headers1, _ = get_authenticated_user(client, "patient_dup1")
    headers2, _ = get_authenticated_user(client, "patient_dup2")
    _, _, centre_test_id, slot_id = setup_centre_test_and_slot(client, headers1)

    booking_payload = {
        "centre_test_id": centre_test_id,
        "appointment_slot_id": slot_id,
    }

    # First patient books slot
    res1 = client.post("/api/v1/bookings", json=booking_payload, headers=headers1)
    assert res1.status_code == 201

    # Second patient attempts to book the SAME slot
    res2 = client.post("/api/v1/bookings", json=booking_payload, headers=headers2)
    assert res2.status_code == 409
    data = res2.json()
    assert data["success"] is False
    assert data["error"]["code"] == "SLOT_ALREADY_BOOKED"


def test_booking_unauthorized_access(client: TestClient):
    headers1, _ = get_authenticated_user(client, "owner_user")
    headers2, _ = get_authenticated_user(client, "other_user")
    _, _, centre_test_id, slot_id = setup_centre_test_and_slot(client, headers1)

    # User 1 creates booking
    res = client.post(
        "/api/v1/bookings",
        json={"centre_test_id": centre_test_id, "appointment_slot_id": slot_id},
        headers=headers1,
    )
    booking_id = res.json()["id"]

    # User 2 attempts to get User 1's booking
    get_res = client.get(f"/api/v1/bookings/{booking_id}", headers=headers2)
    assert get_res.status_code == 403
    assert get_res.json()["error"]["code"] == "FORBIDDEN"

    # User 2 attempts to cancel User 1's booking
    cancel_res = client.post(f"/api/v1/bookings/{booking_id}/cancel", headers=headers2)
    assert cancel_res.status_code == 403
    assert cancel_res.json()["error"]["code"] == "FORBIDDEN"


def test_cancel_booking_lifecycle_and_free_slot(client: TestClient):
    headers, _ = get_authenticated_user(client, "cancel_patient")
    centre_id, _, centre_test_id, slot_id = setup_centre_test_and_slot(client, headers)

    # Book slot
    book_res = client.post(
        "/api/v1/bookings",
        json={"centre_test_id": centre_test_id, "appointment_slot_id": slot_id},
        headers=headers,
    )
    booking_id = book_res.json()["id"]

    # Cancel booking
    cancel_res = client.post(f"/api/v1/bookings/{booking_id}/cancel", headers=headers)
    assert cancel_res.status_code == 200
    assert cancel_res.json()["status"] == "CANCELLED"

    # Verify slot is freed up and available again
    slots_res = client.get(f"/api/v1/centres/{centre_id}/slots", headers=headers)
    available_slots = [s for s in slots_res.json() if s["id"] == slot_id and s["is_available"]]
    assert len(available_slots) == 1

    # Attempt to cancel again -> invalid state transition
    second_cancel_res = client.post(f"/api/v1/bookings/{booking_id}/cancel", headers=headers)
    assert second_cancel_res.status_code == 409
    assert second_cancel_res.json()["error"]["code"] == "INVALID_STATE_TRANSITION"
