import uuid
from sqlalchemy import Column, String, Integer, Numeric, DateTime, CheckConstraint, Index, func
from sqlalchemy.dialects.postgresql import UUID

from .database import Base


class Booking(Base):
    __tablename__ = "bookings"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    flight_id = Column(UUID(as_uuid=True), nullable=False)
    passenger_name = Column(String(200), nullable=False)
    passenger_email = Column(String(200), nullable=False)
    seat_count = Column(Integer, nullable=False)
    total_price = Column(Numeric(10, 2), nullable=False)
    status = Column(String(20), nullable=False, default="CONFIRMED")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        CheckConstraint("seat_count > 0", name="check_seat_count_positive"),
        CheckConstraint("total_price > 0", name="check_total_price_positive"),
        Index("idx_bookings_user", "user_id"),
        Index("idx_bookings_flight", "flight_id"),
        Index("idx_bookings_status", "status"),
    )
