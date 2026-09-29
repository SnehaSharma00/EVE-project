from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient


def get_user_and_booking(client: TestClient, price: Decimal = Decimal("500.00")):
    email = f"payer_{datetime.now(UTC).timestamp()}@example.com"
    client.post(
        "/api/v1/auth/signup",
        json={"email": email, "password": "Password123!", "full_name": "Payer Patient"},
    )
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "Password123!"},
    )
    headers = {"Authorization": f"Bearer {login_res.json()['access_token']}"}

    # Centre
    c_res = client.post(
        "/api/v1/centres",
        json={
            "name": "Care Clinic",
            "address": "12 Care Rd",
            "city": "Bengaluru",
            "state": "Karnataka",
        },
        headers=headers,
    )
    centre_id = c_res.json()["id"]

    # Test
    t_res = client.post(
        "/api/v1/tests",
        json={
            "name": "Liver Function Test (LFT)",
            "description": "Bilirubin, SGOT, SGPT",
            "category": "Biochemistry",
        },
        headers=headers,
    )
    test_id = t_res.json()["id"]

    # Centre Test
    ct_res = client.post(
        f"/api/v1/centres/{centre_id}/tests",
        json={"test_id": test_id, "price": float(price)},
        headers=headers,
    )
    centre_test_id = ct_res.json()["id"]

    # Slot
    future_dt = (datetime.now(UTC) + timedelta(days=5)).isoformat()
    slot_res = client.post(
        f"/api/v1/centres/{centre_id}/slots",
        json={"appointment_datetime": future_dt, "is_available": True},
        headers=headers,
    )
    slot_id = slot_res.json()["id"]

    # Booking
    booking_res = client.post(
        "/api/v1/bookings",
        json={"centre_test_id": centre_test_id, "appointment_slot_id": slot_id},
        headers=headers,
    )
    booking = booking_res.json()
    return headers, booking


def test_payment_success_confirms_booking(client: TestClient):
    headers, booking = get_user_and_booking(client, Decimal("500.00"))
    booking_id = booking["id"]

    payment_payload = {
        "booking_id": booking_id,
        "amount": 500.00,
        "simulate_status": "SUCCESS",
    }
    response = client.post("/api/v1/payments", json=payment_payload, headers=headers)
    assert response.status_code == 201
    payment_data = response.json()
    assert payment_data["status"] == "SUCCESS"
    assert payment_data["payment_reference"].startswith("PAY-")
    assert Decimal(str(payment_data["amount"])) == Decimal("500.00")

    # Verify booking status changed to CONFIRMED
    booking_res = client.get(f"/api/v1/bookings/{booking_id}", headers=headers)
    assert booking_res.status_code == 200
    assert booking_res.json()["status"] == "CONFIRMED"


def test_payment_failure_fails_booking(client: TestClient):
    headers, booking = get_user_and_booking(client, Decimal("400.00"))
    booking_id = booking["id"]

    payment_payload = {
        "booking_id": booking_id,
        "amount": 400.00,
        "simulate_status": "FAILED",
    }
    response = client.post("/api/v1/payments", json=payment_payload, headers=headers)
    assert response.status_code == 201
    payment_data = response.json()
    assert payment_data["status"] == "FAILED"

    # Verify booking status changed to FAILED
    booking_res = client.get(f"/api/v1/bookings/{booking_id}", headers=headers)
    assert booking_res.status_code == 200
    assert booking_res.json()["status"] == "FAILED"


def test_payment_amount_mismatch(client: TestClient):
    headers, booking = get_user_and_booking(client, Decimal("500.00"))
    booking_id = booking["id"]

    # Try paying 300 instead of 500
    payment_payload = {
        "booking_id": booking_id,
        "amount": 300.00,
        "simulate_status": "SUCCESS",
    }
    response = client.post("/api/v1/payments", json=payment_payload, headers=headers)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "PAYMENT_AMOUNT_MISMATCH"


def test_payment_cancelled_booking(client: TestClient):
    headers, booking = get_user_and_booking(client, Decimal("500.00"))
    booking_id = booking["id"]

    # Cancel booking first
    client.post(f"/api/v1/bookings/{booking_id}/cancel", headers=headers)

    payment_payload = {
        "booking_id": booking_id,
        "amount": 500.00,
        "simulate_status": "SUCCESS",
    }
    response = client.post("/api/v1/payments", json=payment_payload, headers=headers)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "BOOKING_ALREADY_CANCELLED"


def test_payment_idempotency_key(client: TestClient):
    headers, booking = get_user_and_booking(client, Decimal("750.00"))
    booking_id = booking["id"]
    idempotency_key = f"ik_test_{datetime.now(UTC).timestamp()}"

    payment_payload = {
        "booking_id": booking_id,
        "amount": 750.00,
        "simulate_status": "SUCCESS",
    }
    headers_with_ik = {**headers, "Idempotency-Key": idempotency_key}

    # First request
    res1 = client.post("/api/v1/payments", json=payment_payload, headers=headers_with_ik)
    assert res1.status_code == 201
    pay1 = res1.json()

    # Second request with SAME Idempotency-Key
    res2 = client.post("/api/v1/payments", json=payment_payload, headers=headers_with_ik)
    assert res2.status_code == 201 or res2.status_code == 200
    pay2 = res2.json()

    # Must return identical payment record
    assert pay1["id"] == pay2["id"]
    assert pay1["payment_reference"] == pay2["payment_reference"]
    assert pay1["status"] == pay2["status"]
