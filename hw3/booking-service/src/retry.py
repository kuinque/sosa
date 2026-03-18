import logging
import time
from functools import wraps
from typing import Callable, Set

import grpc

from .config import config

logger = logging.getLogger(__name__)

RETRYABLE_CODES: Set[grpc.StatusCode] = {
    grpc.StatusCode.UNAVAILABLE,
    grpc.StatusCode.DEADLINE_EXCEEDED,
}

NON_RETRYABLE_CODES: Set[grpc.StatusCode] = {
    grpc.StatusCode.INVALID_ARGUMENT,
    grpc.StatusCode.NOT_FOUND,
    grpc.StatusCode.RESOURCE_EXHAUSTED,
    grpc.StatusCode.UNAUTHENTICATED,
    grpc.StatusCode.PERMISSION_DENIED,
    grpc.StatusCode.FAILED_PRECONDITION,
}


def with_retry(
    max_attempts: int = None,
    initial_delay_ms: int = None,
):
    max_attempts = max_attempts or config.RETRY_MAX_ATTEMPTS
    initial_delay_ms = initial_delay_ms or config.RETRY_INITIAL_DELAY_MS
    
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            delay_ms = initial_delay_ms
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except grpc.RpcError as e:
                    last_exception = e
                    code = e.code()
                    
                    if code in NON_RETRYABLE_CODES:
                        logger.warning(
                            f"Non-retryable gRPC error (code={code.name}): {e.details()}"
                        )
                        raise
                    
                    if code in RETRYABLE_CODES:
                        if attempt < max_attempts:
                            logger.warning(
                                f"Retryable gRPC error (code={code.name}), "
                                f"attempt {attempt}/{max_attempts}, "
                                f"retrying in {delay_ms}ms: {e.details()}"
                            )
                            time.sleep(delay_ms / 1000.0)
                            delay_ms *= 2
                            continue
                        else:
                            logger.error(
                                f"Max retries exceeded for gRPC call "
                                f"(code={code.name}): {e.details()}"
                            )
                            raise
                    
                    logger.warning(
                        f"Unknown gRPC error (code={code.name}): {e.details()}"
                    )
                    raise
                except Exception as e:
                    logger.error(f"Unexpected error in gRPC call: {e}")
                    raise
            
            raise last_exception
        
        return wrapper
    return decorator
