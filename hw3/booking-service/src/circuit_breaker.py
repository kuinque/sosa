import logging
import time
import threading
from enum import Enum
from typing import Callable, Any
from functools import wraps

from .config import config

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitBreakerError(Exception):
    pass


class CircuitBreaker:
    def __init__(
        self,
        failure_threshold: int = None,
        recovery_timeout: int = None,
        half_open_requests: int = None,
    ):
        self.failure_threshold = failure_threshold or config.CB_FAILURE_THRESHOLD
        self.recovery_timeout = recovery_timeout or config.CB_RECOVERY_TIMEOUT
        self.half_open_requests = half_open_requests or config.CB_HALF_OPEN_REQUESTS
        
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time = 0
        self._half_open_calls = 0
        self._lock = threading.Lock()
    
    @property
    def state(self) -> CircuitState:
        with self._lock:
            if self._state == CircuitState.OPEN:
                if time.time() - self._last_failure_time >= self.recovery_timeout:
                    self._transition_to(CircuitState.HALF_OPEN)
            return self._state
    
    def _transition_to(self, new_state: CircuitState):
        if self._state != new_state:
            logger.info(f"Circuit Breaker: {self._state.value} → {new_state.value}")
            self._state = new_state
            if new_state == CircuitState.HALF_OPEN:
                self._half_open_calls = 0
            elif new_state == CircuitState.CLOSED:
                self._failure_count = 0
    
    def _record_success(self):
        with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._half_open_calls += 1
                if self._half_open_calls >= self.half_open_requests:
                    self._transition_to(CircuitState.CLOSED)
            elif self._state == CircuitState.CLOSED:
                self._failure_count = 0
    
    def _record_failure(self):
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()
            
            if self._state == CircuitState.HALF_OPEN:
                self._transition_to(CircuitState.OPEN)
            elif self._state == CircuitState.CLOSED:
                if self._failure_count >= self.failure_threshold:
                    self._transition_to(CircuitState.OPEN)
    
    def can_execute(self) -> bool:
        state = self.state
        if state == CircuitState.CLOSED:
            return True
        if state == CircuitState.OPEN:
            return False
        if state == CircuitState.HALF_OPEN:
            with self._lock:
                return self._half_open_calls < self.half_open_requests
        return False
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        if not self.can_execute():
            raise CircuitBreakerError(
                f"Circuit breaker is {self.state.value}. Service temporarily unavailable."
            )
        
        try:
            result = func(*args, **kwargs)
            self._record_success()
            return result
        except Exception as e:
            self._record_failure()
            raise


circuit_breaker = CircuitBreaker()


def with_circuit_breaker(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        return circuit_breaker.call(func, *args, **kwargs)
    return wrapper
