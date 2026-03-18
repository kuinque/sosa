import json
import logging
from typing import Optional, Any
from redis.sentinel import Sentinel

from .config import config

logger = logging.getLogger(__name__)


class CacheService:
    def __init__(self):
        self._sentinel: Optional[Sentinel] = None
        self._master = None
        
    def connect(self):
        try:
            self._sentinel = Sentinel(
                [(config.REDIS_SENTINEL_HOST, config.REDIS_SENTINEL_PORT)],
                socket_timeout=5.0
            )
            self._master = self._sentinel.master_for(
                config.REDIS_MASTER_NAME,
                socket_timeout=5.0
            )
            self._master.ping()
            logger.info("Connected to Redis Sentinel successfully")
        except Exception as e:
            logger.warning(f"Failed to connect to Redis Sentinel: {e}. Caching disabled.")
            self._sentinel = None
            self._master = None
    
    def _get_master(self):
        if self._master is None:
            return None
        try:
            self._master.ping()
            return self._master
        except Exception:
            self.connect()
            return self._master
    
    def get(self, key: str) -> Optional[Any]:
        master = self._get_master()
        if master is None:
            return None
        try:
            data = master.get(key)
            if data:
                logger.info(f"Cache HIT for key: {key}")
                return json.loads(data)
            logger.info(f"Cache MISS for key: {key}")
            return None
        except Exception as e:
            logger.warning(f"Cache get error for key {key}: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: int = None) -> bool:
        master = self._get_master()
        if master is None:
            return False
        try:
            ttl = ttl or config.CACHE_TTL_SECONDS
            master.setex(key, ttl, json.dumps(value, default=str))
            logger.info(f"Cache SET for key: {key} with TTL: {ttl}s")
            return True
        except Exception as e:
            logger.warning(f"Cache set error for key {key}: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        master = self._get_master()
        if master is None:
            return False
        try:
            master.delete(key)
            logger.info(f"Cache DELETE for key: {key}")
            return True
        except Exception as e:
            logger.warning(f"Cache delete error for key {key}: {e}")
            return False
    
    def delete_pattern(self, pattern: str) -> bool:
        master = self._get_master()
        if master is None:
            return False
        try:
            keys = master.keys(pattern)
            if keys:
                master.delete(*keys)
                logger.info(f"Cache DELETE pattern: {pattern}, deleted {len(keys)} keys")
            return True
        except Exception as e:
            logger.warning(f"Cache delete pattern error for {pattern}: {e}")
            return False
    
    def invalidate_flight(self, flight_id: str):
        self.delete(f"flight:{flight_id}")
        self.delete_pattern("search:*")
    
    def invalidate_search_cache(self):
        self.delete_pattern("search:*")


cache_service = CacheService()
