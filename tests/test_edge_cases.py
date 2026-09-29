from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient


def create_user_helper(client: TestClient, email_prefix: str = "edge_user"):
    email = f"{email_prefix}_{datetime.now(UTC).timestamp()}@example.com"
    res = client.post(
        "/api/v1/auth/signup",
        json={"email": email, "password": "Password123!", "full_name": "Edge Patient"},
    )
    user_id = res.json()["id"]
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "Password123!"},
    )
    headers = {"Authorization": f"Bearer {login_res.json()['access_token']}"}
    return user_id, headers


def test_edge_case_inactive_centre_booking(client: TestClient):
    _, headers = create_user_helper(client, "inactive_c")

    # Create inactive centre
    c_res = client.post(
        "/api/v1/centres",
        json={
            "name": "Inactive Centre",
            "address": "00 Closed Ave",
            "city": "Pune",
            "state": "Maharashtra",
            "is_active": False,
        },
        headers=headers,
    )
    centre_id = c_res.json()["id"]

    t_res = client.post(
        "/api/v1/tests",
        json={"name": "CBC", "category": "General", "is_active": True},
        headers=headers,
    )
    test_id = t_res.json()["id"]

    # Attempting to add test to inactive centre
    add_test_res = client.post(
        f"/api/v1/centres/{centre_id}/tests",
        json={"test_id": test_id, "price": 300.00},
        headers=headers,
    )
    assert add_test_res.status_code == 422
    assert add_test_res.json()["error"]["code"] == "INACTIVE_CENTRE"


def test_edge_case_inactive_test_booking(client: TestClient):
    _, headers = create_user_helper(client, "inactive_t")

    c_res = client.post(
        "/api/v1/centres",
        json={
            "name": "Active Centre",
            "address": "11 Open Ave",
            "city": "Pune",
            "state": "Maharashtra",
            "is_active": True,
        },
        headers=headers,
    )
    centre_id = c_res.json()["id"]

    # Inactive test
    t_res = client.post(
        "/api/v1/tests",
        json={"name": "Discontinued Test", "category": "Old", "is_active": False},
        headers=headers,
    )
    test_id = t_res.json()["id"]

    add_test_res = client.post(
        f"/api/v1/centres/{centre_id}/tests",
        json={"test_id": test_id, "price": 300.00},
        headers=headers,
    )
    assert add_test_res.status_code == 422
    assert add_test_res.json()["error"]["code"] == "INACTIVE_TEST"


def test_edge_case_slot_mismatch_centre(client: TestClient):
    _, headers = create_user_helper(client, "mismatch_slot")

    # Centre 1 & Test
    c1_res = client.post(
        "/api/v1/centres",
        json={"name": "Centre 1", "address": "1 A St", "city": "Delhi", "state": "Delhi"},
        headers=headers,
    )
    c1_id = c1_res.json()["id"]

    t_res = client.post(
        "/api/v1/tests",
        json={"name": "ECG", "category": "Cardiology"},
        headers=headers,
    )
    t_id = t_res.json()["id"]

    ct_res = client.post(
        f"/api/v1/centres/{c1_id}/tests",
        json={"test_id": t_id, "price": 400.00},
        headers=headers,
    )
    ct_id = ct_res.json()["id"]

    # Centre 2 with slot
    c2_res = client.post(
        "/api/v1/centres",
        json={"name": "Centre 2", "address": "2 B St", "city": "Delhi", "state": "Delhi"},
        headers=headers,
    )
    c2_id = c2_res.json()["id"]

    future_dt = (datetime.now(UTC) + timedelta(days=2)).isoformat()
    s_res = client.post(
        f"/api/v1/centres/{c2_id}/slots",
        json={"appointment_datetime": future_dt, "is_available": True},
        headers=headers,
    )
    slot_c2_id = s_res.json()["id"]

    # Try booking Centre 1's test using Centre 2's slot
    book_res = client.post(
        "/api/v1/bookings",
        json={"centre_test_id": ct_id, "appointment_slot_id": slot_c2_id},
        headers=headers,
    )
    assert book_res.status_code == 422
    assert book_res.json()["error"]["code"] == "INVALID_SLOT_CENTRE"


def test_edge_case_pay_confirmed_booking(client: TestClient):
    _, headers = create_user_helper(client, "pay_confirmed")

    # Setup centre, test, slot, booking
    c_res = client.post(
        "/api/v1/centres",
        json={"name": "Centre Alpha", "address": "Alpha Way", "city": "Goa", "state": "Goa"},
        headers=headers,
    )
    c_id = c_res.json()["id"]
    t_res = client.post(
        "/api/v1/tests",
        json={"name": "Urine Routine", "category": "Pathology"},
        headers=headers,
    )
    t_id = t_res.json()["id"]
    ct_res = client.post(
        f"/api/v1/centres/{c_id}/tests",
        json={"test_id": t_id, "price": 250.00},
        headers=headers,
    )
    ct_id = ct_res.json()["id"]
    s_res = client.post(
        f"/api/v1/centres/{c_id}/slots",
        json={
            "appointment_datetime": (datetime.now(UTC) + timedelta(days=3)).isoformat(),
            "is_available": True,
        },
        headers=headers,
    )
    slot_id = s_res.json()["id"]

    b_res = client.post(
        "/api/v1/bookings",
        json={"centre_test_id": ct_id, "appointment_slot_id": slot_id},
        headers=headers,
    )
    booking_id = b_res.json()["id"]

    # First payment -> Confirmed
    pay1 = client.post(
        "/api/v1/payments",
        json={"booking_id": booking_id, "amount": 250.00, "simulate_status": "SUCCESS"},
        headers=headers,
    )
    assert pay1.status_code == 201

    # Second payment attempt on already confirmed booking
    pay2 = client.post(
        "/api/v1/payments",
        json={"booking_id": booking_id, "amount": 250.00, "simulate_status": "SUCCESS"},
        headers=headers,
    )
    assert pay2.status_code == 409
    assert pay2.json()["error"]["code"] == "BOOKING_ALREADY_CONFIRMED"
