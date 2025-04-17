"""
Middleware components for the Customer Sentiment Hub API.

This module contains middleware functions that process requests and responses,
handling cross-cutting concerns such as request tracking, logging, security,
and performance monitoring.
"""

import time
import uuid
import logging
from typing import Callable, Dict, List, Optional, Type

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

try:
    import jwt
    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False

from customer_sentiment_hub.config.settings import settings
from customer_sentiment_hub.api.models import ErrorResponse


# Configure logging
logger = logging.getLogger("customer_sentiment_hub")


class RequestIdMiddleware(BaseHTTPMiddleware):
    """
    Adds a unique request ID to each request.
    
    Benefits:
    - Allows tracing a request through the entire system
    - Helps with debugging by correlating logs across services
    - Useful for troubleshooting client-reported issues
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Process the request
        response = await call_next(request)
        
        # Add request ID as a header to the response
        response.headers["X-Request-ID"] = request_id
        return response


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Logs incoming requests and outgoing responses with timing information.
    
    Benefits:
    - Provides visibility into API usage patterns
    - Helps identify slow endpoints for optimization
    - Facilitates debugging and performance monitoring
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        
        # Extract client information safely
        client_host = request.client.host if request.client else "unknown"
        request_id = getattr(request.state, "request_id", "unknown")
        
        # Log the request
        logger.info(
            f"Request started: {request.method} {request.url.path} "
            f"from {client_host} [request_id: {request_id}]"
        )
        
        try:
            # Process the request
            response = await call_next(request)
            
            # Calculate processing time
            process_time = time.time() - start_time
            
            # Log the response
            logger.info(
                f"Request completed: {request.method} {request.url.path} "
                f"- Status: {response.status_code} - Time: {process_time:.4f}s "
                f"[request_id: {request_id}]"
            )
            
            # Add processing time header
            response.headers["X-Process-Time"] = f"{process_time:.4f}"
            
            return response
        except Exception as e:
            # Log the exception
            logger.exception(
                f"Request failed: {request.method} {request.url.path} "
                f"- Error: {str(e)} [request_id: {request_id}]"
            )
            # Re-raise to let it be handled by the exception handlers
            raise


class RateLimitingMiddleware(BaseHTTPMiddleware):
    """
    Implements rate limiting to prevent API abuse.
    
    Benefits:
    - Protects against DoS attacks
    - Ensures fair resource sharing among clients
    - Helps maintain service stability under high load
    """
    
    def __init__(
        self, 
        app, 
        requests_limit: int = 100, 
        window_seconds: int = 60,
        excluded_paths: List[str] = None
    ):
        """Initialize with configurable limits and exclusions."""
        super().__init__(app)
        self.requests_limit = requests_limit
        self.window_seconds = window_seconds
        self.excluded_paths = excluded_paths or ["/docs", "/redoc", "/openapi.json", "/health"]
        self.clients: Dict[str, List[float]] = {}
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip rate limiting for excluded paths
        if any(request.url.path.startswith(path) for path in self.excluded_paths):
            return await call_next(request)
            
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
                content=error_response.model_dump()  
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
    Implements API key authentication.
    
    Benefits:
    - Simple authentication mechanism for API clients
    - Easier to implement than OAuth or JWT
    - Good for internal or trusted partner integrations
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
                content=error_response.model_dump()  
            )
        
        # Process the request
        return await call_next(request)
    
    def _is_valid_api_key(self, api_key: str) -> bool:
        """
        Validate the provided API key against the configured valid keys.
        
        This uses a simple list check, but could be extended to use a database
        or more sophisticated validation in production.
        """
        try:
            valid_keys = settings.security.api_keys
            return api_key in valid_keys
        except AttributeError:
            logger.warning("API key validation attempted but no valid keys configured")
            return False


class JWTAuthMiddleware(BaseHTTPMiddleware):
    """
    Implements JWT-based authentication.
    
    Benefits:
    - Stateless authentication (no server-side storage needed)
    - Can contain user information and permissions
    - Supports token expiration for better security
    
    Note: Requires the PyJWT package to be installed
    """
    
    def __init__(
        self, 
        app, 
        secret_key: str,
        algorithm: str = "HS256",
        token_header: str = "Authorization",
        excluded_paths: List[str] = None
    ):
        if not JWT_AVAILABLE:
            raise ImportError(
                "JWT authentication requires the PyJWT package. "
                "Install it with: pip install pyjwt"
            )
            
        super().__init__(app)
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.token_header = token_header
        self.excluded_paths = excluded_paths or [
            "/docs", "/redoc", "/openapi.json", "/health", "/auth/token"
        ]
    
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
                content=error_response.model_dump()  
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
                content=error_response.model_dump()  
            )
        except jwt.InvalidTokenError:
            error_response = ErrorResponse(
                detail="Invalid authentication token",
                code="INVALID_TOKEN",
                path=request.url.path
            )
            return JSONResponse(
                status_code=401,
                content=error_response.model_dump()  
            )
        
        # Process the request
        return await call_next(request)


def create_middleware_config(settings):
    """
    Create middleware configuration based on settings.
    
    This function centralizes the logic for determining which middleware
    to enable based on application settings.
    
    Returns:
        dict: Configuration for each middleware type
    """
    config = {
        "use_request_id": True,  # Always enabled
        "use_logging": True,     # Always enabled
        "use_gzip": True,        # Always enabled
        "use_rate_limiting": False,
        "use_api_key_auth": False,
        "use_jwt_auth": False,
        "cors": {
            "allow_origins": ["*"],
            "allow_credentials": True,
            "allow_methods": ["*"],
            "allow_headers": ["*"],
            "max_age": 600
        },
        "trusted_hosts": None,
    }
    
    # Try to load security settings if available
    try:
        if hasattr(settings, "security"):
            # CORS settings
            if hasattr(settings.security, "cors"):
                config["cors"] = {
                    "allow_origins": settings.security.cors.allow_origins,
                    "allow_credentials": settings.security.cors.allow_credentials,
                    "allow_methods": settings.security.cors.allow_methods,
                    "allow_headers": settings.security.cors.allow_headers,
                    "max_age": settings.security.cors.max_age
                }
            
            # Trusted hosts
            if hasattr(settings.security, "allowed_hosts"):
                config["trusted_hosts"] = settings.security.allowed_hosts
            
            # Authentication settings
            if hasattr(settings.security, "auth_type"):
                if settings.security.auth_type == "api_key":
                    config["use_api_key_auth"] = True
                elif settings.security.auth_type == "jwt":
                    config["use_jwt_auth"] = True
            
            # Rate limiting settings - only enable in production by default
            if (hasattr(settings, "environment") and settings.environment == "production" and 
                    hasattr(settings.security, "rate_limit")):
                config["use_rate_limiting"] = True
    except AttributeError as e:
        logger.warning(f"Could not fully load security settings: {str(e)}")
    
    return config


def setup_middlewares(app: FastAPI):
    """
    Configure and add all middlewares to the FastAPI application.
    
    This function centralizes middleware configuration and ensures they're
    added in the correct order for proper operation.
    
    Args:
        app: The FastAPI application instance
    """
    # Get middleware configuration
    config = create_middleware_config(settings)
    
    # Add GZip compression
    if config["use_gzip"]:
        app.add_middleware(GZipMiddleware, minimum_size=1000)
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config["cors"]["allow_origins"],
        allow_credentials=config["cors"]["allow_credentials"],
        allow_methods=config["cors"]["allow_methods"],
        allow_headers=config["cors"]["allow_headers"],
        max_age=config["cors"]["max_age"],
    )
    
    # Add trusted host middleware if configured
    if config["trusted_hosts"]:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=config["trusted_hosts"],
        )
    
    # Add basic request tracking and logging middleware
    if config["use_request_id"]:
        app.add_middleware(RequestIdMiddleware)
    
    if config["use_logging"]:
        app.add_middleware(LoggingMiddleware)
    
    # Add rate limiting middleware if enabled
    if config["use_rate_limiting"]:
        try:
            app.add_middleware(
                RateLimitingMiddleware,
                requests_limit=settings.security.rate_limit.requests_limit,
                window_seconds=settings.security.rate_limit.window_seconds,
            )
        except AttributeError:
            logger.warning("Rate limiting enabled but configuration incomplete, using defaults")
            app.add_middleware(RateLimitingMiddleware)
    
    # Add authentication middleware if enabled
    if config["use_api_key_auth"]:
        try:
            app.add_middleware(
                APIKeyAuthMiddleware,
                api_key_header=settings.security.api_key_header,
                excluded_paths=settings.security.auth_excluded_paths,
            )
        except AttributeError:
            logger.warning("API key authentication enabled but configuration incomplete, using defaults")
            app.add_middleware(APIKeyAuthMiddleware)
    
    if config["use_jwt_auth"]:
        try:
            app.add_middleware(
                JWTAuthMiddleware,
                secret_key=settings.security.jwt_secret_key,
                algorithm=settings.security.jwt_algorithm,
                token_header=settings.security.jwt_header,
                excluded_paths=settings.security.auth_excluded_paths,
            )
        except AttributeError:
            logger.warning("JWT authentication enabled but configuration incomplete")
