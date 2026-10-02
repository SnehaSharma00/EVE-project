# EVE Healthcare — Diagnostic Test Booking & Payment Backend Service







[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)



[![Python 3.12+](https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white)](https://www.python.org)



[![SQLAlchemy 2.0](https://img.shields.io/badge/SQLAlchemy-2.0-D71F00?logo=sqlalchemy&logoColor=white)](https://www.sqlalchemy.org)



[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white)](https://www.postgresql.org)



[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white)](https://www.docker.com)



[![Test Coverage](https://img.shields.io/badge/Coverage-92%25-brightgreen)](https://pytest.org)







> **Engineering Priority:** `Correctness > Architecture > Security > Tests > Documentation > Bonus Features`







Production-grade modular backend service for diagnostic test bookings, simulated payments, and **strictly idempotent webhook processing**, built for the **EVE Healthcare SDE Intern Backend Engineering Assignment**.







---







## Table of Contents



1. [Project Overview & Problem Statement](#1-project-overview--problem-statement)



2. [Architecture & Design System](#2-architecture--design-system)



3. [Tech Stack](#3-tech-stack)



4. [Folder Structure](#4-folder-structure)



5. [Database Design & ER Diagram](#5-database-design--er-diagram)



6. [Booking State Machine](#6-booking-state-machine)



7. [Simulated Payments & Header Idempotency](#7-simulated-payments--header-idempotency)



8. [Webhook Idempotency Strategy](#8-webhook-idempotency-strategy)



9. [Authentication & Authorization](#9-authentication--authorization)



10. [API Endpoints Reference](#10-api-endpoints-reference)



11. [Example API Requests & Responses](#11-example-api-requests--responses)



12. [Environment Variables](#12-environment-variables)



13. [Local Development Setup](#13-local-development-setup)



14. [Docker & Docker Compose Deployment](#14-docker--docker-compose-deployment)



15. [Running Migrations](#15-running-migrations)



16. [Running Automated Tests & Coverage](#16-running-automated-tests--coverage)



17. [Edge Cases & Error Handling](#17-edge-cases--error-handling)



18. [Design Decisions & Trade-offs](#18-design-decisions--trade-offs)



19. [Important Assumptions](#19-important-assumptions)



20. [Future Improvements & Roadmap](#20-future-improvements--roadmap)







---







## 1. Service Context & Core Requirements







Diagnostic test booking platforms need reliable handling of several important concerns:



- **Price consistency:** The amount captured when a booking is created must remain unchanged for that booking, even if the centre updates the test price later.



- **Appointment integrity:** A single appointment slot must not be allocated to multiple bookings, including when requests are made concurrently.



- **Controlled booking states:** Booking statuses (`PENDING`, `CONFIRMED`, `FAILED`, `CANCELLED`) should follow defined transitions so that invalid state changes cannot occur.



- **Reliable Payment & Webhook Processing:** Payment providers can deliver the same webhook more than once or send updates in a different order. Processing repeated events must therefore avoid duplicate payments, duplicate bookings, and inconsistent booking states.







This service uses a clean **modular monolith** structure to address these concerns through strict database constraints, transactional isolation, and comprehensive test coverage.







---







## 2. Architecture & Design System







The system follows a layered, unidirectional architectural pattern:







```



                  ┌────────────────────────────────────────┐
                  │          FastAPI Route Handler         │
                  │ (HTTP parsing, Status codes, Response) │
                  └───────────────────┬────────────────────┘
                                      │
                                      ▼
                  ┌────────────────────────────────────────┐
                  │          Pydantic Schema Layer         │
                  │   (Validation, Data sanitization)      │
                  └───────────────────┬────────────────────┘
                                      │
                                      ▼
                  ┌────────────────────────────────────────┐
                  │             Service Layer              │
                  │ (Business logic, State machine, Rules) │
                  └───────────────────┬────────────────────┘
                                      │
                                      ▼
                  ┌────────────────────────────────────────┐
                  │           Repository Layer             │
                  │   (ORM queries, Eager loading, DTOs)   │
                  └───────────────────┬────────────────────┘
                                      │
                                      ▼
                  ┌────────────────────────────────────────┐
                  │        PostgreSQL Database 16          │
                  │ (Foreign keys, Unique index, Numeric)  │
                  └────────────────────────────────────────┘

```

### Core Architecture Guidelines:


- **Focused Route Handlers:** Routes are responsible for parsing requests, returning HTTP responses, and passing work to service methods.



- **Centralized Business Rules:** Services handle state transitions, authorization checks, and booking-time price snapshots.



- **Dedicated Repository Layer:** SQL and ORM database operations are contained within repository classes.



- **Consistent Error Format:** Application exceptions use a common error response structure:


```bash

  {
    "success": false,
    "error": {
      "code": "ERROR_CODE",
      "message": "Human readable error description."
    }
  }

```

---


## 3. Tech Stack


| Component | Technology | Rationale |
|---|---|---|
| **Runtime & Framework** | Python 3.12+ / FastAPI | High performance, native async support, automatic OpenAPI/Swagger generation. |
| **ORM & Database** | SQLAlchemy 2.0 / PostgreSQL 16 | Modern type-safe `Mapped` columns, transactional safety, and robust ACID guarantees. |
| **Migrations** | Alembic | Tracked, reversible database schema evolution. |
| **Data Validation** | Pydantic v2 & `pydantic-settings` | Fast C-level input validation and typed configuration. |
| **Security & Auth** | Argon2 (`argon2-cffi`) & PyJWT | Memory-hard password hashing and standard JWT bearer token authentication. |
| **Testing** | Pytest, HTTPX, Pytest-Cov | High-speed unit and integration testing suite with SQLite in-memory isolation. |
| **Containerization** | Docker & Docker Compose | Self-contained multi-container deployment (API + PostgreSQL). |
| **Linter & Formatter** | Ruff | Modern, lightning-fast PEP8 compliance and lint validation. |




---


## 5. Database Design & ER Diagram



```mermaid

erDiagram



    USERS ||--o{ BOOKINGS : "places"



    DIAGNOSTIC_CENTRES ||--o{ CENTRE_TESTS : "offers"



    DIAGNOSTIC_CENTRES ||--o{ APPOINTMENT_SLOTS : "schedules"



    DIAGNOSTIC_TESTS ||--o{ CENTRE_TESTS : "included_in"



    CENTRE_TESTS ||--o{ BOOKINGS : "booked_for"



    APPOINTMENT_SLOTS ||--o| BOOKINGS : "reserves"



    BOOKINGS ||--o{ PAYMENTS : "paid_by"



    PAYMENTS ||--o{ PAYMENT_WEBHOOK_EVENTS : "updated_by"







    USERS {



        int id PK



        string email UK "Indexed"



        string password_hash



        string full_name



        string role "PATIENT | ADMIN"



        bool is_active



        timestamp created_at



        timestamp updated_at



    }







    DIAGNOSTIC_CENTRES {



        int id PK



        string name "Indexed"



        string address



        string city "Indexed"



        string state



        float latitude



        float longitude



        bool is_active



        timestamp created_at



        timestamp updated_at



    }







    DIAGNOSTIC_TESTS {



        int id PK



        string name "Indexed"



        text description



        string category "Indexed"



        bool is_active



        timestamp created_at



        timestamp updated_at



    }







    CENTRE_TESTS {



        int id PK



        int centre_id FK "Indexed"



        int test_id FK "Indexed"



        numeric price "Numeric(10, 2)"



        bool is_available



        timestamp created_at



        timestamp updated_at



    }







    APPOINTMENT_SLOTS {



        int id PK



        int centre_id FK "Indexed"



        int centre_test_id FK "Nullable"



        timestamp appointment_datetime "Indexed"



        bool is_available "Indexed"



        timestamp created_at



    }







    BOOKINGS {



        int id PK



        string booking_reference UK "Indexed"



        int user_id FK "Indexed"



        int centre_test_id FK "Indexed"



        int appointment_slot_id FK "Indexed"



        numeric amount "Price Snapshot Numeric(10, 2)"



        string status "PENDING | CONFIRMED | FAILED | CANCELLED"



        timestamp created_at



        timestamp updated_at



    }







    PAYMENTS {



        int id PK



        string payment_reference UK "Indexed"



        int booking_id FK "Indexed"



        numeric amount "Numeric(10, 2)"



        string status "PENDING | SUCCESS | FAILED"



        string provider



        string provider_transaction_id



        string idempotency_key UK "Indexed"



        timestamp created_at



        timestamp updated_at



    }







    PAYMENT_WEBHOOK_EVENTS {



        int id PK



        string event_id UK "Indexed"



        string event_type



        string payment_id "Indexed"



        text payload



        timestamp processed_at



        timestamp created_at



    }



```







### Critical Database Integrity Rules:



1. **Monetary Precision:** Stored strictly using `Numeric(10, 2)` / `Decimal` — never IEEE 754 floating points.



2. **Price Snapshotting:** `bookings.amount` records the exact price snapshot at the moment of booking creation.



3. **Uniqueness Constraints:**



   - `users.email` is globally unique.



   - `centre_tests(centre_id, test_id)` prevents duplicate test mappings for a center.



   - `bookings.booking_reference` is globally unique.



   - `payments.payment_reference` and `payments.idempotency_key` are unique.



   - `payment_webhook_events.event_id` is globally unique to guarantee idempotency.



4. **Foreign Keys & Cascades:**



   - Deleting a centre or test cascades to junction tables.



   - Bookings protect referenced Users, CentreTests, and Slots with `RESTRICT` constraints to maintain financial audit trails.







---







## 6. Booking State Machine







The booking lifecycle is governed by a strict state machine preventing arbitrary or illegal status modifications:







```mermaid



stateDiagram-v2



    [*] --> PENDING : Booking Created (Slot Reserved)



    PENDING --> CONFIRMED : Payment SUCCESS / Webhook SUCCESS



    PENDING --> FAILED : Payment FAILED / Webhook FAILED (Slot Released)



    PENDING --> CANCELLED : User Cancels (Slot Released)



    CONFIRMED --> CANCELLED : Refund / Cancellation (Slot Released)



    FAILED --> [*]



    CANCELLED --> [*]



    CONFIRMED --> [*]



```







### Transition Validation Rules:



- **`PENDING`**: Can transition to `CONFIRMED`, `FAILED`, or `CANCELLED`.



- **`CONFIRMED`**: Can only transition to `CANCELLED`.



- **`FAILED`** & **`CANCELLED`**: Terminal states. Any attempted transition out of these states returns `409 Conflict (INVALID_STATE_TRANSITION)`.



- **Slot Release Guarantee:** When a booking transitions to `CANCELLED` or `FAILED`, the reserved appointment slot is automatically restored to `is_available = True`.







---







## 7. Mock Payment Processing & Request Idempotency







For payment requests made through `POST /api/v1/payments`:



1. The service first verifies authenticated user ownership and confirms that the booking is in the `PENDING` state.



2. The submitted payment amount is checked against `booking.amount`; mismatched amounts are rejected with `422 Unprocessable Content`.



3. **Idempotency Header:** A client may provide an `Idempotency-Key` header (for example, `Idempotency-Key: ik_88f921a`).



   - If a payment already exists for that key, the existing payment record is returned immediately so that no duplicate charge or repeated booking transition occurs.



4. After the simulated payment is created successfully, the booking is atomically moved to either `CONFIRMED` or `FAILED`.







---







## 8. Webhook Idempotency Strategy







Webhooks from payment gateways are delivered asynchronously and often retried.







```mermaid



sequenceDiagram



    autonumber



    actor Gateway as Payment Gateway



    participant API as Webhook Endpoint (/payments/webhook)



    participant Service as WebhookService



    participant DB as PostgreSQL Database







    Gateway->>API: POST /payments/webhook {event_id, payment_id, status}



    API->>Service: process_webhook(payload)



    Service->>DB: SELECT * FROM payment_webhook_events WHERE event_id = ?



    alt Event already exists (Duplicate Delivery)



        DB-->>Service: Existing Event Record



        Service-->>API: 200 OK {"status": "ALREADY_PROCESSED"}



        API-->>Gateway: 200 OK



    else New Event



        Service->>DB: SELECT * FROM payments WHERE payment_reference = ?



        Service->>DB: UPDATE payments SET status = ?



        Service->>DB: UPDATE bookings SET status = ? (via State Machine)



        Service->>DB: INSERT INTO payment_webhook_events (event_id, ...)



        DB-->>Service: Committed



        Service-->>API: 200 OK {"status": "SUCCESS"}



        API-->>Gateway: 200 OK



    end



```







### Concurrency Safety:



- Database-level `UNIQUE(event_id)` index acts as the ultimate concurrency guard.



- If two identical webhook requests arrive concurrently at the exact same millisecond, one commits while the other triggers an `IntegrityError`, rolls back cleanly, and returns the idempotent response.







---







## 9. Authentication & Authorization







- **Password Security:** Hashes passwords with **Argon2id** (`argon2-cffi`), resistant to GPU/ASIC brute-force attacks.



- **Tokens:** Issues signed JWT access tokens containing user ID, email, and role.



- **Resource Ownership Authorization:** Non-admin patients can only view or cancel their own bookings and payments. Attempting to view another user's booking returns `403 Forbidden`.



- **Role Support:** Supports `PATIENT` and `ADMIN` roles through the `require_role(UserRole.ADMIN)` dependency.







---







## 10. API Endpoints Reference







| Method | Endpoint | Auth Required | Description |
|---|---|:---:|---|
| **GET** | `/health` | No | System & database health status |
| **POST** | `/api/v1/auth/signup` | No | Register a new user |
| **POST** | `/api/v1/auth/login` | No | Authenticate user and receive JWT token |
| **GET** | `/api/v1/auth/me` | Yes | Get authenticated user profile |
| **GET** | `/api/v1/centres` | No | List diagnostic centres (filter by `city`, `is_active`) |
| **GET** | `/api/v1/centres/{id}` | No | Get centre details by ID |
| **POST** | `/api/v1/centres` | Yes | Create diagnostic centre |
| **PATCH** | `/api/v1/centres/{id}` | Yes | Update diagnostic centre |
| **GET** | `/api/v1/tests` | No | List diagnostic tests (filter by `category`, `is_active`) |
| **GET** | `/api/v1/tests/{id}` | No | Get diagnostic test by ID |
| **POST** | `/api/v1/tests` | Yes | Create diagnostic test in catalogue |
| **GET** | `/api/v1/centres/{id}/tests` | No | List tests & prices offered at centre |
| **POST** | `/api/v1/centres/{id}/tests` | Yes | Associate test with centre and set price |
| **GET** | `/api/v1/centres/{id}/slots` | No | List available appointment slots at centre |
| **POST** | `/api/v1/centres/{id}/slots` | Yes | Create appointment slot at centre |
| **POST** | `/api/v1/bookings` | Yes | Create diagnostic booking (status `PENDING`) |
| **GET** | `/api/v1/bookings` | Yes | List user's bookings (all bookings if admin) |
| **GET** | `/api/v1/bookings/{id}` | Yes | Get booking details (ownership verified) |
| **POST** | `/api/v1/bookings/{id}/cancel` | Yes | Cancel booking and release slot |
| **POST** | `/api/v1/payments` | Yes | Process simulated payment (supports `Idempotency-Key`) |
| **GET** | `/api/v1/payments/{id}` | Yes | Get payment details |
| **POST** | `/api/v1/payments/webhook` | No | Idempotent payment gateway webhook receiver |


---


## 11. Example API Requests & Responses


### 1. User Signup

```bash

POST /api/v1/auth/signup

Content-Type: application/json

{
  "email": "sarah.connor@example.com",
  "password": "SecurePassword123!",
  "full_name": "Sarah Connor"
}


```

**Response (201 Created):**


```json

{
  "id": 1,
  "email": "sarah.connor@example.com",
  "full_name": "Sarah Connor",
  "role": "PATIENT",
  "is_active": true,
  "created_at": "2026-09-27T00:15:00Z",
  "updated_at": "2026-09-27T00:15:00Z"
}

```

### 2. Create Booking



```bash

POST /api/v1/bookings

Authorization: Bearer \\<JWT_TOKEN>

Content-Type: application/json

{
  "centre_test_id": 1,
  "appointment_slot_id": 5
}

```

**Response (201 Created):**

```json

{
  "id": 1,
  "booking_reference": "BKG-20260927-9A1F3B20",
  "user_id": 1,
  "centre_test_id": 1,
  "appointment_slot_id": 5,
  "amount": "650.00",
  "status": "PENDING",
  "created_at": "2026-09-27T00:18:00Z",
  "updated_at": "2026-09-27T00:18:00Z"
}

```

### 3. Idempotent Payment Webhook

```bash

POST /api/v1/payments/webhook

Content-Type: application/json

{
  "event_id": "evt_wh_98421049",
  "event_type": "payment.updated",
  "payment_id": "PAY-20260927-44E290BA",
  "status": "SUCCESS"
}

```

**Response (200 OK):**



```json

{
  "success": true,
  "event_id": "evt_wh_98421049",
  "message": "Webhook processed successfully.",
  "status": "SUCCESS",
  "processed_at": "2026-09-27T00:21:00Z"
}



```

**If re-sent with the same `event_id`:**

```json
{
  "success": true,
  "event_id": "evt_wh_98421049",
  "message": "Webhook event already processed.",
  "status": "ALREADY_PROCESSED",
  "processed_at": "2026-09-27T00:21:00Z"
}

```


---


## 12. Environment Variables


| Variable | Default (Local) | Description |
|---|---|---|
| `APP_NAME` | `EVE Healthcare Diagnostic Service` | Application title for OpenAPI |
| `APP_ENV` | `development` | Environment (`development`, `production`, `test`) |
| `DEBUG` | `True` | Debug flag |
| `SECRET_KEY` | `supersecretkeyforevediagnosticbackendengineeringassignment2026` | Key used for signing JWTs |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | JWT expiration duration in minutes |
| `DATABASE_URL` | `postgresql://eve_user:eve_password@localhost:5432/eve_healthcare` | Database connection URI |
| `LOG_LEVEL` | `INFO` | Application log verbosity |


---


## 13. Local Development Setup

### Prerequisites

- Python 3.12+ (or 3.13)

- PostgreSQL (or local SQLite)


### Installation

```bash

*# 1. Clone the repository*
git clone https://github.com/SnehaSharma00/EVE-project.git
cd sde-backend-assignment

*# 2. Create virtual environment*
python -m venv .venv
source .venv/bin/activate  *# On Windows: .venv\Scripts\activate*

*# 3. Install dependencies*
pip install -r requirements.txt

*# 4. Configure environment*
cp .env.example .env

*# 5. Apply database migrations*
alembic upgrade head

*# 6. Start development server*
uvicorn app.main:app --reload --port 8000

```


Interactive Swagger documentation will be available at: **http://localhost:8000/docs**


---


## 14. Docker & Docker Compose Deployment







The application is fully containerized with automated migrations on boot:







```bash

*# Start PostgreSQL and FastAPI together*
docker compose up --build

```



- API Endpoint: **http://localhost:8000**



- Health Check: **http://localhost:8000/health**



- Swagger UI: **http://localhost:8000/docs**







---







## 15. Running Migrations







```bash

*# Apply migrations to latest schema*
alembic upgrade head

*# Rollback one migration*
alembic downgrade -1

*# Generate a new auto-detected migration*
alembic revision --autogenerate -m "add_new_feature"

```

---

## 16. Running Automated Tests & Coverage

The test suite runs against an isolated in-memory SQLite database for maximum speed and safety.



```bash

*# Run all tests with short traceback*
pytest

*# Run tests with coverage report*
pytest --cov=app

```







**Coverage Report Output (92% Coverage):**



```

Name                                     Stmts   Miss  Cover
------------------------------------------------------------
app\api\deps.py                             42      9    79%
app\api\routes\auth.py                      20      0   100%
app\api\routes\bookings.py                  25      2    92%
app\api\routes\centres.py                   43      0   100%
app\api\routes\health.py                    15      2    87%
app\api\routes\payments.py                  16      2    88%
app\api\routes\tests.py                     21      0   100%
app\api\routes\webhooks.py                   9      0   100%
app\core\config.py                          25      1    96%
app\core\exceptions.py                      35      1    97%
app\core\logging.py                         23      0   100%
app\core\security.py                        22      0   100%
app\db\database.py                          16      4    75%
app\db\models\\\\* (all 9 model modules)      137      0   100%
app\repositories\\\\* (all 6 repos)           195     18    91%
app\schemas\\\\* (all 9 schema modules)       154      0   100%
app\services\\\\* (all 6 services)            284     31    89%
------------------------------------------------------------
TOTAL                                     1224    102    92%
\\======================= 36 passed in 7.33s =======================

```

---

## 17. Edge Cases & Error Handling

| Scenario | Handled Behavior | Status Code |
|---|---|:---:|
| **Duplicate Email Signup** | Rejects registration with `DUPLICATE_USER` | `409 Conflict` |
| **Invalid JWT / Expired JWT** | Rejects with `INVALID_TOKEN` or `TOKEN_EXPIRED` | `401 Unauthorized` |
| **Double Booking of Same Slot** | Concurrency locked; rejects 2nd attempt with `SLOT_ALREADY_BOOKED` | `409 Conflict` |
| **Booking Past Appointment** | Validates against UTC current time (`PAST_APPOINTMENT_DATE`) | `422 Unprocessable` |
| **Accessing Another User's Booking** | Strictly checks ownership; raises `FORBIDDEN` | `403 Forbidden` |
| **Booking Inactive Centre / Test** | Validates active status before reserving slot | `422 Unprocessable` |
| **Payment Amount Mismatch** | Compares against booking price snapshot | `422 Unprocessable` |
| **Payment on Cancelled Booking** | Rejects payment with `BOOKING_ALREADY_CANCELLED` | `409 Conflict` |
| **Double Payment on Booking** | Rejects duplicate payment with `PAYMENT_ALREADY_COMPLETED` | `409 Conflict` |
| **Repeated Idempotency Key** | Returns original payment record with no side effects | `200/201 OK` |
| **Repeated Webhook Event (10x)** | Idempotent short-circuit; returns `ALREADY_PROCESSED` with 0 duplicate DB records | `200 OK` |
| **Webhook on Cancelled Booking** | Updates payment audit status but preserves `CANCELLED` booking state | `200 OK` |


---

## 18. Architecture Choices & Engineering Considerations

1. **Modular Monolith Instead of Microservices:**

   - **Reasoning:** For a diagnostic booking service of this size, a modular monolith keeps domain boundaries between routes, services, and repositories while avoiding network latency, distributed transaction complexity (2PC/Saga), and additional orchestration overhead.

2. **Synchronous Session with Threadpool Execution:**

   - **Reasoning:** Synchronous SQLAlchemy 2.0 keeps ORM relationship loading and transaction handling straightforward, while FastAPI's automatic threadpool offloading supports request execution without introducing unnecessary async ORM complexity.

3. **Argon2id Instead of Standard Bcrypt:**

   - **Reasoning:** Argon2, the winner of the Password Hashing Competition (PHC), was selected for its memory-hard design and stronger resistance to hardware-accelerated password attacks.

4. **Booking-Time Price Snapshot:**

   - **Reasoning:** Diagnostic test prices may change over time. Saving the selected price directly in `bookings.amount` preserves the original booking amount for historical accuracy and financial auditing.

---


## 19. Important Assumptions

- Diagnostic centres manage their own catalog of tests and appointment slots.
- Appointment slot times are stored and evaluated in UTC.
- Simulated payment gateways communicate webhook status changes using standard reference codes.
- Cancellations release the corresponding appointment slot back to the public pool for re-booking.

---


