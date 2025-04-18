"""
Configuration settings for the Customer Sentiment Hub.

This module defines a structured hierarchy of settings using immutable dataclasses
that provide type safety, validation, and clear organization of configuration.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Union
import logging

from customer_sentiment_hub.config.environment import (
    get_env_var, 
    get_env_var_bool, 
    get_env_var_float,
    get_env_var_int, 
    get_env_var_list
)

# Configure logging
logger = logging.getLogger("customer_sentiment_hub.config")


@dataclass(frozen=True)
class GeminiSettings:
    """Settings for the Gemini LLM service."""
    
    model_name: str = "gemini-2.0-flash-001"
    temperature: float = 0.0
    max_output_tokens: int = 1024
    
    @classmethod
    def from_environment(cls) -> "GeminiSettings":
        """Create settings from environment variables."""
        return cls(
            model_name=get_env_var("GEMINI_MODEL_NAME", cls.model_name),
            temperature=get_env_var_float("GEMINI_TEMPERATURE", cls.temperature),
            max_output_tokens=get_env_var_int("GEMINI_MAX_OUTPUT_TOKENS", cls.max_output_tokens),
        )


@dataclass(frozen=True)
class GoogleCloudSettings:
    """Settings for Google Cloud services."""
    
    credentials_path: Optional[str] = None
    project_id: Optional[str] = None
    location: str = "us-central1"
    
    @classmethod
    def from_environment(cls) -> "GoogleCloudSettings":
        """Create settings from environment variables."""
        return cls(
            credentials_path=get_env_var("GOOGLE_APPLICATION_CREDENTIALS"),
            project_id=get_env_var("GOOGLE_CLOUD_PROJECT"),
            location=get_env_var("GOOGLE_CLOUD_LOCATION", cls.location),
        )


@dataclass(frozen=True)
class ProcessingSettings:
    """Settings for review processing."""
    
    batch_size: int = 5
    confidence_threshold: float = 0.3
    max_labels_per_review: int = 5
    
    @classmethod
    def from_environment(cls) -> "ProcessingSettings":
        """Create settings from environment variables."""
        return cls(
            batch_size=get_env_var_int("PROCESSING_BATCH_SIZE", cls.batch_size),
            confidence_threshold=get_env_var_float(
                "PROCESSING_CONFIDENCE_THRESHOLD", cls.confidence_threshold),
            max_labels_per_review=get_env_var_int(
                "PROCESSING_MAX_LABELS", cls.max_labels_per_review),
        )


@dataclass(frozen=True)
class CORSSettings:
    """CORS (Cross-Origin Resource Sharing) settings."""
    
    # Use field with default_factory to avoid mutable default values
    allow_origins: List[str] = field(default_factory=lambda: ["*"])
    allow_credentials: bool = True
    allow_methods: List[str] = field(default_factory=lambda: ["*"])
    allow_headers: List[str] = field(default_factory=lambda: ["*"])
    max_age: int = 600  # 10 minutes
    
    @classmethod
    def from_environment(cls) -> "CORSSettings":
        """Create settings from environment variables."""
        return cls(
            allow_origins=get_env_var_list("CORS_ALLOW_ORIGINS", ["*"]),
            allow_credentials=get_env_var_bool("CORS_ALLOW_CREDENTIALS", True),
            allow_methods=get_env_var_list("CORS_ALLOW_METHODS", ["*"]),
            allow_headers=get_env_var_list("CORS_ALLOW_HEADERS", ["*"]),
            max_age=get_env_var_int("CORS_MAX_AGE", 600),
        )


@dataclass(frozen=True)
class RateLimitSettings:
    """Rate limiting settings."""
    
    requests_limit: int = 100
    window_seconds: int = 60
    
    @classmethod
    def from_environment(cls) -> "RateLimitSettings":
        """Create settings from environment variables."""
        return cls(
            requests_limit=get_env_var_int("RATE_LIMIT_REQUESTS", 100),
            window_seconds=get_env_var_int("RATE_LIMIT_WINDOW_SECONDS", 60),
        )


@dataclass(frozen=True)
class SecuritySettings:
    """Security settings for the application."""
    
    # CORS settings
    cors: CORSSettings = field(default_factory=CORSSettings)
    
    # Trusted hosts - using default_factory to avoid mutable default
    allowed_hosts: List[str] = field(default_factory=lambda: ["*"])
    
    # Rate limiting
    rate_limit: RateLimitSettings = field(default_factory=RateLimitSettings)
    
    # Authentication - with more explicit defaults
    auth_type: str = "none"  # Options: "none", "api_key", "jwt"
    auth_excluded_paths: List[str] = field(
        default_factory=lambda: ["/docs", "/redoc", "/openapi.json", "/health"]
    )
    
    # API Key authentication
    api_keys: List[str] = field(default_factory=lambda: ["dev-api-key"])
    api_key_header: str = "X-API-Key"
    
    # JWT authentication
    jwt_secret_key: str = "your-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_header: str = "Authorization"
    
    @classmethod
    def from_environment(cls) -> "SecuritySettings":
        """Create settings from environment variables."""
        return cls(
            cors=CORSSettings.from_environment(),
            allowed_hosts=get_env_var_list("ALLOWED_HOSTS", ["*"]),
            rate_limit=RateLimitSettings.from_environment(),
            auth_type=get_env_var("AUTH_TYPE", "none"),
            auth_excluded_paths=get_env_var_list(
                "AUTH_EXCLUDED_PATHS", 
                ["/docs", "/redoc", "/openapi.json", "/health"]
            ),
            api_keys=get_env_var_list("API_KEYS", ["dev-api-key"]),
            api_key_header=get_env_var("API_KEY_HEADER", "X-API-Key"),
            jwt_secret_key=get_env_var("JWT_SECRET_KEY", "your-secret-key-change-in-production"),
            jwt_algorithm=get_env_var("JWT_ALGORITHM", "HS256"),
            jwt_header=get_env_var("JWT_HEADER", "Authorization"),
        )


@dataclass(frozen=True)
class AppSettings:
    """Main application settings container."""
    
    # Basic application info
    app_name: str = "Customer Sentiment Hub API"
    description: str = "API for analyzing customer sentiment"
    version: str = "0.1.0"
    
    # Environment and server settings
    debug: bool = False
    log_level: str = "INFO"
    environment: str = "development" 
    host: str = "0.0.0.0"
    port: int = 8000
    
    # Component-specific settings
    gemini: GeminiSettings = field(default_factory=GeminiSettings)
    google_cloud: GoogleCloudSettings = field(default_factory=GoogleCloudSettings)
    processing: ProcessingSettings = field(default_factory=ProcessingSettings)
    security: SecuritySettings = field(default_factory=SecuritySettings)
    
    @classmethod
    def from_environment(cls) -> "AppSettings":
        """Create settings from environment variables."""
        try:
            return cls(
                # Basic info
                app_name=get_env_var("APP_NAME", cls.app_name),
                description=get_env_var("APP_DESCRIPTION", cls.description),
                version=get_env_var("APP_VERSION", cls.version),
                
                # Environment settings
                debug=get_env_var_bool("DEBUG", cls.debug),
                log_level=get_env_var("LOG_LEVEL", cls.log_level),
                environment=get_env_var("ENVIRONMENT", cls.environment),
                host=get_env_var("HOST", cls.host),
                port=get_env_var_int("PORT", cls.port),
                
                # Component settings
                gemini=GeminiSettings.from_environment(),
                google_cloud=GoogleCloudSettings.from_environment(),
                processing=ProcessingSettings.from_environment(),
                security=SecuritySettings.from_environment(),
            )
        except Exception as e:
            # Log error but continue with defaults
            logger.error(f"Error loading environment settings: {str(e)}. Using defaults.")
            return cls()


# Cache and validate the global settings on module import for better performance
try:
    settings = AppSettings.from_environment()
    logger.info(f"Settings loaded for environment: {settings.environment}")
except Exception as e:
    # Fallback to defaults if environment loading fails
    logger.error(f"Failed to load settings from environment: {str(e)}. Using defaults.")
    settings = AppSettings()