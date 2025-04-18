# src/customer_sentiment_hub/api/app.py

"""
Main application module for the Customer Sentiment Hub API.

Initializes the FastAPI app, configures middleware, exception handlers,
logging, and mounts only the live endpoints (/health and /analyze).
"""

import json
import logging
import time
from datetime import datetime
from typing import Any, Dict

from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError


from customer_sentiment_hub.config.settings import settings
from customer_sentiment_hub.api.models import ErrorResponse

from customer_sentiment_hub.api.routes import main_router
from customer_sentiment_hub.services.gemini_service import GeminiService
from customer_sentiment_hub.services.processor import ReviewProcessor
from customer_sentiment_hub.domain.validation import ValidationService
from customer_sentiment_hub.utils.logging import configure_logging, get_logger


configure_logging(
    log_level=settings.log_level,
    console_output=True,
    file_output=True,
)
logger = get_logger(__name__)


class _CustomJSONEncoder(json.JSONEncoder):
    """Extend JSON encoding to support datetime objects."""
    def default(self, obj: Any) -> Any:
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


def _safe_serialize(obj: Any) -> Dict[str, Any]:
    """Serialize arbitrary object to JSON-compatible dict using custom encoder."""
    return json.loads(json.dumps(obj, cls=_CustomJSONEncoder))


def _register_exception_handlers(app: FastAPI) -> None:
    """
    Attach global exception handlers for validation errors, HTTP exceptions,
    and uncaught exceptions to produce consistent JSON error responses.
    """

    @app.exception_handler(RequestValidationError)
    async def _handle_request_validation(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        start = time.time()
        errors = "; ".join(
            f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in exc.errors()
        )
        logger.warning("Validation failed: %s", errors)
        payload = ErrorResponse(
            detail=f"Validation error: {errors}",
            code="VALIDATION_ERROR",
            path=request.url.path,
            timestamp=datetime.utcnow(),
        ).model_dump()
        logger.debug("Validation error handled in %.4fs", time.time() - start)
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=_safe_serialize(payload),
        )

    @app.exception_handler(HTTPException)
    async def _handle_http_exception(
        request: Request, exc: HTTPException
    ) -> JSONResponse:
        level = logging.ERROR if exc.status_code >= 500 else logging.WARNING
        logger.log(level, "HTTP %d: %s", exc.status_code, exc.detail)
        payload = ErrorResponse(
            detail=exc.detail,
            code=f"HTTP_{exc.status_code}",
            path=request.url.path,
            timestamp=datetime.utcnow(),
        ).model_dump()
        return JSONResponse(
            status_code=exc.status_code,
            content=_safe_serialize(payload),
            headers=exc.headers,
        )

    @app.exception_handler(Exception)
    async def _handle_unexpected_exception(
        request: Request, exc: Exception
    ) -> JSONResponse:
        logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
        payload = ErrorResponse(
            detail="Internal server error",
            code="INTERNAL_SERVER_ERROR",
            path=request.url.path,
            timestamp=datetime.utcnow(),
        ).model_dump()
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_safe_serialize(payload),
        )


def create_app() -> FastAPI:
    """
    Construct and configure the FastAPI application:
    - CORS middleware
    - Exception handlers
    - Startup service‐initialization
    - Mounting live routes
    """
    app = FastAPI(
        title=settings.app_name,
        description=settings.description,
        version=settings.version,
        docs_url="/docs" if settings.environment != "production" else None,
        redoc_url="/redoc" if settings.environment != "production" else None,
        openapi_url="/openapi.json" if settings.environment != "production" else None,
    )


    # Exception handlers
    _register_exception_handlers(app)

    # Initialize shared services on startup
    @app.on_event("startup")
    async def _startup() -> None:
        logger.info("Starting %s v%s", settings.app_name, settings.version)
        validation = ValidationService()
        gemini     = GeminiService(
            gemini_settings=settings.gemini,
            google_settings=settings.google_cloud,
            validation_service=validation,
        )
        processor  = ReviewProcessor(
            llm_service=gemini,
            settings=settings.processing,
        )

        app.state.validation_service = validation
        app.state.gemini_service     = gemini
        app.state.processor          = processor

    app.include_router(main_router)

    return app


app = create_app()
def start(
    host: str | None = None,
    port: int | None = None,
    reload: bool = False,
    workers: int = 1,
    log_level: str | None = None
) -> None:
    """
    Console‐script entrypoint for `poetry run sentiment-api` or `python -m customer_sentiment_hub server`.
    Launches Uvicorn on our `app` instance.
    """
    import uvicorn

    # Resolve defaults from settings
    actual_host   = host or settings.host
    actual_port   = port or settings.port
    actual_reload = reload if settings.debug else False
    actual_log    = (log_level or settings.log_level).lower()

    logger.info(
        "Starting HTTP API on %s:%d (reload=%s) → log_level=%s",
        actual_host, actual_port, actual_reload, actual_log
    )
    uvicorn.run(
        "customer_sentiment_hub.api.app:app",
        host=actual_host,
        port=actual_port,
        reload=actual_reload,
        log_level=actual_log,
        workers=workers,
    )