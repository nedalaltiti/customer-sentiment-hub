"""Configuration settings for the Customer Sentiment Hub."""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from customer_sentiment_hub.config.environment import get_env_var, get_env_var_bool


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
            temperature=float(get_env_var("GEMINI_TEMPERATURE", str(cls.temperature))),
            max_output_tokens=int(get_env_var("GEMINI_MAX_OUTPUT_TOKENS", 
                                              str(cls.max_output_tokens))),
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
            credentials_path=get_env_var("GOOGLE_APPLICATION_CREDENTIALS", None),
            project_id=get_env_var("GOOGLE_CLOUD_PROJECT", None),
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
            batch_size=int(get_env_var("PROCESSING_BATCH_SIZE", str(cls.batch_size))),
            confidence_threshold=float(get_env_var(
                "PROCESSING_CONFIDENCE_THRESHOLD", str(cls.confidence_threshold))),
            max_labels_per_review=int(get_env_var(
                "PROCESSING_MAX_LABELS", str(cls.max_labels_per_review))),
        )

@dataclass(frozen=True)
class CORSSettings:
    """CORS (Cross-Origin Resource Sharing) settings."""
    
    allow_origins: list[str] = None
    allow_credentials: bool = True
    allow_methods: list[str] = None
    allow_headers: list[str] = None
    max_age: int = 600  # 10 minutes
    
    def __post_init__(self):
        # Set default values if None
        object.__setattr__(self, 'allow_origins', 
                          self.allow_origins or ["*"])
        object.__setattr__(self, 'allow_methods', 
                          self.allow_methods or ["*"])
        object.__setattr__(self, 'allow_headers', 
                          self.allow_headers or ["*"])
    
    @classmethod
    def from_environment(cls) -> "CORSSettings":
        """Create settings from environment variables."""
        origins = get_env_var("CORS_ALLOW_ORIGINS", None)
        origins_list = origins.split(",") if origins else None
        
        methods = get_env_var("CORS_ALLOW_METHODS", None)
        methods_list = methods.split(",") if methods else None
        
        headers = get_env_var("CORS_ALLOW_HEADERS", None)
        headers_list = headers.split(",") if headers else None
        
        return cls(
            allow_origins=origins_list,
            allow_credentials=get_env_var_bool("CORS_ALLOW_CREDENTIALS", True),
            allow_methods=methods_list,
            allow_headers=headers_list,
            max_age=int(get_env_var("CORS_MAX_AGE", "600")),
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
            requests_limit=int(get_env_var("RATE_LIMIT_REQUESTS", "100")),
            window_seconds=int(get_env_var("RATE_LIMIT_WINDOW_SECONDS", "60")),
        )


@dataclass(frozen=True)
class SecuritySettings:
    """Security settings for the application."""
    
    # CORS settings
    cors: CORSSettings = CORSSettings()
    
    # Trusted hosts
    allowed_hosts: list[str] = None
    
    # Rate limiting
    rate_limit: RateLimitSettings = RateLimitSettings()
    
    # Authentication
    auth_type: str = "none"  # Options: "none", "api_key", "jwt"
    auth_excluded_paths: list[str] = None
    
    # API Key authentication
    api_keys: list[str] = None
    api_key_header: str = "X-API-Key"
    
    # JWT authentication
    jwt_secret_key: str = "your-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_header: str = "Authorization"
    
    def __post_init__(self):
        # Set default values if None
        object.__setattr__(self, 'allowed_hosts', 
                          self.allowed_hosts or ["*"])
        object.__setattr__(self, 'auth_excluded_paths', 
                          self.auth_excluded_paths or ["/docs", "/redoc", "/openapi.json", "/health"])
        object.__setattr__(self, 'api_keys', 
                          self.api_keys or ["dev-api-key"])
    
    @classmethod
    def from_environment(cls) -> "SecuritySettings":
        """Create settings from environment variables."""
        hosts = get_env_var("ALLOWED_HOSTS", None)
        hosts_list = hosts.split(",") if hosts else None
        
        excluded_paths = get_env_var("AUTH_EXCLUDED_PATHS", None)
        excluded_paths_list = excluded_paths.split(",") if excluded_paths else None
        
        api_keys = get_env_var("API_KEYS", None)
        api_keys_list = api_keys.split(",") if api_keys else None
        
        return cls(
            cors=CORSSettings.from_environment(),
            allowed_hosts=hosts_list,
            rate_limit=RateLimitSettings.from_environment(),
            auth_type=get_env_var("AUTH_TYPE", "none"),  # Default to "none" for now
            auth_excluded_paths=excluded_paths_list,
            api_keys=api_keys_list,
            api_key_header=get_env_var("API_KEY_HEADER", "X-API-Key"),
            jwt_secret_key=get_env_var("JWT_SECRET_KEY", "your-secret-key-change-in-production"),
            jwt_algorithm=get_env_var("JWT_ALGORITHM", "HS256"),
            jwt_header=get_env_var("JWT_HEADER", "Authorization"),
        )
    
@dataclass(frozen=True)
class AppSettings:
    """Main application settings."""
    app_name: str = "Customer Sentiment Hub API"
    description: str = "API for analyzing customer sentiment"
    debug: bool = False
    log_level: str = "INFO"
    version: str = "0.1.0"
    environment: str = "development" 
    host: str = "0.0.0.0"
    port: int = 8000
    gemini: GeminiSettings = GeminiSettings()
    google_cloud: GoogleCloudSettings = GoogleCloudSettings()
    processing: ProcessingSettings = ProcessingSettings()
    security: SecuritySettings = SecuritySettings()
    
    @classmethod
    def from_environment(cls) -> "AppSettings":
        """Create settings from environment variables."""
        return cls(
            debug=get_env_var_bool("DEBUG", cls.debug),
            log_level=get_env_var("LOG_LEVEL", cls.log_level),
            environment=get_env_var("ENVIRONMENT", cls.environment),
            host=get_env_var("HOST", cls.host),
            port=int(get_env_var("PORT", str(cls.port))),
            gemini=GeminiSettings.from_environment(),
            google_cloud=GoogleCloudSettings.from_environment(),
            processing=ProcessingSettings.from_environment(),
            security=SecuritySettings.from_environment(),
        )

# Global settings instance
settings = AppSettings.from_environment()