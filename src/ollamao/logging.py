"""Structured logging configuration for ollamao."""

import logging
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import structlog
from rich.console import Console
from rich.logging import RichHandler

from .config import get_settings


def setup_logging() -> None:
    """Configure structured logging for the application."""
    settings = get_settings()

    # Configure structlog
    structlog.configure(
        processors=[
            # Add filename, line number, and function name to log entries
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            # Choose renderer based on format setting
            (
                structlog.processors.JSONRenderer()
                if settings.log_format == "json"
                else structlog.dev.ConsoleRenderer(colors=True)
            ),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Configure standard library logging
    if settings.log_format == "console":
        logging.basicConfig(
            format="%(message)s",
            level=getattr(logging, settings.log_level.upper()),
            handlers=[
                RichHandler(console=Console(file=sys.stdout), rich_tracebacks=True)
            ],
        )
    else:
        logging.basicConfig(
            format="%(message)s",
            level=getattr(logging, settings.log_level.upper()),
            handlers=[logging.StreamHandler(sys.stdout)],
        )

    # Set uvicorn log levels
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)


def get_logger(name: str) -> structlog.BoundLogger:
    """Get a structured logger instance."""
    return structlog.get_logger(name)


class RequestLogger:
    """Logger for tracking HTTP requests with metrics."""

    def __init__(self):
        self.logger = get_logger("ollamao.requests")

    def log_request_start(
        self,
        request_id: str,
        method: str,
        path: str,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Log the start of a request and return context for completion logging."""
        context = {
            "request_id": request_id,
            "method": method,
            "path": path,
            "model": model,
            "api_key_hash": hash(api_key) if api_key else None,
            "start_time": time.time(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        self.logger.info("Request started", **context)

        return context

    def log_request_complete(
        self,
        context: Dict[str, Any],
        status_code: int,
        tokens_prompt: Optional[int] = None,
        tokens_response: Optional[int] = None,
        error: Optional[str] = None,
    ) -> None:
        """Log the completion of a request with metrics."""
        end_time = time.time()
        latency_ms = int((end_time - context["start_time"]) * 1000)

        log_data = {
            **context,
            "status_code": status_code,
            "latency_ms": latency_ms,
            "tokens_prompt": tokens_prompt,
            "tokens_response": tokens_response,
            "error": error,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }

        if error:
            self.logger.error("Request failed", **log_data)
        else:
            self.logger.info("Request completed", **log_data)


class ModelLogger:
    """Logger for tracking model-specific operations."""

    def __init__(self):
        self.logger = get_logger("ollamao.models")

    def log_ollama_request(
        self,
        model: str,
        ollama_url: str,
        method: str = "POST",
    ) -> None:
        """Log an outgoing request to Ollama."""
        self.logger.debug(
            "Ollama request",
            model=model,
            ollama_url=ollama_url,
            method=method,
        )

    def log_ollama_response(
        self,
        model: str,
        status_code: int,
        latency_ms: int,
        tokens: Optional[int] = None,
        error: Optional[str] = None,
    ) -> None:
        """Log the response from Ollama."""
        if error:
            self.logger.error(
                "Ollama request failed",
                model=model,
                status_code=status_code,
                latency_ms=latency_ms,
                error=error,
            )
        else:
            self.logger.debug(
                "Ollama response",
                model=model,
                status_code=status_code,
                latency_ms=latency_ms,
                tokens=tokens,
            )

    def log_model_not_found(self, model: str, available_models: list[str]) -> None:
        """Log when a requested model is not found."""
        self.logger.warning(
            "Model not found",
            requested_model=model,
            available_models=available_models,
        )


class AuthLogger:
    """Logger for authentication and authorization events."""

    def __init__(self):
        self.logger = get_logger("ollamao.auth")

    def log_auth_success(self, api_key_hash: int, key_name: str) -> None:
        """Log successful authentication."""
        self.logger.debug(
            "Authentication successful",
            api_key_hash=api_key_hash,
            key_name=key_name,
        )

    def log_auth_failure(self, reason: str, api_key_hash: Optional[int] = None) -> None:
        """Log authentication failure."""
        self.logger.warning(
            "Authentication failed",
            reason=reason,
            api_key_hash=api_key_hash,
        )

    def log_quota_exceeded(self, api_key_hash: int, key_name: str) -> None:
        """Log quota exceeded event (for future use)."""
        self.logger.warning(
            "Quota exceeded",
            api_key_hash=api_key_hash,
            key_name=key_name,
        )


# Global logger instances
request_logger = RequestLogger()
model_logger = ModelLogger()
auth_logger = AuthLogger()
