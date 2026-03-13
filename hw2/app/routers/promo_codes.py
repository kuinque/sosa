"""Promo codes API with role-based access control."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import TokenPayload, require_roles
from app.database import get_db
from app.exceptions import ApiException
from app.models import PromoCode

router = APIRouter(prefix="/promo-codes", tags=["PromoCodes"])


def _ensure_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


@router.post("", status_code=201)
def create_promo_code(
    body: dict,
    db: Session = Depends(get_db),
    user: TokenPayload = Depends(require_roles("SELLER", "ADMIN")),
):
    """Create promo code. SELLER and ADMIN can create, USER cannot."""
    code = body.get("code")
    discount_type = body.get("discount_type")
    discount_value = body.get("discount_value")
    min_order_amount = body.get("min_order_amount", 0)
    max_uses = body.get("max_uses")
    valid_from = body.get("valid_from")
    valid_until = body.get("valid_until")

    if not all([code, discount_type, discount_value, max_uses, valid_from, valid_until]):
        raise ApiException(400, "VALIDATION_ERROR", "Missing required fields")

    if discount_type not in ("PERCENTAGE", "FIXED_AMOUNT"):
        raise ApiException(400, "VALIDATION_ERROR", "discount_type must be PERCENTAGE or FIXED_AMOUNT")

    existing = db.query(PromoCode).filter(PromoCode.code == code.upper()).first()
    if existing:
        raise ApiException(400, "VALIDATION_ERROR", "Promo code already exists")

    if isinstance(valid_from, str):
        valid_from = datetime.fromisoformat(valid_from.replace("Z", "+00:00"))
    if isinstance(valid_until, str):
        valid_until = datetime.fromisoformat(valid_until.replace("Z", "+00:00"))

    promo = PromoCode(
        code=code.upper(),
        discount_type=discount_type,
        discount_value=discount_value,
        min_order_amount=min_order_amount,
        max_uses=max_uses,
        valid_from=valid_from,
        valid_until=valid_until,
        active=True,
    )
    db.add(promo)
    db.commit()
    db.refresh(promo)

    return {
        "id": promo.id,
        "code": promo.code,
        "discount_type": promo.discount_type,
        "discount_value": float(promo.discount_value),
        "min_order_amount": float(promo.min_order_amount),
        "max_uses": promo.max_uses,
        "current_uses": promo.current_uses,
        "valid_from": _ensure_utc(promo.valid_from).isoformat(),
        "valid_until": _ensure_utc(promo.valid_until).isoformat(),
        "active": promo.active,
    }
