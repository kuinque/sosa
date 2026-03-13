"""Request logging middleware with JSON format."""
import json
import logging
import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger("api")
logger.setLevel(logging.INFO)

if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware that logs every API request in JSON format."""

    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        start_time = time.time()

        body = None
        if request.method in ("POST", "PUT", "DELETE"):
            try:
                body_bytes = await request.body()
                if body_bytes:
                    body = json.loads(body_bytes)
                    if isinstance(body, dict) and "password" in body:
                        body = {**body, "password": "***MASKED***"}
            except Exception:
                body = None

        response = await call_next(request)

        duration_ms = round((time.time() - start_time) * 1000, 2)

        user_id = getattr(request.state, "user_id", None)
        if user_id is None:
            user_id_header = request.headers.get("X-User-Id")
            if user_id_header:
                try:
                    user_id = int(user_id_header)
                except ValueError:
                    pass

        log_data = {
            "request_id": request_id,
            "method": request.method,
            "endpoint": request.url.path,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
            "user_id": user_id,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }

        if body and request.method in ("POST", "PUT", "DELETE"):
            log_data["request_body"] = body

        logger.info(json.dumps(log_data))

        response.headers["X-Request-Id"] = request_id

        return response
