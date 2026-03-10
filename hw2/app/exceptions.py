from typing import Any, Optional

from fastapi import HTTPException


class AppException(HTTPException):
    def __init__(
        self,
        status_code: int,
        error_code: str,
        message: str,
        details: Optional[dict[str, Any]] = None,
    ):
        self.error_code = error_code
        self.error_message = message
        self.details = details
        super().__init__(status_code=status_code, detail=message)


class ProductNotFound(AppException):
    def __init__(self, product_id: int):
        super().__init__(
            status_code=404,
            error_code="PRODUCT_NOT_FOUND",
            message=f"Product with id {product_id} not found",
            details={"product_id": product_id},
        )


class ProductInactive(AppException):
    def __init__(self, product_id: int):
        super().__init__(
            status_code=409,
            error_code="PRODUCT_INACTIVE",
            message=f"Product with id {product_id} is not active",
            details={"product_id": product_id},
        )


class OrderNotFound(AppException):
    def __init__(self, order_id: int):
        super().__init__(
            status_code=404,
            error_code="ORDER_NOT_FOUND",
            message=f"Order with id {order_id} not found",
            details={"order_id": order_id},
        )


class OrderLimitExceeded(AppException):
    def __init__(self, operation: str):
        super().__init__(
            status_code=429,
            error_code="ORDER_LIMIT_EXCEEDED",
            message=f"Rate limit exceeded for {operation}",
            details={"operation": operation},
        )


class OrderHasActive(AppException):
    def __init__(self, user_id: int):
        super().__init__(
            status_code=409,
            error_code="ORDER_HAS_ACTIVE",
            message="User already has an active order",
            details={"user_id": user_id},
        )


class InvalidStateTransition(AppException):
    def __init__(self, current_status: str, action: str):
        super().__init__(
            status_code=409,
            error_code="INVALID_STATE_TRANSITION",
            message=f"Cannot {action} order in status {current_status}",
            details={"current_status": current_status, "action": action},
        )


class InsufficientStock(AppException):
    def __init__(self, items: list[dict]):
        super().__init__(
            status_code=409,
            error_code="INSUFFICIENT_STOCK",
            message="Insufficient stock for some products",
            details={"items": items},
        )


class PromoCodeInvalid(AppException):
    def __init__(self, code: str, reason: str):
        super().__init__(
            status_code=422,
            error_code="PROMO_CODE_INVALID",
            message=f"Promo code '{code}' is invalid: {reason}",
            details={"code": code, "reason": reason},
        )


class PromoCodeMinAmount(AppException):
    def __init__(self, code: str, min_amount: float, order_amount: float):
        super().__init__(
            status_code=422,
            error_code="PROMO_CODE_MIN_AMOUNT",
            message=f"Order amount {order_amount} is below minimum {min_amount} for promo code",
            details={
                "code": code,
                "min_order_amount": min_amount,
                "order_amount": order_amount,
            },
        )


class OrderOwnershipViolation(AppException):
    def __init__(self, order_id: int):
        super().__init__(
            status_code=403,
            error_code="ORDER_OWNERSHIP_VIOLATION",
            message="Order belongs to another user",
            details={"order_id": order_id},
        )


class ValidationError(AppException):
    def __init__(self, errors: list[dict]):
        super().__init__(
            status_code=400,
            error_code="VALIDATION_ERROR",
            message="Validation error",
            details={"errors": errors},
        )


class AccessDenied(AppException):
    def __init__(self, reason: str = "Insufficient permissions"):
        super().__init__(
            status_code=403,
            error_code="ACCESS_DENIED",
            message=reason,
        )


class TokenExpired(AppException):
    def __init__(self):
        super().__init__(
            status_code=401,
            error_code="TOKEN_EXPIRED",
            message="Token has expired",
        )


class TokenInvalid(AppException):
    def __init__(self):
        super().__init__(
            status_code=401,
            error_code="TOKEN_INVALID",
            message="Invalid token",
        )


class RefreshTokenInvalid(AppException):
    def __init__(self):
        super().__init__(
            status_code=401,
            error_code="REFRESH_TOKEN_INVALID",
            message="Invalid or expired refresh token",
        )
