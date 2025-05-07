# src/customer_sentiment_hub/api/app.py

"""
Main application module for the Customer Sentiment Hub API.

Initializes the FastAPI app, configures middleware, exception handlers,
logging, and mounts API endpoints.
"""

import json
import logging
import time
import uuid 
from datetime import datetime
from typing import Any, Dict
from contextlib import asynccontextmanager # Use lifespan for modern FastAPI

from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware # Added CORS

from customer_sentiment_hub.config.settings import settings
from customer_sentiment_hub.api.models import ErrorResponse
from customer_sentiment_hub.api.routes import main_router
from customer_sentiment_hub.services.gemini_service import GeminiService
from customer_sentiment_hub.services.processor import ReviewProcessor
from customer_sentiment_hub.domain.validation import ValidationService
from customer_sentiment_hub.utils.logging import configure_logging, get_logger
# Assuming metrics collector exists as per previous analysis
# from customer_sentiment_hub.utils.metrics import MetricsCollector 

# Import Freshdesk Service
from customer_sentiment_hub.services.freshdesk_service import FreshdeskService

# Configure logging (using settings.logging_.level if defined like that)
log_level_to_use = settings.logging_.level if hasattr(settings, 'logging_') else settings.log_level
configure_logging(
    log_level=log_level_to_use,
    console_output=True,
    file_output=True, # Consider disabling file output if logging to CloudWatch
)
logger = get_logger(__name__)

# Initialize metrics collector if used
# metrics = MetricsCollector()

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
        correlation_id = getattr(request.state, 'correlation_id', 'N/A')
        errors = "; ".join(
            f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in exc.errors()
        )
        logger.warning(
            "Validation failed",
            extra={
                "correlation_id": correlation_id,
                "errors": errors,
                "path": request.url.path
            }
        )
        # Use detail structure expected by FastAPI default handler for better tooling integration
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": exc.errors()}, 
        )

    @app.exception_handler(HTTPException)
    async def _handle_http_exception(
        request: Request, exc: HTTPException
    ) -> JSONResponse:
        correlation_id = getattr(request.state, 'correlation_id', 'N/A')
        level = logging.ERROR if exc.status_code >= 500 else logging.WARNING
        logger.log(
            level,
            "HTTP error",
            extra={
                "correlation_id": correlation_id,
                "status_code": exc.status_code,
                "detail": exc.detail,
                "path": request.url.path
            }
        )
        # Use a consistent ErrorResponse model
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
        correlation_id = getattr(request.state, 'correlation_id', 'N/A')
        logger.exception(
            "Unhandled exception",
            extra={
                "correlation_id": correlation_id,
                "path": request.url.path,
                "method": request.method
            }
        )
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

# Use lifespan context manager for startup/shutdown logic
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan events (startup/shutdown)."""
    # Startup
    logger.info("Starting %s v%s", settings.app_name, settings.version)
    
    # Initialize services
    validation = ValidationService()
    gemini = GeminiService(
        gemini_settings=settings.gemini,
        google_settings=settings.google_cloud,
        validation_service=validation,
    )
    processor = ReviewProcessor(
        llm_service=gemini,
        settings=settings.processing,
    )
    
    # Initialize Freshdesk Service
    freshdesk = None
    try:
        # Ensure Freshdesk settings are loaded in your main settings object
        # Check for settings.freshdesk and settings.freshdesk.api_key
        if hasattr(settings, 'freshdesk') and settings.freshdesk and hasattr(settings.freshdesk, 'api_key') and settings.freshdesk.api_key:
            freshdesk = FreshdeskService(settings.freshdesk)
            logger.info("Freshdesk service initialized.")
        else:
            logger.warning("Freshdesk settings not found or API key missing in config. Freshdesk service not initialized.")
    except Exception as e:
        logger.error(f"Failed to initialize Freshdesk service: {e}", exc_info=True)
        

    # Add services to application state
    app.state.validation_service = validation
    app.state.gemini_service = gemini
    app.state.processor = processor
    app.state.freshdesk_service = freshdesk # Store even if None
    # app.state.metrics = metrics # If using metrics
    
    yield  # Application runs here
    
    # Shutdown logic (if any)
    logger.info("Shutting down %s", settings.app_name)
    # Add cleanup for services if needed (e.g., closing connections)

def create_app() -> FastAPI:
    """
    Construct and configure the FastAPI application.
    """
    app = FastAPI(
        title=settings.app_name,
        description=settings.description,
        version=settings.version,
        docs_url="/docs" if settings.environment != "production" else None,
        redoc_url="/redoc" if settings.environment != "production" else None,
        openapi_url="/openapi.json" if settings.environment != "production" else None,
        lifespan=lifespan, # Use the lifespan context manager
    )

    # Add CORS middleware (ensure settings.cors_origins is defined)
    if hasattr(settings, 'cors_origins') and settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    else:
        logger.warning("CORS origins not configured. Allowing all origins for development.")
        # Default permissive CORS for development if not specified
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"], 
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # Add correlation ID middleware
    @app.middleware("http")
    async def add_correlation_id(request: Request, call_next):
        correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
        request.state.correlation_id = correlation_id
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        return response

    # Register exception handlers
    _register_exception_handlers(app)

    # Include API routers
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
    Console‐script entrypoint.
    Launches Uvicorn on our `app` instance.
    """
    import uvicorn

    # Resolve defaults from settings
    actual_host = host or settings.host
    actual_port = port or settings.port
    # Ensure reload is False if not in debug mode
    actual_reload = reload and settings.debug 
    # Use the same log level determination as above
    actual_log = (log_level or log_level_to_use).lower()

    logger.info(
        "Starting HTTP API on %s:%d (reload=%s, workers=%d) → log_level=%s",
        actual_host, actual_port, actual_reload, workers, actual_log
    )
    uvicorn.run(
        "customer_sentiment_hub.api.app:app",
        host=actual_host,
        port=actual_port,
        reload=actual_reload,
        log_level=actual_log,
        workers=workers,
    )

