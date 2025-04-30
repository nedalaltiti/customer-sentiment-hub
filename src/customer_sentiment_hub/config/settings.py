# src/customer_sentiment_hub/config/settings.py

"""
Configuration settings for the Customer Sentiment Hub.

This module defines a structured hierarchy of settings using immutable dataclasses
that provide type safety, validation, and clear organization of configuration.
"""

import logging
import os
from dataclasses import dataclass, field
from typing import Optional, List

from customer_sentiment_hub.config.environment import (
    get_env_var, 
    get_env_var_bool, 
    get_env_var_float,
    get_env_var_int, 
    get_env_var_list
)
from customer_sentiment_hub.utils.secret_manager import load_gemini_credentials

logger = logging.getLogger("customer_sentiment_hub.config")

# Attempt to load Gemini credentials early (consider moving inside AppSettings if needed)
try:
    # Make sure AWS credentials are available in the environment for this to work
    # or handle potential Boto3 NoCredentialsError
    load_gemini_credentials(
        secret_name=get_env_var("AWS_SECRET_NAME", "genai-gemini-vertex-prod-api"),
        region_name=get_env_var("AWS_REGION", "us-west-1")
    )
    logger.info("Attempted to load Gemini credentials from AWS Secrets Manager")
except Exception as e:
    logger.warning(f"Could not load Gemini credentials from Secrets Manager: {e}. Ensure AWS credentials and region are set.")


@dataclass(frozen=True)
class GeminiSettings:
    """Settings for the Gemini LLM service."""
    model_name: str = "gemini-1.5-flash-latest" # Updated default
    temperature: float = 0.1 # Adjusted default
    max_output_tokens: int = 2048 # Increased default

    @classmethod
    def from_environment(cls) -> "GeminiSettings":
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
        # GOOGLE_APPLICATION_CREDENTIALS is the standard env var for ADC
        # project_id might be inferred from credentials or environment
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
        return cls(
            batch_size=get_env_var_int("PROCESSING_BATCH_SIZE", cls.batch_size),
            confidence_threshold=get_env_var_float(
                "PROCESSING_CONFIDENCE_THRESHOLD", cls.confidence_threshold),
            max_labels_per_review=get_env_var_int(
                "PROCESSING_MAX_LABELS", cls.max_labels_per_review),
        )

# --- Added Freshdesk Settings --- 
@dataclass(frozen=True)
class FreshdeskSettings:
    """Settings for Freshdesk integration."""
    api_key: Optional[str] = None # Made optional to allow graceful degradation
    domain: Optional[str] = None   # Made optional
    # Define default custom field names used in Freshdesk
    custom_field_category: str = "cf_category" # Example field name
    custom_field_subcategory: str = "cf_subcategory" # Example field name
    custom_field_sentiment: str = "cf_sentiment" # Example field name
    # Optional: Add webhook secret for validation
    webhook_secret: Optional[str] = None

    @classmethod
    def from_environment(cls) -> "FreshdeskSettings":
        # Load required fields from environment variables
        api_key = get_env_var("FRESHDESK_API_KEY")
        domain = get_env_var("FRESHDESK_DOMAIN")
        
        # Load optional fields
        webhook_secret = get_env_var("FRESHDESK_WEBHOOK_SECRET")
        cf_category = get_env_var("FRESHDESK_CUSTOM_FIELD_CATEGORY", cls.custom_field_category)
        cf_subcategory = get_env_var("FRESHDESK_CUSTOM_FIELD_SUBCATEGORY", cls.custom_field_subcategory)
        cf_sentiment = get_env_var("FRESHDESK_CUSTOM_FIELD_SENTIMENT", cls.custom_field_sentiment)
        
        # Log a warning if essential fields are missing, but still return the object
        if not api_key:
            logger.warning("FRESHDESK_API_KEY environment variable not set. Freshdesk integration will be disabled.")
        if not domain:
            logger.warning("FRESHDESK_DOMAIN environment variable not set. Freshdesk integration will be disabled.")
            
        return cls(
            api_key=api_key,
            domain=domain,
            webhook_secret=webhook_secret,
            custom_field_category=cf_category,
            custom_field_subcategory=cf_subcategory,
            custom_field_sentiment=cf_sentiment,
        )

# --- End Added Freshdesk Settings --- 

@dataclass(frozen=True)
class AppSettings:
    """Main application settings container."""

    # Basic application info
    app_name: str = "Customer Sentiment Hub API"
    description: str = "API for analyzing customer sentiment"
    version: str = "0.1.0" # Consider loading from pyproject.toml

    # Environment and server settings
    debug: bool = False
    log_level: str = "INFO"
    environment: str = "development" 
    host: str = "0.0.0.0"
    port: int = 8000
    api_version: str = "v1"
    # Optional: CORS origins
    cors_origins: List[str] = field(default_factory=list) 

    # Component-specific settings
    gemini: GeminiSettings = field(default_factory=GeminiSettings.from_environment)
    google_cloud: GoogleCloudSettings = field(default_factory=GoogleCloudSettings.from_environment)
    processing: ProcessingSettings = field(default_factory=ProcessingSettings.from_environment)
    # Add Freshdesk settings instance
    freshdesk: FreshdeskSettings = field(default_factory=FreshdeskSettings.from_environment)

    @classmethod
    def from_environment(cls) -> "AppSettings":
        # This method now primarily orchestrates the component-specific loaders
        try:
            return cls(
                app_name=get_env_var("APP_NAME", cls.app_name),
                description=get_env_var("APP_DESCRIPTION", cls.description),
                version=get_env_var("APP_VERSION", cls.version),
                debug=get_env_var_bool("DEBUG", cls.debug),
                log_level=get_env_var("LOG_LEVEL", cls.log_level),
                environment=get_env_var("ENVIRONMENT", cls.environment),
                host=get_env_var("HOST", cls.host),
                port=get_env_var_int("PORT", cls.port),
                api_version=get_env_var("API_VERSION", cls.api_version),
                cors_origins=get_env_var_list("CORS_ORIGINS"), # Load CORS origins
                # Factories are called automatically by dataclass
            )
        except Exception as e:
            logger.error(f"Error loading environment settings: {e}. Falling back to defaults.", exc_info=True)
            # Return default instance - component settings will use their defaults too
            return cls()

# Instantiate once at import time
try:
    settings = AppSettings.from_environment()
    logger.info(f"Loaded settings for environment: {settings.environment}")
    # You can add more detailed logging of loaded settings if needed, being careful with secrets
    # logger.debug(f"Loaded settings: {settings}") 
except Exception as e:
    logger.critical(f"Unrecoverable error loading AppSettings: {e}", exc_info=True)
    # Fallback to default settings if loading fails critically
    settings = AppSettings()
