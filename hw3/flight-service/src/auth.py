import logging
import grpc
from typing import Callable

from .config import config

logger = logging.getLogger(__name__)

API_KEY_METADATA = "x-api-key"


class AuthInterceptor(grpc.ServerInterceptor):
    def __init__(self, api_key: str):
        self._api_key = api_key
    
    def intercept_service(self, continuation, handler_call_details):
        metadata = dict(handler_call_details.invocation_metadata)
        api_key = metadata.get(API_KEY_METADATA)
        
        if not api_key:
            logger.warning(f"Missing API key for method: {handler_call_details.method}")
            return _unauthenticated_handler()
        
        if api_key != self._api_key:
            logger.warning(f"Invalid API key for method: {handler_call_details.method}")
            return _unauthenticated_handler()
        
        logger.debug(f"Authenticated request for method: {handler_call_details.method}")
        return continuation(handler_call_details)


def _unauthenticated_handler():
    def handler(request, context):
        context.abort(grpc.StatusCode.UNAUTHENTICATED, "Invalid or missing API key")
    
    return grpc.unary_unary_rpc_method_handler(handler)


def create_auth_interceptor() -> AuthInterceptor:
    return AuthInterceptor(config.GRPC_API_KEY)
