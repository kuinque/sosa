import logging
import time
from contextlib import asynccontextmanager
from datetime import date as date_type
from decimal import Decimal
from typing import Optional
from uuid import UUID

import grpc
from fastapi import FastAPI, HTTPException, Depends, Query
from sqlalchemy.orm import Session

from .config import config
from .database import engine, Base, get_db
from .models import Booking
from .schemas import (
    FlightResponse, FlightListResponse,
    CreateBookingRequest, BookingResponse, BookingListResponse,
)
from .flight_client import flight_client
from .circuit_breaker import CircuitBreakerError

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def wait_for_db(max_retries: int = 30, delay: int = 2):
    from sqlalchemy import text
    for i in range(max_retries):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("Database connection established")
            return
        except Exception as e:
            logger.warning(f"Database not ready (attempt {i+1}/{max_retries}): {e}")
            time.sleep(delay)
    raise RuntimeError("Could not connect to database")


def run_migrations():
    logger.info("Running database migrations...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database migrations completed")


@asynccontextmanager
async def lifespan(app: FastAPI):
    wait_for_db()
    run_migrations()
    flight_client.connect()
    logger.info("Booking Service started")
    yield
    logger.info("Booking Service shutting down")


app = FastAPI(
    title="Booking Service",
    description="REST API for flight bookings",
    version="1.0.0",
    lifespan=lifespan,
)


def handle_grpc_error(e: grpc.RpcError):
    code = e.code()
    details = e.details()
    
    if code == grpc.StatusCode.NOT_FOUND:
        raise HTTPException(status_code=404, detail=details)
    elif code == grpc.StatusCode.INVALID_ARGUMENT:
        raise HTTPException(status_code=400, detail=details)
    elif code == grpc.StatusCode.RESOURCE_EXHAUSTED:
        raise HTTPException(status_code=409, detail=details)
    elif code == grpc.StatusCode.UNAUTHENTICATED:
        raise HTTPException(status_code=500, detail="Internal authentication error")
    elif code == grpc.StatusCode.UNAVAILABLE:
        raise HTTPException(status_code=503, detail="Flight service unavailable")
    else:
        raise HTTPException(status_code=500, detail=f"Internal error: {details}")


@app.get("/flights", response_model=FlightListResponse)
def search_flights(
    origin: str = Query(..., min_length=3, max_length=3, description="IATA code"),
    destination: str = Query(..., min_length=3, max_length=3, description="IATA code"),
    flight_date: Optional[date_type] = Query(None, alias="date", description="Flight date (YYYY-MM-DD)"),
):
    try:
        flights = flight_client.search_flights(origin.upper(), destination.upper(), flight_date)
        return FlightListResponse(flights=[FlightResponse(**f) for f in flights])
    except CircuitBreakerError:
        raise HTTPException(status_code=503, detail="Service temporarily unavailable")
    except grpc.RpcError as e:
        handle_grpc_error(e)


@app.get("/flights/{flight_id}", response_model=FlightResponse)
def get_flight(flight_id: UUID):
    try:
        flight = flight_client.get_flight(str(flight_id))
        return FlightResponse(**flight)
    except CircuitBreakerError:
        raise HTTPException(status_code=503, detail="Service temporarily unavailable")
    except grpc.RpcError as e:
        handle_grpc_error(e)


@app.post("/bookings", response_model=BookingResponse, status_code=201)
def create_booking(request: CreateBookingRequest, db: Session = Depends(get_db)):
    try:
        flight = flight_client.get_flight(str(request.flight_id))
    except CircuitBreakerError:
        raise HTTPException(status_code=503, detail="Service temporarily unavailable")
    except grpc.RpcError as e:
        handle_grpc_error(e)
    
    booking = Booking(
        user_id=request.user_id,
        flight_id=request.flight_id,
        passenger_name=request.passenger_name,
        passenger_email=request.passenger_email,
        seat_count=request.seat_count,
        total_price=Decimal("0"),
        status="PENDING",
    )
    db.add(booking)
    db.flush()
    
    try:
        reservation = flight_client.reserve_seats(
            str(request.flight_id),
            str(booking.id),
            request.seat_count,
        )
    except CircuitBreakerError:
        db.rollback()
        raise HTTPException(status_code=503, detail="Service temporarily unavailable")
    except grpc.RpcError as e:
        db.rollback()
        handle_grpc_error(e)
    
    total_price = Decimal(str(flight["price"])) * request.seat_count
    booking.total_price = total_price
    booking.status = "CONFIRMED"
    
    db.commit()
    db.refresh(booking)
    
    logger.info(f"Created booking {booking.id} for flight {request.flight_id}")
    return booking


@app.get("/bookings/{booking_id}", response_model=BookingResponse)
def get_booking(booking_id: UUID, db: Session = Depends(get_db)):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    return booking


@app.post("/bookings/{booking_id}/cancel", response_model=BookingResponse)
def cancel_booking(booking_id: UUID, db: Session = Depends(get_db)):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    if booking.status != "CONFIRMED":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel booking with status {booking.status}"
        )
    
    try:
        flight_client.release_reservation(str(booking.id))
    except CircuitBreakerError:
        raise HTTPException(status_code=503, detail="Service temporarily unavailable")
    except grpc.RpcError as e:
        code = e.code()
        if code != grpc.StatusCode.NOT_FOUND:
            handle_grpc_error(e)
    
    booking.status = "CANCELLED"
    db.commit()
    db.refresh(booking)
    
    logger.info(f"Cancelled booking {booking.id}")
    return booking


@app.get("/bookings", response_model=BookingListResponse)
def list_bookings(
    user_id: Optional[UUID] = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(Booking)
    if user_id:
        query = query.filter(Booking.user_id == user_id)
    
    bookings = query.order_by(Booking.created_at.desc()).all()
    return BookingListResponse(bookings=bookings)


@app.get("/health")
def health_check():
    return {"status": "healthy"}
