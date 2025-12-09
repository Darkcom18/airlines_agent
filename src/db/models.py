"""
SQLAlchemy models for C1 Travel Agent System.
"""
import uuid
from datetime import datetime
from typing import Optional
from decimal import Decimal

from sqlalchemy import (
    String, Boolean, DateTime, ForeignKey, Text, Numeric, Date, JSON
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class User(Base):
    """User account model."""
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(255))
    phone: Mapped[Optional[str]] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    passengers: Mapped[list["UserPassenger"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    ff_cards: Mapped[list["UserFFCard"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    bookings: Mapped[list["Booking"]] = relationship(back_populates="user")
    sessions: Mapped[list["Session"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class UserPassenger(Base):
    """Saved passenger information for a user."""
    __tablename__ = "user_passengers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    passenger_type: Mapped[str] = mapped_column(String(10), default="ADT")
    title: Mapped[Optional[str]] = mapped_column(String(10))
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    date_of_birth: Mapped[Optional[datetime]] = mapped_column(Date)
    gender: Mapped[Optional[str]] = mapped_column(String(10))
    nationality: Mapped[Optional[str]] = mapped_column(String(3))
    passport_number: Mapped[Optional[str]] = mapped_column(String(50))
    passport_expiry: Mapped[Optional[datetime]] = mapped_column(Date)
    passport_country: Mapped[Optional[str]] = mapped_column(String(3))
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="passengers")


class UserFFCard(Base):
    """Frequent flyer cards for a user."""
    __tablename__ = "user_ff_cards"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    airline_code: Mapped[str] = mapped_column(String(3), nullable=False)
    card_number: Mapped[str] = mapped_column(String(50), nullable=False)
    card_type: Mapped[Optional[str]] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="ff_cards")


class Booking(Base):
    """Flight booking record."""
    __tablename__ = "bookings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    pnr: Mapped[Optional[str]] = mapped_column(String(10))
    booking_code: Mapped[Optional[str]] = mapped_column(String(50))
    source: Mapped[str] = mapped_column(String(10), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    booking_data: Mapped[Optional[dict]] = mapped_column(JSON)
    total_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(3), default="VND")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Relationships
    user: Mapped[Optional["User"]] = relationship(back_populates="bookings")
    passengers: Mapped[list["BookingPassenger"]] = relationship(
        back_populates="booking", cascade="all, delete-orphan"
    )


class Session(Base):
    """Agent session for state persistence."""
    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    session_token: Mapped[Optional[str]] = mapped_column(String(255), unique=True)
    agent_state: Mapped[Optional[dict]] = mapped_column(JSON)
    context: Mapped[Optional[dict]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Relationships
    user: Mapped[Optional["User"]] = relationship(back_populates="sessions")


class BookingPassenger(Base):
    """Passenger linked to a booking."""
    __tablename__ = "booking_passengers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    booking_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False
    )
    passenger_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user_passengers.id", ondelete="SET NULL")
    )
    passenger_type: Mapped[str] = mapped_column(String(10), nullable=False)
    title: Mapped[Optional[str]] = mapped_column(String(10))
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    date_of_birth: Mapped[Optional[datetime]] = mapped_column(Date)
    ticket_number: Mapped[Optional[str]] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    # Relationships
    booking: Mapped["Booking"] = relationship(back_populates="passengers")
