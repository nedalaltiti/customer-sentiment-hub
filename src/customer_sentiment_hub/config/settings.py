# src/customer_sentiment_hub/config/settings.py

"""
Configuration settings for the Customer Sentiment Hub.

This module defines a structured hierarchy of settings using immutable dataclasses
that provide type safety, validation, and clear organization of configuration.
"""

import logging
import os

from customer_sentiment_hub.utils.secret_manager import load_gemini_credentials

try:
    load_gemini_credentials(
        secret_name="genai-gemini-vertex-prod-api",
        region_name="us-west-1"
    )
    logging.getLogger("customer_sentiment_hub.config")\
           .info("Gemini credentials loaded from AWS Secrets Manager")
except Exception as e:
    logging.getLogger("customer_sentiment_hub.config")\
           .warning(f"Could not load Gemini credentials from Secrets Manager: {e}")

from dataclasses import dataclass, field
from typing import Optional

from customer_sentiment_hub.config.environment import (
    get_env_var, 
    get_env_var_bool, 
    get_env_var_float,
    get_env_var_int, 
    get_env_var_list
)

logger = logging.getLogger("customer_sentiment_hub.config")


@dataclass(frozen=True)
class GeminiSettings:
    """Settings for the Gemini LLM service."""
    model_name: str = "gemini-2.0-flash-001"
    temperature: float = 0.0
    max_output_tokens: int = 1024

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
    api_version: str='v1'
    @classmethod
    def from_environment(cls) -> "AppSettings":
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
                gemini=GeminiSettings.from_environment(),
                google_cloud=GoogleCloudSettings.from_environment(),
                processing=ProcessingSettings.from_environment(),
                api_version=get_env_var("API_VERSION", cls.api_version),
            )
        except Exception as e:
            logger.error(f"Error loading environment settings: {e}. Falling back to defaults.")
            return cls()


# Instantiate once at import time
try:
    settings = AppSettings.from_environment()
    logger.info(f"Loaded settings for environment: {settings.environment}")
except Exception as e:
    logger.error(f"Unrecoverable error loading AppSettings: {e}")
    settings = AppSettings()

