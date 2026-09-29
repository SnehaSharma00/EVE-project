from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models.booking import Booking
from app.db.models.enums import BookingStatus, PaymentStatus
from app.db.models.payment import Payment
from app.db.models.webhook import PaymentWebhookEvent


def setup_booking_and_pending_payment(client: TestClient, db: Session):
    # 1. Create User
    email = f"webhook_patient_{datetime.now(UTC).timestamp()}@example.com"
    client.post(
        "/api/v1/auth/signup",
        json={"email": email, "password": "Password123!", "full_name": "Webhook Patient"},
    )
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "Password123!"},
    )
    headers = {"Authorization": f"Bearer {login_res.json()['access_token']}"}

    # 2. Create Centre
    c_res = client.post(
        "/api/v1/centres",
        json={
            "name": "Webhook Lab",
            "address": "99 Health St",
            "city": "Bengaluru",
            "state": "Karnataka",
        },
        headers=headers,
    )
    centre_id = c_res.json()["id"]

    # 3. Create Test
    t_res = client.post(
        "/api/v1/tests",
        json={
            "name": "Full Body Profile",
            "description": "Comprehensive Health Screening",
            "category": "Preventive Care",
        },
        headers=headers,
    )
    test_id = t_res.json()["id"]

    # 4. Create CentreTest
    ct_res = client.post(
        f"/api/v1/centres/{centre_id}/tests",
        json={"test_id": test_id, "price": 1200.00},
        headers=headers,
    )
    centre_test_id = ct_res.json()["id"]

    # 5. Create Slot
    future_dt = (datetime.now(UTC) + timedelta(days=7)).isoformat()
    slot_res = client.post(
        f"/api/v1/centres/{centre_id}/slots",
        json={"appointment_datetime": future_dt, "is_available": True},
        headers=headers,
    )
    slot_id = slot_res.json()["id"]

    # 6. Create Booking
    b_res = client.post(
        "/api/v1/bookings",
        json={"centre_test_id": centre_test_id, "appointment_slot_id": slot_id},
        headers=headers,
    )
    booking = b_res.json()
    booking_id = booking["id"]

    # 7. Create Pending Payment directly or through API
    pay_ref = f"PAY-{datetime.now(UTC).strftime('%Y%m%d')}-WH{booking_id}"
    payment = Payment(
        booking_id=booking_id,
        amount=Decimal("1200.00"),
        payment_reference=pay_ref,
        status=PaymentStatus.PENDING,
        provider="mock_gateway",
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)

    return headers, booking, payment


def test_critical_webhook_idempotency_sent_ten_times(client: TestClient, db: Session):
    """
    CRITICAL TEST:
    Send the exact same webhook event 10 times.
    Verify:
    - exactly one webhook event record exists
    - exactly one payment exists
    - exactly one booking exists
    - payment status is SUCCESS
    - booking status is CONFIRMED
    - no duplicate side effects occur
    """
    headers, booking, payment = setup_booking_and_pending_payment(client, db)
    booking_id = booking["id"]
    payment_ref = payment.payment_reference
    event_id = f"evt_idempotency_10x_{datetime.now(UTC).timestamp()}"

    webhook_payload = {
        "event_id": event_id,
        "event_type": "payment.updated",
        "payment_id": payment_ref,
        "status": "SUCCESS",
    }

    responses = []
    # Send the exact same webhook 10 times
    for _ in range(10):
        res = client.post("/api/v1/payments/webhook", json=webhook_payload)
        responses.append(res)

    # 1. All responses should be HTTP 200 OK
    for i, res in enumerate(responses):
        assert res.status_code == 200, f"Request #{i + 1} failed with status {res.status_code}"
        data = res.json()
        assert data["success"] is True
        assert data["event_id"] == event_id
        if i == 0:
            assert data["status"] == "SUCCESS"
            assert data["message"] == "Webhook processed successfully."
        else:
            assert data["status"] == "ALREADY_PROCESSED"
            assert data["message"] == "Webhook event already processed."

    # 2. Verify database records
    # Exactly one webhook event record exists for this event_id
    event_count = db.scalar(
        select(func.count(PaymentWebhookEvent.id)).where(PaymentWebhookEvent.event_id == event_id)
    )
    assert event_count == 1, f"Expected 1 webhook event record, found {event_count}"

    # Exactly one payment exists for this booking
    payment_count = db.scalar(
        select(func.count(Payment.id)).where(Payment.booking_id == booking_id)
    )
    assert payment_count == 1, f"Expected 1 payment record, found {payment_count}"

    # Exactly one booking exists
    booking_count = db.scalar(select(func.count(Booking.id)).where(Booking.id == booking_id))
    assert booking_count == 1, f"Expected 1 booking record, found {booking_count}"

    # Final Payment state is SUCCESS
    db.refresh(payment)
    assert payment.status == PaymentStatus.SUCCESS

    # Final Booking state is CONFIRMED
    booking_record = db.scalar(select(Booking).where(Booking.id == booking_id))
    assert booking_record.status == BookingStatus.CONFIRMED


def test_webhook_payment_failed(client: TestClient, db: Session):
    headers, booking, payment = setup_booking_and_pending_payment(client, db)
    booking_id = booking["id"]
    payment_ref = payment.payment_reference
    event_id = f"evt_failed_{datetime.now(UTC).timestamp()}"

    webhook_payload = {
        "event_id": event_id,
        "event_type": "payment.updated",
        "payment_id": payment_ref,
        "status": "FAILED",
    }

    res = client.post("/api/v1/payments/webhook", json=webhook_payload)
    assert res.status_code == 200
    assert res.json()["status"] == "FAILED"

    db.refresh(payment)
    assert payment.status == PaymentStatus.FAILED

    booking_record = db.scalar(select(Booking).where(Booking.id == booking_id))
    assert booking_record.status == BookingStatus.FAILED


def test_webhook_unknown_payment(client: TestClient):
    webhook_payload = {
        "event_id": "evt_unknown_payment",
        "event_type": "payment.updated",
        "payment_id": "PAY-NONEXISTENT-9999",
        "status": "SUCCESS",
    }
    res = client.post("/api/v1/payments/webhook", json=webhook_payload)
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "PAYMENT_NOT_FOUND"


def test_webhook_on_cancelled_booking(client: TestClient, db: Session):
    headers, booking, payment = setup_booking_and_pending_payment(client, db)
    booking_id = booking["id"]
    payment_ref = payment.payment_reference

    # Cancel booking first
    client.post(f"/api/v1/bookings/{booking_id}/cancel", headers=headers)

    event_id = f"evt_cancelled_{datetime.now(UTC).timestamp()}"
    webhook_payload = {
        "event_id": event_id,
        "event_type": "payment.updated",
        "payment_id": payment_ref,
        "status": "SUCCESS",
    }
    res = client.post("/api/v1/payments/webhook", json=webhook_payload)
    assert res.status_code == 200

    # Booking must remain CANCELLED
    booking_record = db.scalar(select(Booking).where(Booking.id == booking_id))
    assert booking_record.status == BookingStatus.CANCELLED
