"""Main FastAPI application for ollamao."""

import asyncio
from contextlib import asynccontextmanager
from typing import Any, Dict

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from . import __version__
from .auth import RequestIDMiddleware
from .config import get_settings
from .logging import get_logger, setup_logging
from .ollama_client import ollama_client
from .router import router

# Setup logging before creating the app
setup_logging()
logger = get_logger("ollamao.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan events."""
    # Startup
    logger.info("Starting ollamao", version=__version__)

    settings = get_settings()
    logger.info(
        "Application configuration",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level,
        debug=settings.debug,
    )

    try:
        yield
    finally:
        # Shutdown
        logger.info("Shutting down ollamao")
        await ollama_client.close()
        logger.info("Shutdown complete")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    # Create FastAPI app
    app = FastAPI(
        title="ollamao",
        description="A production-grade, OpenAI-compatible LLM serving stack powered by Ollama",
        version=__version__,
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        lifespan=lifespan,
    )

    # Add middleware
    app.add_middleware(RequestIDMiddleware)

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(router)

    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        """Handle uncaught exceptions."""
        logger.error(
            "Unhandled exception",
            exc_info=exc,
            path=request.url.path,
            method=request.method,
        )

        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "message": "Internal server error",
                    "type": "internal_error",
                    "code": "unhandled_exception",
                }
            },
        )

    return app


# Create the app instance
app = create_app()


def main() -> None:
    """Main entry point for running the application."""
    import uvicorn

    settings = get_settings()

    uvicorn.run(
        "ollamao.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_config=None,  # We handle logging ourselves
        access_log=False,  # We handle access logging ourselves
    )


if __name__ == "__main__":
    main()
