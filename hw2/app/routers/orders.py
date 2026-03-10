from datetime import datetime, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import CurrentUser, get_current_user
from app.config import settings
from app.database import get_db
from app.exceptions import (
    AccessDenied,
    InsufficientStock,
    InvalidStateTransition,
    OrderHasActive,
    OrderLimitExceeded,
    OrderNotFound,
    OrderOwnershipViolation,
    ProductInactive,
    ProductNotFound,
    PromoCodeInvalid,
    PromoCodeMinAmount,
)
from app.generated.models import (
    OrderCreate,
    OrderItemResponse,
    OrderResponse,
    OrderUpdate,
)
from app.models import Order, OrderItem, Product, PromoCode, UserOperation

router = APIRouter(prefix="/orders", tags=["Orders"])


def _to_response(order: Order) -> OrderResponse:
    return OrderResponse(
        id=order.id,
        user_id=order.user_id,
        status=order.status,
        promo_code_id=order.promo_code_id,
        total_amount=float(order.total_amount),
        discount_amount=float(order.discount_amount),
        items=[
            OrderItemResponse(
                id=item.id,
                product_id=item.product_id,
                quantity=item.quantity,
                price_at_order=float(item.price_at_order),
            )
            for item in order.items
        ],
        created_at=order.created_at,
        updated_at=order.updated_at,
    )


def _check_rate_limit(db: Session, user_id: int, operation_type: str):
    cutoff = datetime.utcnow() - timedelta(minutes=settings.order_rate_limit_minutes)
    last_op = (
        db.query(UserOperation)
        .filter(
            UserOperation.user_id == user_id,
            UserOperation.operation_type == operation_type,
            UserOperation.created_at > cutoff,
        )
        .first()
    )
    if last_op:
        raise OrderLimitExceeded(operation_type)


def _check_active_orders(db: Session, user_id: int):
    active = (
        db.query(Order)
        .filter(
            Order.user_id == user_id,
            Order.status.in_(["CREATED", "PAYMENT_PENDING"]),
        )
        .first()
    )
    if active:
        raise OrderHasActive(user_id)


def _validate_products(db: Session, items: list) -> list[tuple[Product, int]]:
    result = []
    insufficient = []

    for item in items:
        product = db.query(Product).filter(Product.id == item.product_id).first()
        if not product:
            raise ProductNotFound(item.product_id)
        if product.status != "ACTIVE":
            raise ProductInactive(item.product_id)
        if product.stock < item.quantity:
            insufficient.append({
                "product_id": item.product_id,
                "requested": item.quantity,
                "available": product.stock,
            })
        result.append((product, item.quantity))

    if insufficient:
        raise InsufficientStock(insufficient)

    return result


def _apply_promo_code(
    db: Session, code: str, subtotal: Decimal
) -> tuple[PromoCode | None, Decimal]:
    promo = db.query(PromoCode).filter(PromoCode.code == code).first()
    if not promo:
        raise PromoCodeInvalid(code, "not found")
    if not promo.active:
        raise PromoCodeInvalid(code, "inactive")
    if promo.current_uses >= promo.max_uses:
        raise PromoCodeInvalid(code, "max uses exceeded")

    now = datetime.utcnow()
    if now < promo.valid_from or now > promo.valid_until:
        raise PromoCodeInvalid(code, "expired or not yet valid")

    if subtotal < promo.min_order_amount:
        raise PromoCodeMinAmount(code, float(promo.min_order_amount), float(subtotal))

    if promo.discount_type == "PERCENTAGE":
        discount = subtotal * promo.discount_value / 100
        max_discount = subtotal * Decimal("0.7")
        discount = min(discount, max_discount)
    else:
        discount = min(promo.discount_value, subtotal)

    return promo, discount


def _check_order_access(order: Order, user: CurrentUser):
    if user.role == "ADMIN":
        return
    if order.user_id != user.user_id:
        raise OrderOwnershipViolation(order.id)


@router.post("", response_model=OrderResponse, status_code=201)
def create_order(
    body: OrderCreate,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    if user.role == "SELLER":
        raise AccessDenied("SELLER cannot create orders")

    user_id = user.user_id

    _check_rate_limit(db, user_id, "CREATE_ORDER")
    _check_active_orders(db, user_id)

    validated = _validate_products(db, body.items)

    for product, qty in validated:
        product.stock -= qty

    subtotal = sum(
        Decimal(str(product.price)) * qty for product, qty in validated
    )

    discount = Decimal(0)
    promo = None
    if body.promo_code:
        promo, discount = _apply_promo_code(db, body.promo_code, subtotal)
        promo.current_uses += 1

    total = subtotal - discount

    order = Order(
        user_id=user_id,
        status="CREATED",
        promo_code_id=promo.id if promo else None,
        total_amount=total,
        discount_amount=discount,
    )
    db.add(order)
    db.flush()

    for product, qty in validated:
        item = OrderItem(
            order_id=order.id,
            product_id=product.id,
            quantity=qty,
            price_at_order=product.price,
        )
        db.add(item)

    op = UserOperation(user_id=user_id, operation_type="CREATE_ORDER")
    db.add(op)

    db.commit()
    db.refresh(order)
    return _to_response(order)


@router.get("/{order_id}", response_model=OrderResponse)
def get_order(
    order_id: int,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    if user.role == "SELLER":
        raise AccessDenied("SELLER cannot view orders")

    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise OrderNotFound(order_id)

    _check_order_access(order, user)
    return _to_response(order)


@router.put("/{order_id}", response_model=OrderResponse)
def update_order(
    order_id: int,
    body: OrderUpdate,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    if user.role == "SELLER":
        raise AccessDenied("SELLER cannot update orders")

    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise OrderNotFound(order_id)

    _check_order_access(order, user)

    if order.status != "CREATED":
        raise InvalidStateTransition(order.status, "update")

    _check_rate_limit(db, user.user_id, "UPDATE_ORDER")

    for item in order.items:
        product = db.query(Product).filter(Product.id == item.product_id).first()
        if product:
            product.stock += item.quantity

    db.query(OrderItem).filter(OrderItem.order_id == order.id).delete()

    validated = _validate_products(db, body.items)

    for product, qty in validated:
        product.stock -= qty

    subtotal = sum(
        Decimal(str(product.price)) * qty for product, qty in validated
    )

    discount = Decimal(0)
    if order.promo_code_id:
        promo = db.query(PromoCode).filter(PromoCode.id == order.promo_code_id).first()
        if promo and subtotal >= promo.min_order_amount:
            if promo.discount_type == "PERCENTAGE":
                discount = subtotal * promo.discount_value / 100
                max_discount = subtotal * Decimal("0.7")
                discount = min(discount, max_discount)
            else:
                discount = min(promo.discount_value, subtotal)
        else:
            if promo:
                promo.current_uses -= 1
            order.promo_code_id = None

    order.total_amount = subtotal - discount
    order.discount_amount = discount

    for product, qty in validated:
        item = OrderItem(
            order_id=order.id,
            product_id=product.id,
            quantity=qty,
            price_at_order=product.price,
        )
        db.add(item)

    op = UserOperation(user_id=user.user_id, operation_type="UPDATE_ORDER")
    db.add(op)

    db.commit()
    db.refresh(order)
    return _to_response(order)


@router.post("/{order_id}/cancel", response_model=OrderResponse)
def cancel_order(
    order_id: int,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    if user.role == "SELLER":
        raise AccessDenied("SELLER cannot cancel orders")

    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise OrderNotFound(order_id)

    _check_order_access(order, user)

    if order.status not in ["CREATED", "PAYMENT_PENDING"]:
        raise InvalidStateTransition(order.status, "cancel")

    for item in order.items:
        product = db.query(Product).filter(Product.id == item.product_id).first()
        if product:
            product.stock += item.quantity

    if order.promo_code_id:
        promo = db.query(PromoCode).filter(PromoCode.id == order.promo_code_id).first()
        if promo:
            promo.current_uses -= 1

    order.status = "CANCELED"

    db.commit()
    db.refresh(order)
    return _to_response(order)
