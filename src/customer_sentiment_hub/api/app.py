"""
Main application module for the Customer Sentiment Hub API.

This module initializes the FastAPI application, configures middleware,
and sets up routes, exception handlers, and documentation. It provides
centralized error handling with consistent response formatting and
proper JSON serialization of all data types.
"""

import logging
import time
from typing import Any, Dict, Optional, Union
import json
from datetime import datetime

from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError, ResponseValidationError
from fastapi.middleware.cors import CORSMiddleware

from customer_sentiment_hub.config.settings import settings
from customer_sentiment_hub.api.middleware import setup_middlewares
from customer_sentiment_hub.api.routes import setup_routes
from customer_sentiment_hub.api.models import ErrorResponse

# Configure root logger
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("customer_sentiment_hub")


class CustomJSONEncoder(json.JSONEncoder):
    """
    Enhanced JSON encoder that properly handles non-serializable types.
    
    This encoder converts datetime objects to ISO format strings and can be
    extended to handle other custom types as needed.
    """
    def default(self, obj: Any) -> Any:
        if isinstance(obj, datetime):
            return obj.isoformat()
        # Add handling for other non-serializable types here
        return super().default(obj)


def safe_serialize(obj: Any) -> Dict:
    """
    Safely serialize any object to a JSON-compatible dictionary.
    
    Args:
        obj: Any object to serialize, including those with datetime fields
        
    Returns:
        Dict: JSON-compatible dictionary representation
    """
    return json.loads(json.dumps(obj, cls=CustomJSONEncoder))


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    This function centralizes all application setup logic, ensuring consistent
    configuration across different deployment environments.
    
    Returns:
        FastAPI: Configured FastAPI application instance
    """
    # Create the FastAPI app with appropriate settings
    app = FastAPI(
        title=settings.app_name,
        description=settings.description,
        version=settings.version,
        docs_url="/docs" if settings.environment != "production" else None,
        redoc_url="/redoc" if settings.environment != "production" else None,
        openapi_url="/openapi.json" if settings.environment != "production" else None,
    )
    
    # Setup global exception handlers
    setup_exception_handlers(app)
    
    # Setup API middlewares
    setup_middlewares(app)
    
    # Setup API routes
    setup_routes(app)
    
    # Add application startup and shutdown event handlers
    @app.on_event("startup")
    async def startup_event():
        """Initialize resources when the application starts."""
        logger.info(f"Starting {settings.app_name} v{settings.version} in {settings.environment} mode")
    
    @app.on_event("shutdown")
    async def shutdown_event():
        """Clean up resources when the application shuts down."""
        logger.info(f"Shutting down {settings.app_name}")
    
    return app


def setup_exception_handlers(app: FastAPI) -> None:
    """
    Configure global exception handlers for the application.
    
    This ensures consistent error responses across the API with proper
    status codes, error details, and serialization of all data types.
    
    Args:
        app: FastAPI application to configure
    """
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        """
        Handle validation errors from request parsing.
        
        This provides detailed information about validation failures to help
        API consumers correct their requests.
        
        Args:
            request: The incoming request that failed validation
            exc: The validation exception with details about what failed
            
        Returns:
            JSONResponse: Structured error response with validation details
        """
        # Start timing for performance monitoring
        start_time = time.time()
        
        # Log the validation error with request details
        logger.warning(
            f"Validation error: {str(exc)} | "
            f"Method: {request.method} | "
            f"URL: {request.url} | "
            f"Client: {request.client.host if request.client else 'unknown'}"
        )
        
        # Extract detailed error information
        errors = []
        for error in exc.errors():
            error_location = " -> ".join([str(loc) for loc in error["loc"]])
            errors.append(f"{error_location}: {error['msg']}")
        
        error_detail = "Validation error: " + "; ".join(errors)
        
        # Create a standardized error response
        error_response = ErrorResponse(
            detail=error_detail,
            code="VALIDATION_ERROR",
            path=request.url.path
        )
        
        # Safely serialize the response with datetime handling
        serialized_content = safe_serialize(error_response.model_dump())
        
        # Log performance data
        processing_time = time.time() - start_time
        logger.debug(f"Validation error processed in {processing_time:.4f}s")
        
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, 
            content=serialized_content
        )
    
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        """
        Handle HTTP exceptions raised by route handlers.
        
        Provides consistent error formatting for explicit HTTP exceptions.
        
        Args:
            request: The incoming request that triggered the exception
            exc: The HTTP exception with status code and detail
            
        Returns:
            JSONResponse: Structured error response
        """
        # Determine appropriate log level based on status code
        log_level = logging.ERROR if exc.status_code >= 500 else logging.WARNING
        
        # Log the HTTP exception
        logger.log(
            log_level, 
            f"HTTP {exc.status_code} exception: {exc.detail} | "
            f"URL: {request.url} | "
            f"Method: {request.method}"
        )
        
        # Create a standardized error response
        error_response = ErrorResponse(
            detail=exc.detail,
            code=f"HTTP_{exc.status_code}",
            path=request.url.path
        )
        
        # Safely serialize the response with datetime handling
        serialized_content = safe_serialize(error_response.model_dump())
        
        return JSONResponse(
            status_code=exc.status_code,
            content=serialized_content,
            headers=exc.headers
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """
        Handle all unhandled exceptions.
        
        This provides a safety net for unexpected errors, returning a generic
        error response while logging the actual exception details.
        
        Args:
            request: The incoming request that triggered the exception
            exc: The unhandled exception
            
        Returns:
            JSONResponse: Generic error response
        """
        # Log the full exception details for troubleshooting
        logger.exception(
            f"Unhandled exception: {str(exc)} | "
            f"Type: {type(exc).__name__} | "
            f"URL: {request.url} | "
            f"Method: {request.method} | "
            f"Client: {request.client.host if request.client else 'unknown'}"
        )
        
        # Determine if this is a response validation error
        is_response_validation = isinstance(exc, ResponseValidationError)
        
        # Create an appropriate generic error response
        error_response = ErrorResponse(
            detail="Response validation error, please check the logs for details" if is_response_validation 
                  else "An internal server error occurred",
            code="RESPONSE_VALIDATION_ERROR" if is_response_validation 
                 else "INTERNAL_SERVER_ERROR",
            path=request.url.path
        )
        
        # Safely serialize the response with datetime handling
        serialized_content = safe_serialize(error_response.model_dump())
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=serialized_content
        )


# Create the application instance
app = create_app()


def start(
    host: Optional[str] = None,
    port: Optional[int] = None,
    reload: bool = False,
    workers: int = 1,
    log_level: Optional[str] = None
) -> None:
    """
    Start the API server with the specified configuration.
    
    This function provides a convenient entry point for running the API
    from command line scripts or directly.
    
    Args:
        host: Host address to bind to (defaults to settings)
        port: Port to listen on (defaults to settings)
        reload: Whether to reload on code changes (development mode)
        workers: Number of worker processes
        log_level: Logging level to use
    """
    import uvicorn
    
    # Use provided values or fall back to settings
    actual_host = host or settings.host
    actual_port = port or settings.port
    actual_log_level = log_level or settings.log_level.lower()
    
    # Configure logging if not already done
    from customer_sentiment_hub.utils.logging import configure_logging
    configure_logging(actual_log_level)
    
    # Log startup information
    logger.info(
        f"Starting API server on {actual_host}:{actual_port} "
        f"(environment: {settings.environment}, reload: {reload}, workers: {workers})"
    )
    
    # Start the server
    uvicorn.run(
        "customer_sentiment_hub.api.app:app",
        host=actual_host,
        port=actual_port,
        reload=reload,
        workers=workers,
        log_level=actual_log_level,
    )


if __name__ == "__main__":
    start()