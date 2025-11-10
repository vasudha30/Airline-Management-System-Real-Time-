from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, func, UniqueConstraint, Text
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import expression
import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)

class Flight(Base):
    __tablename__ = "flights"
    id = Column(Integer, primary_key=True)
    flight_number = Column(String, nullable=False)
    origin = Column(String, nullable=False)
    destination = Column(String, nullable=False)
    depart_at = Column(DateTime, nullable=False)
    arrive_at = Column(DateTime, nullable=False)
    status = Column(String, default="scheduled")

class Seat(Base):
    __tablename__ = "seats"
    id = Column(Integer, primary_key=True)
    flight_id = Column(Integer, ForeignKey("flights.id", ondelete="CASCADE"))
    seat_code = Column(String, nullable=False)
    seat_class = Column(String, default="economy")
    __table_args__ = (UniqueConstraint("flight_id", "seat_code", name="uix_flight_seat"),)

class Booking(Base):
    __tablename__ = "bookings"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    flight_id = Column(Integer, ForeignKey("flights.id"))
    seat_id = Column(Integer, ForeignKey("seats.id"))
    status = Column(String, nullable=False)  # hold, confirmed, cancelled
    hold_expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

class Payment(Base):
    __tablename__ = "payments"
    id = Column(Integer, primary_key=True)
    booking_id = Column(Integer, ForeignKey("bookings.id"), nullable=True)
    amount_cents = Column(Integer, nullable=False)
    status = Column(String, nullable=False)  # pending, succeeded, failed
    idempotency_key = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
