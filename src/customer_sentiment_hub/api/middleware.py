"""
Middleware components for the Customer Sentiment Hub API.

This module contains middleware functions that process requests and responses,
handling cross-cutting concerns such as authentication, logging, rate limiting,
CORS, and error handling.
"""

import time
import uuid
import logging
from fastapi import Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable, Dict, List, Optional
import jwt
from datetime import datetime, timedelta

from customer_sentiment_hub.config.settings import settings
from customer_sentiment_hub.api.models import ErrorResponse


# Configure logging
logger = logging.getLogger("customer_sentiment_hub")


class RequestIdMiddleware(BaseHTTPMiddleware):
    """
    Middleware that adds a unique request ID to each request.
    
    This helps with tracing requests across the system and debugging.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = str(uuid.uuid4())
        # Add request ID to request state for access in route handlers
        request.state.request_id = request_id
        # Add request ID as a header to the response
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that logs incoming requests and outgoing responses.
    
    Captures timing information and request details for monitoring and debugging.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        
        # Extract client information safely
        client_host = request.client.host if request.client else "unknown"
        
        # Log the request
        logger.info(
            f"Request started: {request.method} {request.url.path} from {client_host}"
        )
        
        try:
            # Process the request
            response = await call_next(request)
            
            # Calculate processing time
            process_time = time.time() - start_time
            
            # Log the response
            logger.info(
                f"Request completed: {request.method} {request.url.path} "
                f"- Status: {response.status_code} - Time: {process_time:.4f}s"
            )
            
            # Add processing time header
            response.headers["X-Process-Time"] = str(process_time)
            
            return response
        except Exception as e:
            # Log the exception
            logger.exception(
                f"Request failed: {request.method} {request.url.path} - Error: {str(e)}"
            )
            # Re-raise to let it be handled by the exception handlers
            raise


class RateLimitingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that implements rate limiting for API requests.
    
    Prevents abuse by limiting the number of requests per client.
    """
    
    def __init__(self, app, requests_limit: int = 100, window_seconds: int = 60):
        super().__init__(app)
        self.requests_limit = requests_limit
        self.window_seconds = window_seconds
        self.clients: Dict[str, List[float]] = {}
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Get client IP address
        client_ip = request.client.host if request.client else "unknown"
        
        # Get current timestamp
        current_time = time.time()
        
        # Initialize client data if not exists
        if client_ip not in self.clients:
            self.clients[client_ip] = []
        
        # Clean old requests (outside the time window)
        self.clients[client_ip] = [
            timestamp for timestamp in self.clients[client_ip] 
            if current_time - timestamp < self.window_seconds
        ]
        
        # Check if limit exceeded
        if len(self.clients[client_ip]) >= self.requests_limit:
            # Return rate limit error
            error_response = ErrorResponse(
                detail=f"Rate limit exceeded. Maximum {self.requests_limit} requests per {self.window_seconds} seconds.",
                code="RATE_LIMIT_EXCEEDED",
                path=request.url.path
            )
            return JSONResponse(
                status_code=429,
                content=error_response.dict()
            )
        
        # Add current request timestamp
        self.clients[client_ip].append(current_time)
        
        # Process the request
        response = await call_next(request)
        
        # Add rate limit headers
        remaining = self.requests_limit - len(self.clients[client_ip])
        response.headers["X-RateLimit-Limit"] = str(self.requests_limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(current_time + self.window_seconds))
        
        return response


class APIKeyAuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware that implements API key authentication.
    
    Validates API keys included in request headers.
    """
    
    def __init__(self, app, api_key_header: str = "X-API-Key", excluded_paths: List[str] = None):
        super().__init__(app)
        self.api_key_header = api_key_header
        self.excluded_paths = excluded_paths or ["/docs", "/redoc", "/openapi.json", "/health"]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip authentication for excluded paths
        if any(request.url.path.startswith(path) for path in self.excluded_paths):
            return await call_next(request)
        
        # Get API key from header
        api_key = request.headers.get(self.api_key_header)
        
        # Validate API key
        if not api_key or not self._is_valid_api_key(api_key):
            error_response = ErrorResponse(
                detail="Invalid or missing API key",
                code="INVALID_API_KEY",
                path=request.url.path
            )
            return JSONResponse(
                status_code=401,
                content=error_response.dict()
            )
        
        # Process the request
        return await call_next(request)
    
    def _is_valid_api_key(self, api_key: str) -> bool:
        """
        Validate the provided API key against the configured valid keys.
        
        In a production environment, this would typically check against a database.
        """
        # For demonstration, we'll check against a list of valid keys in settings
        valid_keys = settings.security.api_keys
        return api_key in valid_keys


class JWTAuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware that implements JWT-based authentication.
    
    Validates JWT tokens included in request headers.
    """
    
    def __init__(
        self, 
        app, 
        secret_key: str,
        algorithm: str = "HS256",
        token_header: str = "Authorization",
        excluded_paths: List[str] = None
    ):
        super().__init__(app)
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.token_header = token_header
        self.excluded_paths = excluded_paths or ["/docs", "/redoc", "/openapi.json", "/health", "/auth/token"]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip authentication for excluded paths
        if any(request.url.path.startswith(path) for path in self.excluded_paths):
            return await call_next(request)
        
        # Get authorization header
        auth_header = request.headers.get(self.token_header)
        
        # Check if header exists and has the correct format
        if not auth_header or not auth_header.startswith("Bearer "):
            error_response = ErrorResponse(
                detail="Invalid or missing authentication token",
                code="INVALID_TOKEN",
                path=request.url.path
            )
            return JSONResponse(
                status_code=401,
                content=error_response.dict()
            )
        
        # Extract the token
        token = auth_header.split(" ")[1]
        
        # Validate the token
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            # Add user information to request state
            request.state.user = payload.get("sub")
            request.state.user_role = payload.get("role")
        except jwt.ExpiredSignatureError:
            error_response = ErrorResponse(
                detail="Authentication token has expired",
                code="TOKEN_EXPIRED",
                path=request.url.path
            )
            return JSONResponse(
                status_code=401,
                content=error_response.dict()
            )
        except jwt.InvalidTokenError:
            error_response = ErrorResponse(
                detail="Invalid authentication token",
                code="INVALID_TOKEN",
                path=request.url.path
            )
            return JSONResponse(
                status_code=401,
                content=error_response.dict()
            )
        
        # Process the request
        return await call_next(request)


def setup_middlewares(app):
    """
    Configure and add all middlewares to the FastAPI application.
    
    This function centralizes middleware configuration and ensures they're
    added in the correct order.
    """
    # Add GZip compression
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.security.cors.allow_origins,
        allow_credentials=settings.security.cors.allow_credentials,
        allow_methods=settings.security.cors.allow_methods,
        allow_headers=settings.security.cors.allow_headers,
        max_age=settings.security.cors.max_age,
    )
    
    # Add trusted host middleware
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.security.allowed_hosts,
    )
    
    # Add custom middlewares in the correct order (outside-in)
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(LoggingMiddleware)
    
    # Only add rate limiting in production
    if settings.environment == "production":
        app.add_middleware(
            RateLimitingMiddleware,
            requests_limit=settings.security.rate_limit.requests_limit,
            window_seconds=settings.security.rate_limit.window_seconds,
        )
    
    # Add authentication middleware based on configuration
    if settings.security.auth_type == "api_key":
        app.add_middleware(
            APIKeyAuthMiddleware,
            api_key_header=settings.security.api_key_header,
            excluded_paths=settings.security.auth_excluded_paths,
        )
    elif settings.security.auth_type == "jwt":
        app.add_middleware(
            JWTAuthMiddleware,
            secret_key=settings.security.jwt_secret_key,
            algorithm=settings.security.jwt_algorithm,
            token_header=settings.security.jwt_header,
            excluded_paths=settings.security.auth_excluded_paths,
        )