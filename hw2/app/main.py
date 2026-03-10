from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError

from app.exceptions import AppException
from app.error_handlers import app_exception_handler, validation_exception_handler
from app.middleware import LoggingMiddleware
from app.routers.auth import router as auth_router
from app.routers.products import router as products_router
from app.routers.orders import router as orders_router
from app.routers.promo_codes import router as promo_codes_router

app = FastAPI(
    title="Marketplace API",
    version="1.0.0",
    description="API сервиса маркетплейса",
)

app.add_middleware(LoggingMiddleware)

app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)

app.include_router(auth_router)
app.include_router(products_router)
app.include_router(orders_router)
app.include_router(promo_codes_router)


@app.get("/health")
def health():
    return {"status": "ok"}
