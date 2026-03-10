from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import CurrentUser, get_current_user
from app.database import get_db
from app.exceptions import AccessDenied
from app.models import PromoCode

router = APIRouter(prefix="/promo-codes", tags=["PromoCodes"])


class PromoCodeCreate(BaseModel):
    code: str
    discount_type: str
    discount_value: float
    min_order_amount: float = 0
    max_uses: int
    valid_from: datetime
    valid_until: datetime


class PromoCodeResponse(BaseModel):
    id: int
    code: str
    discount_type: str
    discount_value: float
    min_order_amount: float
    max_uses: int
    current_uses: int
    valid_from: datetime
    valid_until: datetime
    active: bool


@router.post("", response_model=PromoCodeResponse, status_code=201)
def create_promo_code(
    body: PromoCodeCreate,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    if user.role not in ["SELLER", "ADMIN"]:
        raise AccessDenied("Only SELLER or ADMIN can create promo codes")

    promo = PromoCode(
        code=body.code,
        discount_type=body.discount_type,
        discount_value=body.discount_value,
        min_order_amount=body.min_order_amount,
        max_uses=body.max_uses,
        valid_from=body.valid_from,
        valid_until=body.valid_until,
    )
    db.add(promo)
    db.commit()
    db.refresh(promo)

    return PromoCodeResponse(
        id=promo.id,
        code=promo.code,
        discount_type=promo.discount_type,
        discount_value=float(promo.discount_value),
        min_order_amount=float(promo.min_order_amount),
        max_uses=promo.max_uses,
        current_uses=promo.current_uses,
        valid_from=promo.valid_from,
        valid_until=promo.valid_until,
        active=promo.active,
    )
