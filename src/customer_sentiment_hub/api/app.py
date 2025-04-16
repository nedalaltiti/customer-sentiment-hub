"""
Main application module for the Customer Sentiment Hub API.

This module initializes the FastAPI application, configures middleware,
and sets up routes, exception handlers, and documentation.
"""

import logging
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from customer_sentiment_hub.config.settings import settings
from customer_sentiment_hub.api.middleware import setup_middlewares
from customer_sentiment_hub.api.routes import setup_routes
from customer_sentiment_hub.api.models import ErrorResponse

import json
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("customer_sentiment_hub")


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    This function centralizes all application setup logic.
    """
    # Create the FastAPI app
    app = FastAPI(
        title=settings.app_name,
        description=settings.description,
        version=settings.version,
        docs_url="/docs" if settings.environment != "production" else None,
        redoc_url="/redoc" if settings.environment != "production" else None,
    )
    
    # Setup exception handlers
    setup_exception_handlers(app)
    
    # Setup middlewares
    setup_middlewares(app)
    
    # Setup routes
    setup_routes(app)
    
    return app

class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

def setup_exception_handlers(app: FastAPI):
    """
    Configure global exception handlers for the application.
    
    This ensures consistent error responses across the API.
    """
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """
        Handle validation errors from request parsing.
        
        Returns a structured error response with details about the validation issue.
        """
        # Log the validation error
        logger.warning(f"Validation error: {str(exc)}")
        
        # Extract error details
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
        
        return JSONResponse(
            status_code=422,
            content=error_response.model_dump()
        )
    
    
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """
        Handle HTTP exceptions raised by route handlers.
        
        Returns a standardized error response.
        """
        # Log the HTTP exception
        log_level = logging.ERROR if exc.status_code >= 500 else logging.WARNING
        logger.log(log_level, f"HTTP exception {exc.status_code}: {exc.detail}")
        
        # Create a standardized error response
        error_response = ErrorResponse(
            detail=exc.detail,
            code=f"HTTP_{exc.status_code}",
            path=request.url.path
        )
        
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response.model_dump(),
            headers=exc.headers
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """
        Handle all unhandled exceptions.
        
        Provides a generic error response while logging the actual exception.
        """
        # Log the unhandled exception
        logger.exception(f"Unhandled exception: {str(exc)}")
        
        # Create a generic error response
        error_response = ErrorResponse(
            detail="An internal server error occurred",
            code="INTERNAL_SERVER_ERROR",
            path=request.url.path
        )
        
        # Convert to dictionary safely
        if hasattr(error_response, "model_dump"):  # Pydantic v2
            error_dict = error_response.model_dump()
        else:  # Pydantic v1
            error_dict = error_response.dict()
        
        # Serialize with custom encoder to handle datetime
        error_json = json.dumps(error_dict, cls=CustomJSONEncoder)
        error_dict = json.loads(error_json)  # Convert back to dict
        
        return JSONResponse(
            status_code=500,
            content=error_dict
        )



# Create the application instance
app = create_app()


def start():
    """
    Start the API server.
    
    This function is the entry point for running the application.
    """
    import uvicorn
    uvicorn.run(
        "customer_sentiment_hub.api.app:app",
        host=settings.host,
        port=settings.port,
        reload=settings.environment == "development",
    )


if __name__ == "__main__":
    start()