import logging
from typing import Optional, List
from datetime import date

import grpc
from google.protobuf.timestamp_pb2 import Timestamp

from .config import config
from .circuit_breaker import circuit_breaker, CircuitBreakerError
from .retry import with_retry
from .generated import flight_pb2, flight_pb2_grpc

logger = logging.getLogger(__name__)


class FlightClient:
    def __init__(self):
        self._channel: Optional[grpc.Channel] = None
        self._stub: Optional[flight_pb2_grpc.FlightServiceStub] = None
    
    def connect(self):
        target = f"{config.FLIGHT_SERVICE_HOST}:{config.FLIGHT_SERVICE_PORT}"
        self._channel = grpc.insecure_channel(target)
        self._stub = flight_pb2_grpc.FlightServiceStub(self._channel)
        logger.info(f"Connected to Flight Service at {target}")
    
    def _get_metadata(self):
        return [("x-api-key", config.GRPC_API_KEY)]
    
    def _call_with_circuit_breaker(self, func, *args, **kwargs):
        return circuit_breaker.call(func, *args, **kwargs)
    
    @with_retry()
    def _search_flights_internal(
        self, origin: str, destination: str, search_date: Optional[date] = None
    ) -> List[dict]:
        request = flight_pb2.SearchFlightsRequest(
            origin=origin,
            destination=destination,
        )
        
        if search_date:
            ts = Timestamp()
            from datetime import datetime
            ts.FromDatetime(datetime.combine(search_date, datetime.min.time()))
            request.date.CopyFrom(ts)
        
        response = self._stub.SearchFlights(request, metadata=self._get_metadata())
        
        return [self._flight_to_dict(f) for f in response.flights]
    
    def search_flights(
        self, origin: str, destination: str, search_date: Optional[date] = None
    ) -> List[dict]:
        try:
            return self._call_with_circuit_breaker(
                self._search_flights_internal, origin, destination, search_date
            )
        except CircuitBreakerError as e:
            logger.error(f"Circuit breaker open: {e}")
            raise
    
    @with_retry()
    def _get_flight_internal(self, flight_id: str) -> Optional[dict]:
        request = flight_pb2.GetFlightRequest(flight_id=flight_id)
        response = self._stub.GetFlight(request, metadata=self._get_metadata())
        return self._flight_to_dict(response.flight)
    
    def get_flight(self, flight_id: str) -> Optional[dict]:
        try:
            return self._call_with_circuit_breaker(
                self._get_flight_internal, flight_id
            )
        except CircuitBreakerError as e:
            logger.error(f"Circuit breaker open: {e}")
            raise
    
    @with_retry()
    def _reserve_seats_internal(
        self, flight_id: str, booking_id: str, seat_count: int
    ) -> dict:
        request = flight_pb2.ReserveSeatsRequest(
            flight_id=flight_id,
            booking_id=booking_id,
            seat_count=seat_count,
        )
        response = self._stub.ReserveSeats(request, metadata=self._get_metadata())
        return self._reservation_to_dict(response.reservation)
    
    def reserve_seats(
        self, flight_id: str, booking_id: str, seat_count: int
    ) -> dict:
        try:
            return self._call_with_circuit_breaker(
                self._reserve_seats_internal, flight_id, booking_id, seat_count
            )
        except CircuitBreakerError as e:
            logger.error(f"Circuit breaker open: {e}")
            raise
    
    @with_retry()
    def _release_reservation_internal(self, booking_id: str) -> dict:
        request = flight_pb2.ReleaseReservationRequest(booking_id=booking_id)
        response = self._stub.ReleaseReservation(request, metadata=self._get_metadata())
        return self._reservation_to_dict(response.reservation)
    
    def release_reservation(self, booking_id: str) -> dict:
        try:
            return self._call_with_circuit_breaker(
                self._release_reservation_internal, booking_id
            )
        except CircuitBreakerError as e:
            logger.error(f"Circuit breaker open: {e}")
            raise
    
    def _flight_to_dict(self, flight: flight_pb2.Flight) -> dict:
        status_map = {
            flight_pb2.FLIGHT_STATUS_SCHEDULED: "SCHEDULED",
            flight_pb2.FLIGHT_STATUS_DEPARTED: "DEPARTED",
            flight_pb2.FLIGHT_STATUS_CANCELLED: "CANCELLED",
            flight_pb2.FLIGHT_STATUS_COMPLETED: "COMPLETED",
        }
        return {
            "id": flight.id,
            "flight_number": flight.flight_number,
            "airline": flight.airline,
            "origin": flight.origin,
            "destination": flight.destination,
            "departure_time": flight.departure_time.ToDatetime().isoformat(),
            "arrival_time": flight.arrival_time.ToDatetime().isoformat(),
            "total_seats": flight.total_seats,
            "available_seats": flight.available_seats,
            "price": flight.price,
            "status": status_map.get(flight.status, "UNKNOWN"),
        }
    
    def _reservation_to_dict(self, reservation: flight_pb2.SeatReservation) -> dict:
        status_map = {
            flight_pb2.RESERVATION_STATUS_ACTIVE: "ACTIVE",
            flight_pb2.RESERVATION_STATUS_RELEASED: "RELEASED",
            flight_pb2.RESERVATION_STATUS_EXPIRED: "EXPIRED",
        }
        return {
            "id": reservation.id,
            "flight_id": reservation.flight_id,
            "booking_id": reservation.booking_id,
            "seat_count": reservation.seat_count,
            "status": status_map.get(reservation.status, "UNKNOWN"),
            "created_at": reservation.created_at.ToDatetime().isoformat(),
        }


flight_client = FlightClient()
