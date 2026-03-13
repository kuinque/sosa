"""FastAPI application with middleware and exception handlers."""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.exceptions import ApiException
from app.middleware.logging import RequestLoggingMiddleware
from app.routers.auth import router as auth_router
from app.routers.orders import router as orders_router
from app.routers.products import router as products_router
from app.routers.promo_codes import router as promo_codes_router

app = FastAPI(
    title="Marketplace API",
    version="1.0.0",
    description="API сервиса маркетплейса с JWT-авторизацией и ролевой моделью",
)

app.add_middleware(RequestLoggingMiddleware)


@app.exception_handler(ApiException)
async def api_exception_handler(request: Request, exc: ApiException):
    """Handle ApiException and return structured error response."""
    content = {
        "error_code": exc.error_code,
        "message": exc.message,
    }
    if exc.details is not None:
        content["details"] = exc.details
    return JSONResponse(status_code=exc.status_code, content=content)


app.include_router(auth_router)
app.include_router(products_router)
app.include_router(orders_router)
app.include_router(promo_codes_router)


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "ok"}
