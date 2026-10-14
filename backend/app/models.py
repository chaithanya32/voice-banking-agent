
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    password_hash: Mapped[str] = mapped_column(
        String(255), nullable=False
    )
    pin_hash: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )
    failed_pin_attempts: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    pin_locked_until: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )


class PaymentRecord(Base):
    __tablename__ = "payments"

    payment_id: Mapped[str] = mapped_column(
        String(36), primary_key=True
    )
    payee_id: Mapped[str] = mapped_column(
        String(20), nullable=False
    )
    payee_name: Mapped[str] = mapped_column(
        String(100), nullable=False
    )
    amount: Mapped[float] = mapped_column(
        Numeric(18, 2), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    customer_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("customers.id"),
        nullable=True,
        index=True,
    )


class LedgerEntry(Base):
    __tablename__ = "ledger_entries"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    payment_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("payments.payment_id"),
        nullable=False,
    )
    account_name: Mapped[str] = mapped_column(
        String(100), nullable=False
    )
    entry_type: Mapped[str] = mapped_column(
        String(10), nullable=False
    )
    amount: Mapped[float] = mapped_column(
        Numeric(18, 2), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    payment_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("payments.payment_id"),
        nullable=True,
    )
    event_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )
    details: Mapped[str] = mapped_column(
        Text, nullable=False, default=""
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
