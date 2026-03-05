from fastapi import FastAPI

from app.routers.products import router as products_router

app = FastAPI(
    title="Marketplace API",
    version="1.0.0",
    description="API сервиса маркетплейса",
)

app.include_router(products_router)


@app.get("/health")
def health():
    return {"status": "ok"}
