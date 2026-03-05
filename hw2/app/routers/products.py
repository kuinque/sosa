from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.generated.models import (
    ProductCreate,
    ProductListResponse,
    ProductResponse,
    ProductUpdate,
)
from app.models import Product

router = APIRouter(prefix="/products", tags=["Products"])


def _to_response(p: Product) -> ProductResponse:
    return ProductResponse(
        id=p.id,
        name=p.name,
        description=p.description,
        price=float(p.price),
        stock=p.stock,
        category=p.category,
        status=p.status,
        created_at=p.created_at,
        updated_at=p.updated_at,
    )


def _get_or_404(db: Session, product_id: int) -> Product:
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.post("", response_model=ProductResponse, status_code=201)
def create_product(body: ProductCreate, db: Session = Depends(get_db)):
    product = Product(
        name=body.name,
        description=body.description,
        price=body.price,
        stock=body.stock,
        category=body.category,
        status=body.status.value if body.status else "ACTIVE",
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return _to_response(product)


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(product_id: int, db: Session = Depends(get_db)):
    return _to_response(_get_or_404(db, product_id))


@router.get("", response_model=ProductListResponse)
def list_products(
    page: int = Query(default=0, ge=0),
    size: int = Query(default=20, ge=1, le=100),
    status: Optional[str] = Query(default=None),
    category: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
):
    query = db.query(Product)
    if status:
        query = query.filter(Product.status == status)
    if category:
        query = query.filter(Product.category == category)

    total = query.count()
    products = query.offset(page * size).limit(size).all()

    return ProductListResponse(
        items=[_to_response(p) for p in products],
        totalElements=total,
        page=page,
        size=size,
    )


@router.put("/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: int, body: ProductUpdate, db: Session = Depends(get_db)
):
    product = _get_or_404(db, product_id)

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "status" and value is not None:
            value = value.value if hasattr(value, "value") else value
        setattr(product, field, value)

    db.commit()
    db.refresh(product)
    return _to_response(product)


@router.delete("/{product_id}", response_model=ProductResponse)
def delete_product(product_id: int, db: Session = Depends(get_db)):
    product = _get_or_404(db, product_id)
    product.status = "ARCHIVED"
    db.commit()
    db.refresh(product)
    return _to_response(product)
