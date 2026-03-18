from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class FlightResponse(BaseModel):
    id: str
    flight_number: str
    airline: str
    origin: str
    destination: str
    departure_time: str
    arrival_time: str
    total_seats: int
    available_seats: int
    price: float
    status: str


class FlightListResponse(BaseModel):
    flights: List[FlightResponse]


class CreateBookingRequest(BaseModel):
    user_id: UUID
    flight_id: UUID
    passenger_name: str = Field(..., min_length=1, max_length=200)
    passenger_email: EmailStr
    seat_count: int = Field(..., gt=0)


class BookingResponse(BaseModel):
    id: UUID
    user_id: UUID
    flight_id: UUID
    passenger_name: str
    passenger_email: str
    seat_count: int
    total_price: Decimal
    status: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class BookingListResponse(BaseModel):
    bookings: List[BookingResponse]


class ErrorResponse(BaseModel):
    detail: str
