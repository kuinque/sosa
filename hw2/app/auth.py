"""JWT authentication utilities."""
from datetime import datetime, timedelta, timezone
from typing import NamedTuple
import secrets

import bcrypt
import jwt
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings
from app.exceptions import ApiException


class TokenPayload(NamedTuple):
    user_id: int
    role: str


security = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    """Hash password using bcrypt."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    """Verify password against hash."""
    return bcrypt.checkpw(password.encode(), hashed.encode())


def create_access_token(user_id: int, role: str) -> str:
    """Create JWT access token."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": str(user_id),
        "role": role,
        "exp": expire,
        "type": "access",
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def create_refresh_token() -> str:
    """Create random refresh token."""
    return secrets.token_urlsafe(64)


def decode_access_token(token: str) -> TokenPayload:
    """Decode and validate access token."""
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        if payload.get("type") != "access":
            raise ApiException(401, "TOKEN_INVALID", "Invalid token type")
        return TokenPayload(
            user_id=int(payload["sub"]),
            role=payload["role"],
        )
    except jwt.ExpiredSignatureError:
        raise ApiException(401, "TOKEN_EXPIRED", "Access token has expired")
    except jwt.InvalidTokenError:
        raise ApiException(401, "TOKEN_INVALID", "Invalid access token")


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> TokenPayload:
    """Dependency to get current authenticated user from JWT."""
    if not credentials:
        raise ApiException(401, "TOKEN_INVALID", "Authorization header missing")
    
    payload = decode_access_token(credentials.credentials)
    request.state.user_id = payload.user_id
    return payload


def require_roles(*allowed_roles: str):
    """Dependency factory to require specific roles."""
    def checker(user: TokenPayload = Depends(get_current_user)) -> TokenPayload:
        if user.role not in allowed_roles:
            raise ApiException(403, "ACCESS_DENIED", f"Access denied. Required roles: {', '.join(allowed_roles)}")
        return user
    return checker
