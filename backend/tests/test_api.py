
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def authenticated_headers():
    """Register a test customer and return their bearer token."""

    email = f"api-test-{uuid4().hex}@example.com"
    password = "TestPassword123!"

    registered = client.post(
        "/auth/register",
        json={
            "name": "API Test User",
            "email": email,
            "password": password,
        },
    )

    assert registered.status_code in (200, 201), registered.text

    logged_in = client.post(
        "/auth/login",
        json={
            "email": email,
            "password": password,
        },
    )

    assert logged_in.status_code == 200, logged_in.text

    token = logged_in.json()["access_token"]

    return {"Authorization": f"Bearer {token}"}


def test_health_endpoint():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_create_payment_success():
    headers = authenticated_headers()

    response = client.post(
        "/payments",
        json={
            "payee_name": "Ravi Kumar",
            "amount_text": "500 rupees",
        },
        headers=headers,
    )

    assert response.status_code == 201

    data = response.json()

    assert data["payee_name"] == "Ravi Kumar"
    assert data["amount"] == "500"
    assert data["status"] == "pending"
    assert data["payment_id"]


def test_reject_unknown_payee():
    headers = authenticated_headers()

    response = client.post(
        "/payments",
        json={
            "payee_name": "Unknown Person",
            "amount_text": "500 rupees",
        },
        headers=headers,
    )

    assert response.status_code == 400


def test_reject_invalid_amount():
    headers = authenticated_headers()

    response = client.post(
        "/payments",
        json={
            "payee_name": "Ravi Kumar",
            "amount_text": "five hundred or fifteen hundred",
        },
        headers=headers,
    )

    assert response.status_code == 400


def test_confirm_payment_success():
    headers = authenticated_headers()

    created = client.post(
        "/payments",
        json={
            "payee_name": "Ravi Kumar",
            "amount_text": "500 rupees",
        },
        headers=headers,
    )

    assert created.status_code == 201, created.text

    payment_id = created.json()["payment_id"]

    response = client.post(
        f"/payments/{payment_id}/confirm",
        json={"confirmed": True},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "completed"


def test_cancel_payment():
    headers = authenticated_headers()

    created = client.post(
        "/payments",
        json={
            "payee_name": "Priya Sharma",
            "amount_text": "200 rupees",
        },
        headers=headers,
    )

    assert created.status_code == 201, created.text

    payment_id = created.json()["payment_id"]

    response = client.post(
        f"/payments/{payment_id}/confirm",
        json={"confirmed": False},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "cancelled"


def test_cannot_confirm_payment_twice():
    headers = authenticated_headers()

    created = client.post(
        "/payments",
        json={
            "payee_name": "Ravi Kumar",
            "amount_text": "500 rupees",
        },
        headers=headers,
    )

    assert created.status_code == 201, created.text

    payment_id = created.json()["payment_id"]

    first_confirmation = client.post(
        f"/payments/{payment_id}/confirm",
        json={"confirmed": True},
        headers=headers,
    )

    assert first_confirmation.status_code == 200

    response = client.post(
        f"/payments/{payment_id}/confirm",
        json={"confirmed": True},
        headers=headers,
    )

    assert response.status_code == 400
