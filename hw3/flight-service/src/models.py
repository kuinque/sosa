import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Numeric, DateTime, ForeignKey, CheckConstraint, UniqueConstraint, Index, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .database import Base


class Flight(Base):
    __tablename__ = "flights"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    flight_number = Column(String(10), nullable=False)
    airline = Column(String(100), nullable=False)
    origin = Column(String(3), nullable=False)
    destination = Column(String(3), nullable=False)
    departure_time = Column(DateTime(timezone=True), nullable=False)
    arrival_time = Column(DateTime(timezone=True), nullable=False)
    total_seats = Column(Integer, nullable=False)
    available_seats = Column(Integer, nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    status = Column(String(20), nullable=False, default="SCHEDULED")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    
    reservations = relationship("SeatReservation", back_populates="flight")
    
    __table_args__ = (
        CheckConstraint("total_seats > 0", name="check_total_seats_positive"),
        CheckConstraint("available_seats >= 0", name="check_available_seats_non_negative"),
        CheckConstraint("available_seats <= total_seats", name="check_available_seats_limit"),
        CheckConstraint("price > 0", name="check_price_positive"),
        CheckConstraint("arrival_time > departure_time", name="check_arrival_after_departure"),
        Index("idx_flights_route_date", "origin", "destination", "departure_time"),
        Index("idx_flights_status", "status"),
        Index("idx_flights_number_date", "flight_number", "departure_time", unique=True),
    )


class SeatReservation(Base):
    __tablename__ = "seat_reservations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    flight_id = Column(UUID(as_uuid=True), ForeignKey("flights.id"), nullable=False)
    booking_id = Column(UUID(as_uuid=True), nullable=False, unique=True)
    seat_count = Column(Integer, nullable=False)
    status = Column(String(20), nullable=False, default="ACTIVE")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    
    flight = relationship("Flight", back_populates="reservations")
    
    __table_args__ = (
        CheckConstraint("seat_count > 0", name="check_seat_count_positive"),
        Index("idx_reservations_booking", "booking_id"),
        Index("idx_reservations_flight", "flight_id"),
    )
