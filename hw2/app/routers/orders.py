"""Orders API with role-based access control."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy import and_, desc
from sqlalchemy.orm import Session

from app.auth import TokenPayload, get_current_user, require_roles
from app.config import settings
from app.database import get_db
from app.exceptions import ApiException
from app.generated.models import (
    OrderCreate,
    OrderResponse,
    OrderUpdate,
)
from app.models import Order, OrderItem, Product, PromoCode, UserOperation

router = APIRouter(prefix="/orders", tags=["Orders"])

CANCELABLE_STATUSES = {"CREATED", "PAYMENT_PENDING"}
UPDATABLE_STATUS = "CREATED"
CREATE_ORDER_TYPE = "CREATE_ORDER"
UPDATE_ORDER_TYPE = "UPDATE_ORDER"


def _ensure_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _order_to_response(order: Order) -> OrderResponse:
    items = [
        {
            "id": oi.id,
            "product_id": oi.product_id,
            "quantity": oi.quantity,
            "price_at_order": float(oi.price_at_order),
        }
        for oi in order.items
    ]
    return OrderResponse(
        id=order.id,
        user_id=order.user_id,
        status=order.status,
        promo_code_id=order.promo_code_id,
        total_amount=float(order.total_amount),
        discount_amount=float(order.discount_amount),
        items=items,
        created_at=_ensure_utc(order.created_at),
        updated_at=_ensure_utc(order.updated_at),
    )


def _check_rate_limit(db: Session, user_id: int, operation_type: str) -> None:
    """Raise ORDER_LIMIT_EXCEEDED if last operation was within N minutes."""
    last = (
        db.query(UserOperation)
        .filter(
            and_(
                UserOperation.user_id == user_id,
                UserOperation.operation_type == operation_type,
            )
        )
        .order_by(desc(UserOperation.created_at))
        .first()
    )
    if not last:
        return
    now = datetime.now(timezone.utc)
    last_ts = last.created_at
    if last_ts.tzinfo is None:
        last_ts = last_ts.replace(tzinfo=timezone.utc)
    elapsed = now - last_ts
    if elapsed < timedelta(minutes=settings.order_limit_minutes):
        raise ApiException(
            429,
            "ORDER_LIMIT_EXCEEDED",
            f"Rate limit: wait at least {settings.order_limit_minutes} minutes between {operation_type} operations",
        )


def _check_active_order(db: Session, user_id: int) -> None:
    """Raise ORDER_HAS_ACTIVE if user has order in CREATED or PAYMENT_PENDING."""
    active = (
        db.query(Order)
        .filter(
            Order.user_id == user_id,
            Order.status.in_(["CREATED", "PAYMENT_PENDING"]),
        )
        .first()
    )
    if active:
        raise ApiException(409, "ORDER_HAS_ACTIVE", "User already has an active order (CREATED or PAYMENT_PENDING)")


def _resolve_promo(
    db: Session,
    code: str,
    total_before_discount: Decimal,
) -> tuple[PromoCode | None, Decimal]:
    """Validate promo and return (promo, discount_amount)."""
    promo = db.query(PromoCode).filter(PromoCode.code == code.upper()).first()
    if not promo:
        raise ApiException(422, "PROMO_CODE_INVALID", "Promo code not found or invalid")
    if not promo.active:
        raise ApiException(422, "PROMO_CODE_INVALID", "Promo code is not active")
    if promo.current_uses >= promo.max_uses:
        raise ApiException(422, "PROMO_CODE_INVALID", "Promo code usage limit exceeded")
    now = datetime.now(timezone.utc)
    valid_from = promo.valid_from.replace(tzinfo=timezone.utc) if promo.valid_from.tzinfo is None else promo.valid_from
    valid_until = promo.valid_until.replace(tzinfo=timezone.utc) if promo.valid_until.tzinfo is None else promo.valid_until
    if now < valid_from or now > valid_until:
        raise ApiException(422, "PROMO_CODE_INVALID", "Promo code is not valid in current period")
    if total_before_discount < promo.min_order_amount:
        raise ApiException(
            422,
            "PROMO_CODE_MIN_AMOUNT",
            "Order total is below minimum required amount for this promo code",
            details={"min_order_amount": float(promo.min_order_amount), "order_total": float(total_before_discount)},
        )
    if promo.discount_type == "PERCENTAGE":
        discount = total_before_discount * (promo.discount_value / 100)
        if discount > total_before_discount * Decimal("0.7"):
            discount = total_before_discount * Decimal("0.7")
    else:
        discount = min(promo.discount_value, total_before_discount)
    return promo, discount


def _check_order_access(order: Order, user: TokenPayload) -> None:
    """Check if user can access this order."""
    if user.role == "ADMIN":
        return
    if order.user_id != user.user_id:
        raise ApiException(403, "ORDER_OWNERSHIP_VIOLATION", "Order belongs to another user")


@router.post("", response_model=OrderResponse, status_code=201)
def create_order(
    body: OrderCreate,
    db: Session = Depends(get_db),
    user: TokenPayload = Depends(require_roles("USER", "ADMIN")),
):
    """Create order. USER and ADMIN can create, SELLER cannot."""
    user_id = user.user_id

    _check_rate_limit(db, user_id, CREATE_ORDER_TYPE)
    _check_active_order(db, user_id)

    product_ids = [it.product_id for it in body.items]
    products = {p.id: p for p in db.query(Product).filter(Product.id.in_(product_ids)).all()}
    insufficient = []
    for it in body.items:
        p = products.get(it.product_id)
        if not p:
            raise ApiException(404, "PRODUCT_NOT_FOUND", f"Product not found: {it.product_id}")
        if p.status != "ACTIVE":
            raise ApiException(409, "PRODUCT_INACTIVE", f"Product {it.product_id} is not active for ordering")
        if p.stock < it.quantity:
            insufficient.append(
                {"product_id": it.product_id, "requested": it.quantity, "available": p.stock}
            )
    if insufficient:
        raise ApiException(409, "INSUFFICIENT_STOCK", "Insufficient stock for one or more items", details={"items": insufficient})

    total_before_discount = Decimal("0")
    for it in body.items:
        p = products[it.product_id]
        total_before_discount += p.price * it.quantity

    discount_amount = Decimal("0")
    promo_to_apply = None
    if body.promo_code:
        promo_to_apply, discount_amount = _resolve_promo(db, body.promo_code, total_before_discount)

    total_amount = total_before_discount - discount_amount

    try:
        for it in body.items:
            p = products[it.product_id]
            p.stock -= it.quantity

        order = Order(
            user_id=user_id,
            status="CREATED",
            promo_code_id=promo_to_apply.id if promo_to_apply else None,
            total_amount=total_amount,
            discount_amount=discount_amount,
        )
        db.add(order)
        db.flush()

        for it in body.items:
            p = products[it.product_id]
            oi = OrderItem(
                order_id=order.id,
                product_id=it.product_id,
                quantity=it.quantity,
                price_at_order=p.price,
            )
            db.add(oi)

        if promo_to_apply:
            promo_to_apply.current_uses += 1

        op = UserOperation(user_id=user_id, operation_type=CREATE_ORDER_TYPE)
        db.add(op)
        db.commit()
        db.refresh(order)
    except Exception:
        db.rollback()
        raise

    return _order_to_response(order)


@router.get("/{order_id}", response_model=OrderResponse)
def get_order(
    order_id: int,
    db: Session = Depends(get_db),
    user: TokenPayload = Depends(require_roles("USER", "ADMIN")),
):
    """Get order by ID. USER only own, ADMIN any, SELLER forbidden."""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise ApiException(404, "ORDER_NOT_FOUND", f"Order not found: {order_id}")
    _check_order_access(order, user)
    return _order_to_response(order)


@router.put("/{order_id}", response_model=OrderResponse)
def update_order(
    order_id: int,
    body: OrderUpdate,
    db: Session = Depends(get_db),
    user: TokenPayload = Depends(require_roles("USER", "ADMIN")),
):
    """Update order. USER only own, ADMIN any, SELLER forbidden."""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise ApiException(404, "ORDER_NOT_FOUND", f"Order not found: {order_id}")
    _check_order_access(order, user)

    if order.status != UPDATABLE_STATUS:
        raise ApiException(409, "INVALID_STATE_TRANSITION", f"Order can be updated only in status CREATED, current: {order.status}")

    _check_rate_limit(db, user.user_id, UPDATE_ORDER_TYPE)

    old_items = list(order.items)
    products_old = {p.id: p for p in db.query(Product).filter(Product.id.in_([oi.product_id for oi in old_items])).all()}
    for oi in old_items:
        products_old[oi.product_id].stock += oi.quantity

    product_ids = [it.product_id for it in body.items]
    products = {p.id: p for p in db.query(Product).filter(Product.id.in_(product_ids)).all()}
    insufficient = []
    for it in body.items:
        p = products.get(it.product_id)
        if not p:
            raise ApiException(404, "PRODUCT_NOT_FOUND", f"Product not found: {it.product_id}")
        if p.status != "ACTIVE":
            raise ApiException(409, "PRODUCT_INACTIVE", f"Product {it.product_id} is not active")
        if p.stock < it.quantity:
            insufficient.append({"product_id": it.product_id, "requested": it.quantity, "available": p.stock})
    if insufficient:
        raise ApiException(409, "INSUFFICIENT_STOCK", "Insufficient stock", details={"items": insufficient})

    total_before_discount = Decimal(sum(products[it.product_id].price * it.quantity for it in body.items))
    discount_amount = Decimal("0")
    promo_entity = None

    if order.promo_code_id:
        promo_entity = db.query(PromoCode).filter(PromoCode.id == order.promo_code_id).first()
        if promo_entity:
            promo_entity.current_uses -= 1
        order.promo_code_id = None

    if promo_entity and total_before_discount >= promo_entity.min_order_amount:
        if promo_entity.discount_type == "PERCENTAGE":
            discount_amount = total_before_discount * (promo_entity.discount_value / 100)
            if discount_amount > total_before_discount * Decimal("0.7"):
                discount_amount = total_before_discount * Decimal("0.7")
        else:
            discount_amount = min(promo_entity.discount_value, total_before_discount)
        order.promo_code_id = promo_entity.id
        promo_entity.current_uses += 1

    total_amount = total_before_discount - discount_amount

    try:
        for oi in old_items:
            db.delete(oi)

        for it in body.items:
            p = products[it.product_id]
            p.stock -= it.quantity
            oi = OrderItem(order_id=order.id, product_id=it.product_id, quantity=it.quantity, price_at_order=p.price)
            db.add(oi)

        order.total_amount = total_amount
        order.discount_amount = discount_amount

        op = UserOperation(user_id=user.user_id, operation_type=UPDATE_ORDER_TYPE)
        db.add(op)
        db.commit()
        db.refresh(order)
    except Exception:
        db.rollback()
        raise

    return _order_to_response(order)


@router.post("/{order_id}/cancel", response_model=OrderResponse)
def cancel_order(
    order_id: int,
    db: Session = Depends(get_db),
    user: TokenPayload = Depends(require_roles("USER", "ADMIN")),
):
    """Cancel order. USER only own, ADMIN any, SELLER forbidden."""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise ApiException(404, "ORDER_NOT_FOUND", f"Order not found: {order_id}")
    _check_order_access(order, user)

    if order.status not in CANCELABLE_STATUSES:
        raise ApiException(409, "INVALID_STATE_TRANSITION", f"Order can be canceled only in CREATED or PAYMENT_PENDING, current: {order.status}")

    try:
        for oi in order.items:
            product = db.query(Product).filter(Product.id == oi.product_id).with_for_update().first()
            if product:
                product.stock += oi.quantity

        if order.promo_code_id:
            promo = db.query(PromoCode).filter(PromoCode.id == order.promo_code_id).first()
            if promo:
                promo.current_uses -= 1

        order.status = "CANCELED"
        db.commit()
        db.refresh(order)
    except Exception:
        db.rollback()
        raise

    return _order_to_response(order)
