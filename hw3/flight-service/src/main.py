import logging
import time
from concurrent import futures

import grpc

from .config import config
from .database import engine, Base
from .models import Flight, SeatReservation
from .cache import cache_service
from .auth import create_auth_interceptor
from .service import FlightServiceServicer
from .generated import flight_pb2_grpc
from .seed import seed_flights

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


def serve():
    wait_for_db()
    run_migrations()
    seed_flights()
    
    cache_service.connect()
    
    auth_interceptor = create_auth_interceptor()
    
    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=10),
        interceptors=[auth_interceptor]
    )
    
    flight_pb2_grpc.add_FlightServiceServicer_to_server(
        FlightServiceServicer(), server
    )
    
    server.add_insecure_port(f'[::]:{config.GRPC_PORT}')
    server.start()
    
    logger.info(f"Flight Service started on port {config.GRPC_PORT}")
    
    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        server.stop(0)


if __name__ == "__main__":
    serve()
