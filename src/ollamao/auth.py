"""Authentication and authorization for ollamao."""

import uuid
from typing import Optional

from fastapi import HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .config import APIKeyConfig, get_config_manager
from .logging import auth_logger


class APIKeyError(Exception):
    """Base exception for API key related errors."""

    pass


class APIKeyNotFoundError(APIKeyError):
    """Raised when an API key is not found."""

    pass


class APIKeyDisabledError(APIKeyError):
    """Raised when an API key is disabled."""

    pass


class QuotaExceededError(APIKeyError):
    """Raised when quota is exceeded (for future use)."""

    pass


class APIKeyAuth:
    """API key authentication handler."""

    def __init__(self):
        self.config_manager = get_config_manager()
        self.security = HTTPBearer(auto_error=False)

    async def authenticate(
        self, credentials: Optional[HTTPAuthorizationCredentials]
    ) -> APIKeyConfig:
        """
        Authenticate a request using API key.

        Args:
            credentials: HTTP authorization credentials

        Returns:
            API key configuration if valid

        Raises:
            HTTPException: If authentication fails
        """
        if not credentials:
            auth_logger.log_auth_failure("No authorization header provided")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authorization header required",
                headers={"WWW-Authenticate": "Bearer"},
            )

        api_key = credentials.credentials
        api_key_hash = hash(api_key)

        try:
            # Get API key configuration
            key_config = self.config_manager.get_api_key_config(api_key)
            if not key_config:
                auth_logger.log_auth_failure("API key not found", api_key_hash)
                raise APIKeyNotFoundError(f"Invalid API key")

            # Check if key is enabled
            if not key_config.enabled:
                auth_logger.log_auth_failure("API key disabled", api_key_hash)
                raise APIKeyDisabledError(f"API key is disabled")

            # TODO: Implement quota checking here when quotas are enforced
            # if not self._check_quota(api_key, key_config):
            #     auth_logger.log_quota_exceeded(api_key_hash, key_config.name)
            #     raise QuotaExceededError(f"Quota exceeded for key: {key_config.name}")

            auth_logger.log_auth_success(api_key_hash, key_config.name)
            return key_config

        except APIKeyError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(e),
                headers={"WWW-Authenticate": "Bearer"},
            )
        except Exception as e:
            auth_logger.log_auth_failure(
                f"Authentication error: {str(e)}", api_key_hash
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Authentication service error",
            )

    def _check_quota(self, api_key: str, key_config: APIKeyConfig) -> bool:
        """
        Check if the API key has quota remaining.

        This is a placeholder for future quota implementation.

        Args:
            api_key: The API key
            key_config: API key configuration

        Returns:
            True if quota is available, False otherwise
        """
        # TODO: Implement actual quota checking
        # For now, "unlimited" quota means always allowed
        return key_config.quota == "unlimited"

    async def get_current_user(self, request: Request) -> APIKeyConfig:
        """
        Get the current authenticated user from the request.

        This is a dependency that can be used in FastAPI routes.

        Args:
            request: FastAPI request object

        Returns:
            API key configuration for the authenticated user
        """
        credentials = await self.security(request)
        return await self.authenticate(credentials)


class RequestIDMiddleware:
    """Middleware to add unique request IDs to each request."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            # Generate a unique request ID
            request_id = str(uuid.uuid4())
            scope["request_id"] = request_id

            # Add request ID to response headers
            async def send_with_request_id(message):
                if message["type"] == "http.response.start":
                    headers = list(message.get("headers", []))
                    headers.append((b"x-request-id", request_id.encode()))
                    message["headers"] = headers
                await send(message)

            await self.app(scope, receive, send_with_request_id)
        else:
            await self.app(scope, receive, send)


def get_request_id(request: Request) -> str:
    """Get the request ID from the request scope."""
    return getattr(request.scope, "request_id", "unknown")


# Global auth instance
api_key_auth = APIKeyAuth()
