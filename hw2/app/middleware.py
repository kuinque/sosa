import json
import logging
import time
import uuid
from datetime import datetime

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api")

for handler in logger.handlers:
    handler.setFormatter(logging.Formatter("%(message)s"))


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-Id") or str(uuid.uuid4())
        request.state.request_id = request_id

        user_id = request.headers.get("X-User-Id")

        start_time = time.perf_counter()

        body = None
        if request.method in ("POST", "PUT", "DELETE"):
            try:
                body_bytes = await request.body()
                if body_bytes:
                    body = json.loads(body_bytes)
                    if isinstance(body, dict) and "password" in body:
                        body["password"] = "***"
            except Exception:
                body = None

        response = await call_next(request)

        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

        log_data = {
            "request_id": request_id,
            "method": request.method,
            "endpoint": request.url.path,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
            "user_id": int(user_id) if user_id else None,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

        if body is not None:
            log_data["request_body"] = body

        logger.info(json.dumps(log_data))

        response.headers["X-Request-Id"] = request_id

        return response
