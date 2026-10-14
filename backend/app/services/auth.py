import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from typing import Optional
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pwdlib import PasswordHash
from sqlalchemy import select
import re
from datetime import datetime, timedelta

from app.database import SessionLocal
from app.models import Customer

JWT_SECRET_KEY = os.getenv(
    "JWT_SECRET_KEY",
    "local-development-secret-change-before-deployment",
)
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_MINUTES = 60

password_hasher = PasswordHash.recommended()
bearer_scheme = HTTPBearer(auto_error=False)


def register_customer(name: str, email: str, password: str) -> Customer:
    name = name.strip()
    email = email.strip().lower()

    if not name:
        raise ValueError("Name is required.")
    if "@" not in email:
        raise ValueError("Enter a valid email address.")
    if len(password) < 8:
        raise ValueError("Password must contain at least 8 characters.")

    with SessionLocal() as session:
        existing = session.scalar(
            select(Customer).where(Customer.email == email)
        )
        if existing:
            raise ValueError("An account with this email already exists.")

        customer = Customer(
            id=str(uuid4()),
            name=name,
            email=email,
            password_hash=password_hasher.hash(password),
        )
        session.add(customer)
        session.commit()
        session.refresh(customer)

        # Return a detached copy of the account details.
        session.expunge(customer)
        return customer


def authenticate_customer(email: str, password: str) -> Customer:
    email = email.strip().lower()

    with SessionLocal() as session:
        customer = session.scalar(
            select(Customer).where(Customer.email == email)
        )

        if (
            customer is None
            or not password_hasher.verify(password, customer.password_hash)
        ):
            raise ValueError("Incorrect email or password.")

        session.expunge(customer)
        return customer


def create_access_token(customer_id: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": customer_id,
        "iat": now,
        "exp": now + timedelta(minutes=ACCESS_TOKEN_MINUTES),
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def get_current_customer(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> Customer:
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="Please log in to continue.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = jwt.decode(
            credentials.credentials,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
        )
        customer_id = payload.get("sub")
        if not customer_id:
            raise ValueError("Missing customer ID.")
    except (jwt.InvalidTokenError, ValueError):
        raise HTTPException(
            status_code=401,
            detail="Your session is invalid or expired. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    with SessionLocal() as session:
        customer = session.get(Customer, customer_id)
        if customer is None:
            raise HTTPException(status_code=401, detail="Customer account not found.")

        session.expunge(customer)
        return customer


def set_customer_pin(customer_id: str, pin: str) -> None:
    if not re.fullmatch(r"\d{4,6}", pin):
        raise ValueError("PIN must contain 4 to 6 digits.")

    with SessionLocal() as session:
        customer = session.get(Customer, customer_id)
        if customer is None:
            raise ValueError("Customer account not found.")

        customer.pin_hash = password_hasher.hash(pin)
        customer.failed_pin_attempts = 0
        customer.pin_locked_until = None
        session.commit()


def verify_customer_pin(customer_id: str, pin: str) -> None:
    if not re.fullmatch(r"\d{4,6}", pin):
        raise ValueError("Enter a valid 4 to 6 digit PIN.")

    with SessionLocal() as session:
        customer = session.get(Customer, customer_id)
        if customer is None:
            raise ValueError("Customer account not found.")

        if not customer.pin_hash:
            raise ValueError("Set up your PIN before making this payment.")

        now = datetime.utcnow()
        locked_until = customer.pin_locked_until

        if locked_until is not None and locked_until > now:
            raise ValueError("PIN verification is temporarily locked. Try again later.")

        if not password_hasher.verify(pin, customer.pin_hash):
            customer.failed_pin_attempts += 1

            if customer.failed_pin_attempts >= 3:
                customer.failed_pin_attempts = 0
                customer.pin_locked_until = now + timedelta(minutes=5)

            session.commit()

            if customer.pin_locked_until is not None:
                raise ValueError("Too many incorrect attempts. PIN locked for 5 minutes.")

            raise ValueError("Incorrect PIN.")

        customer.failed_pin_attempts = 0
        customer.pin_locked_until = None
        session.commit()
