import logging
from datetime import datetime, date
from uuid import UUID
from typing import Optional, List

import grpc
from google.protobuf.timestamp_pb2 import Timestamp
from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from .database import SessionLocal
from .models import Flight, SeatReservation
from .cache import cache_service
from .generated import flight_pb2, flight_pb2_grpc

logger = logging.getLogger(__name__)


def datetime_to_timestamp(dt: datetime) -> Timestamp:
    ts = Timestamp()
    ts.FromDatetime(dt)
    return ts


def timestamp_to_datetime(ts: Timestamp) -> Optional[datetime]:
    if ts.seconds == 0 and ts.nanos == 0:
        return None
    return ts.ToDatetime()


def flight_to_proto(flight: Flight) -> flight_pb2.Flight:
    status_map = {
        "SCHEDULED": flight_pb2.FLIGHT_STATUS_SCHEDULED,
        "DEPARTED": flight_pb2.FLIGHT_STATUS_DEPARTED,
        "CANCELLED": flight_pb2.FLIGHT_STATUS_CANCELLED,
        "COMPLETED": flight_pb2.FLIGHT_STATUS_COMPLETED,
    }
    return flight_pb2.Flight(
        id=str(flight.id),
        flight_number=flight.flight_number,
        airline=flight.airline,
        origin=flight.origin,
        destination=flight.destination,
        departure_time=datetime_to_timestamp(flight.departure_time),
        arrival_time=datetime_to_timestamp(flight.arrival_time),
        total_seats=flight.total_seats,
        available_seats=flight.available_seats,
        price=float(flight.price),
        status=status_map.get(flight.status, flight_pb2.FLIGHT_STATUS_UNSPECIFIED),
    )


def flight_to_dict(flight: Flight) -> dict:
    return {
        "id": str(flight.id),
        "flight_number": flight.flight_number,
        "airline": flight.airline,
        "origin": flight.origin,
        "destination": flight.destination,
        "departure_time": flight.departure_time.isoformat(),
        "arrival_time": flight.arrival_time.isoformat(),
        "total_seats": flight.total_seats,
        "available_seats": flight.available_seats,
        "price": float(flight.price),
        "status": flight.status,
    }


def dict_to_flight_proto(data: dict) -> flight_pb2.Flight:
    status_map = {
        "SCHEDULED": flight_pb2.FLIGHT_STATUS_SCHEDULED,
        "DEPARTED": flight_pb2.FLIGHT_STATUS_DEPARTED,
        "CANCELLED": flight_pb2.FLIGHT_STATUS_CANCELLED,
        "COMPLETED": flight_pb2.FLIGHT_STATUS_COMPLETED,
    }
    departure_ts = Timestamp()
    departure_ts.FromDatetime(datetime.fromisoformat(data["departure_time"]))
    arrival_ts = Timestamp()
    arrival_ts.FromDatetime(datetime.fromisoformat(data["arrival_time"]))
    
    return flight_pb2.Flight(
        id=data["id"],
        flight_number=data["flight_number"],
        airline=data["airline"],
        origin=data["origin"],
        destination=data["destination"],
        departure_time=departure_ts,
        arrival_time=arrival_ts,
        total_seats=data["total_seats"],
        available_seats=data["available_seats"],
        price=data["price"],
        status=status_map.get(data["status"], flight_pb2.FLIGHT_STATUS_UNSPECIFIED),
    )


def reservation_to_proto(reservation: SeatReservation) -> flight_pb2.SeatReservation:
    status_map = {
        "ACTIVE": flight_pb2.RESERVATION_STATUS_ACTIVE,
        "RELEASED": flight_pb2.RESERVATION_STATUS_RELEASED,
        "EXPIRED": flight_pb2.RESERVATION_STATUS_EXPIRED,
    }
    return flight_pb2.SeatReservation(
        id=str(reservation.id),
        flight_id=str(reservation.flight_id),
        booking_id=str(reservation.booking_id),
        seat_count=reservation.seat_count,
        status=status_map.get(reservation.status, flight_pb2.RESERVATION_STATUS_UNSPECIFIED),
        created_at=datetime_to_timestamp(reservation.created_at),
    )


class FlightServiceServicer(flight_pb2_grpc.FlightServiceServicer):
    
    def SearchFlights(self, request, context):
        origin = request.origin.upper()
        destination = request.destination.upper()
        
        if not origin or not destination:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "origin and destination are required")
        
        search_date = timestamp_to_datetime(request.date)
        
        cache_key = f"search:{origin}:{destination}:{search_date.date() if search_date else 'all'}"
        cached = cache_service.get(cache_key)
        if cached:
            flights = [dict_to_flight_proto(f) for f in cached]
            return flight_pb2.SearchFlightsResponse(flights=flights)
        
        db = SessionLocal()
        try:
            query = db.query(Flight).filter(
                and_(
                    Flight.origin == origin,
                    Flight.destination == destination,
                    Flight.status == "SCHEDULED"
                )
            )
            
            if search_date:
                query = query.filter(
                    func.date(Flight.departure_time) == search_date.date()
                )
            
            flights = query.order_by(Flight.departure_time).all()
            
            flights_data = [flight_to_dict(f) for f in flights]
            cache_service.set(cache_key, flights_data)
            
            flights_proto = [flight_to_proto(f) for f in flights]
            return flight_pb2.SearchFlightsResponse(flights=flights_proto)
        finally:
            db.close()
    
    def GetFlight(self, request, context):
        flight_id = request.flight_id
        
        if not flight_id:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "flight_id is required")
        
        try:
            UUID(flight_id)
        except ValueError:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "Invalid flight_id format")
        
        cache_key = f"flight:{flight_id}"
        cached = cache_service.get(cache_key)
        if cached:
            return flight_pb2.GetFlightResponse(flight=dict_to_flight_proto(cached))
        
        db = SessionLocal()
        try:
            flight = db.query(Flight).filter(Flight.id == flight_id).first()
            
            if not flight:
                context.abort(grpc.StatusCode.NOT_FOUND, f"Flight {flight_id} not found")
            
            cache_service.set(cache_key, flight_to_dict(flight))
            
            return flight_pb2.GetFlightResponse(flight=flight_to_proto(flight))
        finally:
            db.close()
    
    def ReserveSeats(self, request, context):
        flight_id = request.flight_id
        booking_id = request.booking_id
        seat_count = request.seat_count
        
        if not flight_id or not booking_id:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "flight_id and booking_id are required")
        
        if seat_count <= 0:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "seat_count must be positive")
        
        try:
            UUID(flight_id)
            UUID(booking_id)
        except ValueError:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "Invalid UUID format")
        
        db = SessionLocal()
        try:
            existing = db.query(SeatReservation).filter(
                SeatReservation.booking_id == booking_id
            ).first()
            
            if existing:
                if existing.status == "ACTIVE":
                    logger.info(f"Idempotent reservation found for booking {booking_id}")
                    return flight_pb2.ReserveSeatsResponse(reservation=reservation_to_proto(existing))
                else:
                    context.abort(grpc.StatusCode.FAILED_PRECONDITION, 
                                  f"Reservation for booking {booking_id} already exists with status {existing.status}")
            
            flight = db.query(Flight).filter(
                Flight.id == flight_id
            ).with_for_update().first()
            
            if not flight:
                context.abort(grpc.StatusCode.NOT_FOUND, f"Flight {flight_id} not found")
            
            if flight.status != "SCHEDULED":
                context.abort(grpc.StatusCode.FAILED_PRECONDITION, 
                              f"Flight is not available for booking (status: {flight.status})")
            
            if flight.available_seats < seat_count:
                context.abort(grpc.StatusCode.RESOURCE_EXHAUSTED, 
                              f"Not enough seats. Available: {flight.available_seats}, requested: {seat_count}")
            
            flight.available_seats -= seat_count
            
            reservation = SeatReservation(
                flight_id=flight_id,
                booking_id=booking_id,
                seat_count=seat_count,
                status="ACTIVE"
            )
            db.add(reservation)
            
            db.commit()
            db.refresh(reservation)
            
            cache_service.invalidate_flight(flight_id)
            
            logger.info(f"Reserved {seat_count} seats on flight {flight_id} for booking {booking_id}")
            return flight_pb2.ReserveSeatsResponse(reservation=reservation_to_proto(reservation))
            
        except grpc.RpcError:
            db.rollback()
            raise
        except Exception as e:
            db.rollback()
            logger.error(f"Error reserving seats: {e}")
            context.abort(grpc.StatusCode.INTERNAL, str(e))
        finally:
            db.close()
    
    def ReleaseReservation(self, request, context):
        booking_id = request.booking_id
        
        if not booking_id:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "booking_id is required")
        
        try:
            UUID(booking_id)
        except ValueError:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "Invalid booking_id format")
        
        db = SessionLocal()
        try:
            reservation = db.query(SeatReservation).filter(
                SeatReservation.booking_id == booking_id
            ).with_for_update().first()
            
            if not reservation:
                context.abort(grpc.StatusCode.NOT_FOUND, 
                              f"Reservation for booking {booking_id} not found")
            
            if reservation.status != "ACTIVE":
                context.abort(grpc.StatusCode.FAILED_PRECONDITION,
                              f"Reservation is not active (status: {reservation.status})")
            
            flight = db.query(Flight).filter(
                Flight.id == reservation.flight_id
            ).with_for_update().first()
            
            if flight:
                flight.available_seats += reservation.seat_count
            
            reservation.status = "RELEASED"
            
            db.commit()
            db.refresh(reservation)
            
            if flight:
                cache_service.invalidate_flight(str(flight.id))
            
            logger.info(f"Released reservation for booking {booking_id}")
            return flight_pb2.ReleaseReservationResponse(reservation=reservation_to_proto(reservation))
            
        except grpc.RpcError:
            db.rollback()
            raise
        except Exception as e:
            db.rollback()
            logger.error(f"Error releasing reservation: {e}")
            context.abort(grpc.StatusCode.INTERNAL, str(e))
        finally:
            db.close()
