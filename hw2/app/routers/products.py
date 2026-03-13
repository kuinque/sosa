"""Products CRUD with role-based access control."""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth import TokenPayload, get_current_user, require_roles
from app.database import get_db
from app.exceptions import ApiException
from app.generated.models import (
    ProductCreate,
    ProductListResponse,
    ProductResponse,
    ProductUpdate,
)
from app.models import Product

router = APIRouter(prefix="/products", tags=["Products"])


def _ensure_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _to_response(p: Product) -> ProductResponse:
    return ProductResponse(
        id=p.id,
        name=p.name,
        description=p.description,
        price=float(p.price),
        stock=p.stock,
        category=p.category,
        status=p.status,
        seller_id=p.seller_id,
        created_at=_ensure_utc(p.created_at),
        updated_at=_ensure_utc(p.updated_at),
    )


def _get_or_404(db: Session, product_id: int) -> Product:
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise ApiException(404, "PRODUCT_NOT_FOUND", f"Product not found: {product_id}")
    return product


def _check_product_access(product: Product, user: TokenPayload) -> None:
    """Check if user can modify this product (SELLER only own, ADMIN any)."""
    if user.role == "ADMIN":
        return
    if user.role == "SELLER":
        if product.seller_id != user.user_id:
            raise ApiException(403, "ACCESS_DENIED", "You can only modify your own products")
        return
    raise ApiException(403, "ACCESS_DENIED", "Users cannot modify products")


@router.post("", response_model=ProductResponse, status_code=201)
def create_product(
    body: ProductCreate,
    db: Session = Depends(get_db),
    user: TokenPayload = Depends(require_roles("SELLER", "ADMIN")),
):
    """Create product. SELLER creates with own seller_id, ADMIN can create for anyone."""
    seller_id = user.user_id if user.role == "SELLER" else None

    product = Product(
        name=body.name,
        description=body.description,
        price=body.price,
        stock=body.stock,
        category=body.category,
        status=getattr(body.status, "value", body.status) or "ACTIVE",
        seller_id=seller_id,
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return _to_response(product)


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(
    product_id: int,
    db: Session = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """Get product by ID. Available to all roles."""
    return _to_response(_get_or_404(db, product_id))


@router.get("", response_model=ProductListResponse)
def list_products(
    page: int = Query(default=0, ge=0),
    size: int = Query(default=20, ge=1, le=100),
    status: Optional[str] = Query(default=None),
    category: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """List products with pagination and filtering. Available to all roles."""
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
    product_id: int,
    body: ProductUpdate,
    db: Session = Depends(get_db),
    user: TokenPayload = Depends(require_roles("SELLER", "ADMIN")),
):
    """Update product. SELLER only own, ADMIN any."""
    product = _get_or_404(db, product_id)
    _check_product_access(product, user)

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "status" and value is not None:
            value = value.value if hasattr(value, "value") else value
        setattr(product, field, value)

    db.commit()
    db.refresh(product)
    return _to_response(product)


@router.delete("/{product_id}", response_model=ProductResponse)
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    user: TokenPayload = Depends(require_roles("SELLER", "ADMIN")),
):
    """Soft delete (archive) product. SELLER only own, ADMIN any."""
    product = _get_or_404(db, product_id)
    _check_product_access(product, user)

    product.status = "ARCHIVED"
    db.commit()
    db.refresh(product)
    return _to_response(product)
