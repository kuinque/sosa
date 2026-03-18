import os


class Config:
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://flight_user:flight_password@localhost:5432/flight_db")
    
    REDIS_SENTINEL_HOST = os.getenv("REDIS_SENTINEL_HOST", "localhost")
    REDIS_SENTINEL_PORT = int(os.getenv("REDIS_SENTINEL_PORT", "26379"))
    REDIS_MASTER_NAME = os.getenv("REDIS_MASTER_NAME", "mymaster")
    
    GRPC_API_KEY = os.getenv("GRPC_API_KEY", "super-secret-api-key-12345")
    GRPC_PORT = int(os.getenv("GRPC_PORT", "50051"))
    
    CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "300"))


config = Config()
