"""Authentication endpoints: register, login, refresh."""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
)
from app.config import settings
from app.database import get_db
from app.exceptions import ApiException
from app.models import RefreshToken, User

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", status_code=201)
def register(body: dict, db: Session = Depends(get_db)):
    """Register a new user."""
    email = body.get("email")
    password = body.get("password")
    role = body.get("role", "USER")

    if not email or not password:
        raise ApiException(400, "VALIDATION_ERROR", "Email and password are required")

    if len(password) < 8:
        raise ApiException(400, "VALIDATION_ERROR", "Password must be at least 8 characters")

    if role not in ("USER", "SELLER", "ADMIN"):
        raise ApiException(400, "VALIDATION_ERROR", "Invalid role. Must be USER, SELLER, or ADMIN")

    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise ApiException(400, "VALIDATION_ERROR", "Email already registered")

    user = User(
        email=email,
        password_hash=hash_password(password),
        role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return {"id": user.id, "email": user.email, "role": user.role}


@router.post("/login")
def login(body: dict, db: Session = Depends(get_db)):
    """Authenticate user and return tokens."""
    email = body.get("email")
    password = body.get("password")

    if not email or not password:
        raise ApiException(400, "VALIDATION_ERROR", "Email and password are required")

    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.password_hash):
        raise ApiException(401, "TOKEN_INVALID", "Invalid email or password")

    access_token = create_access_token(user.id, user.role)
    refresh_token_value = create_refresh_token()

    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
    refresh_token = RefreshToken(
        user_id=user.id,
        token=refresh_token_value,
        expires_at=expires_at,
    )
    db.add(refresh_token)
    db.commit()

    return {
        "access_token": access_token,
        "refresh_token": refresh_token_value,
        "token_type": "bearer",
    }


@router.post("/refresh")
def refresh(body: dict, db: Session = Depends(get_db)):
    """Refresh access token using refresh token."""
    refresh_token_value = body.get("refresh_token")

    if not refresh_token_value:
        raise ApiException(400, "VALIDATION_ERROR", "refresh_token is required")

    token = db.query(RefreshToken).filter(RefreshToken.token == refresh_token_value).first()
    if not token:
        raise ApiException(401, "REFRESH_TOKEN_INVALID", "Invalid refresh token")

    now = datetime.now(timezone.utc)
    expires_at = token.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if now > expires_at:
        db.delete(token)
        db.commit()
        raise ApiException(401, "REFRESH_TOKEN_INVALID", "Refresh token has expired")

    user = db.query(User).filter(User.id == token.user_id).first()
    if not user:
        raise ApiException(401, "REFRESH_TOKEN_INVALID", "User not found")

    access_token = create_access_token(user.id, user.role)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token_value,
        "token_type": "bearer",
    }
