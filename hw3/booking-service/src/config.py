import os


class Config:
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://booking_user:booking_password@localhost:5432/booking_db")
    
    FLIGHT_SERVICE_HOST = os.getenv("FLIGHT_SERVICE_HOST", "localhost")
    FLIGHT_SERVICE_PORT = int(os.getenv("FLIGHT_SERVICE_PORT", "50051"))
    
    GRPC_API_KEY = os.getenv("GRPC_API_KEY", "super-secret-api-key-12345")
    
    CB_FAILURE_THRESHOLD = int(os.getenv("CB_FAILURE_THRESHOLD", "5"))
    CB_RECOVERY_TIMEOUT = int(os.getenv("CB_RECOVERY_TIMEOUT", "30"))
    CB_HALF_OPEN_REQUESTS = int(os.getenv("CB_HALF_OPEN_REQUESTS", "1"))
    
    RETRY_MAX_ATTEMPTS = int(os.getenv("RETRY_MAX_ATTEMPTS", "3"))
    RETRY_INITIAL_DELAY_MS = int(os.getenv("RETRY_INITIAL_DELAY_MS", "100"))


config = Config()
