import logging
from datetime import datetime, timedelta
from decimal import Decimal

from .database import SessionLocal
from .models import Flight

logger = logging.getLogger(__name__)


def seed_flights():
    db = SessionLocal()
    try:
        existing = db.query(Flight).first()
        if existing:
            logger.info("Flights already seeded, skipping")
            return
        
        base_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        flights_data = [
            {
                "flight_number": "SU1234",
                "airline": "Aeroflot",
                "origin": "SVO",
                "destination": "LED",
                "departure_time": base_date + timedelta(days=1, hours=8),
                "arrival_time": base_date + timedelta(days=1, hours=9, minutes=30),
                "total_seats": 180,
                "available_seats": 180,
                "price": Decimal("5500.00"),
            },
            {
                "flight_number": "SU1235",
                "airline": "Aeroflot",
                "origin": "SVO",
                "destination": "LED",
                "departure_time": base_date + timedelta(days=1, hours=14),
                "arrival_time": base_date + timedelta(days=1, hours=15, minutes=30),
                "total_seats": 180,
                "available_seats": 180,
                "price": Decimal("6000.00"),
            },
            {
                "flight_number": "S71001",
                "airline": "S7 Airlines",
                "origin": "DME",
                "destination": "LED",
                "departure_time": base_date + timedelta(days=1, hours=10),
                "arrival_time": base_date + timedelta(days=1, hours=11, minutes=45),
                "total_seats": 150,
                "available_seats": 150,
                "price": Decimal("4800.00"),
            },
            {
                "flight_number": "SU2001",
                "airline": "Aeroflot",
                "origin": "LED",
                "destination": "SVO",
                "departure_time": base_date + timedelta(days=1, hours=12),
                "arrival_time": base_date + timedelta(days=1, hours=13, minutes=30),
                "total_seats": 180,
                "available_seats": 180,
                "price": Decimal("5200.00"),
            },
            {
                "flight_number": "DP405",
                "airline": "Pobeda",
                "origin": "VKO",
                "destination": "AER",
                "departure_time": base_date + timedelta(days=2, hours=7),
                "arrival_time": base_date + timedelta(days=2, hours=9, minutes=30),
                "total_seats": 189,
                "available_seats": 189,
                "price": Decimal("3500.00"),
            },
            {
                "flight_number": "U6101",
                "airline": "Ural Airlines",
                "origin": "SVO",
                "destination": "SVX",
                "departure_time": base_date + timedelta(days=2, hours=9),
                "arrival_time": base_date + timedelta(days=2, hours=11, minutes=30),
                "total_seats": 160,
                "available_seats": 160,
                "price": Decimal("7200.00"),
            },
            {
                "flight_number": "SU1500",
                "airline": "Aeroflot",
                "origin": "SVO",
                "destination": "KZN",
                "departure_time": base_date + timedelta(days=3, hours=6),
                "arrival_time": base_date + timedelta(days=3, hours=7, minutes=45),
                "total_seats": 140,
                "available_seats": 140,
                "price": Decimal("6500.00"),
            },
            {
                "flight_number": "SU1236",
                "airline": "Aeroflot",
                "origin": "SVO",
                "destination": "LED",
                "departure_time": base_date + timedelta(days=2, hours=8),
                "arrival_time": base_date + timedelta(days=2, hours=9, minutes=30),
                "total_seats": 180,
                "available_seats": 180,
                "price": Decimal("5700.00"),
            },
        ]
        
        for flight_data in flights_data:
            flight = Flight(**flight_data)
            db.add(flight)
        
        db.commit()
        logger.info(f"Seeded {len(flights_data)} flights")
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error seeding flights: {e}")
    finally:
        db.close()
