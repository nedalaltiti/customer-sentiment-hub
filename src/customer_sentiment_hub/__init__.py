"""
Customer Sentiment Hub - AI-powered customer feedback analysis.

This package provides sentiment analysis for customer reviews through:
1. An HTTP API server for programmatic access
2. A command-line interface for direct interaction
"""

# Version information
__version__ = "0.1.0"
__author__ = "UsClarity"
__license__ = "Proprietary"

# Core domain models
from customer_sentiment_hub.domain.schema import Label, Review, ReviewOutput, AnalysisRequest
from customer_sentiment_hub.domain.taxonomy import Sentiment, CategoryType

# Services
from customer_sentiment_hub.services.processor import ReviewProcessor
from customer_sentiment_hub.services.gemini_service import GeminiService

# Validation and configuration
from customer_sentiment_hub.domain.validation import ValidationService
from customer_sentiment_hub.config.settings import settings

# API entry points
from customer_sentiment_hub.api.app import start as start_api_server, app as api_app

# Define public API
__all__ = [
    # Version info
    "__version__",
    
    # Core domain models
    "Label",
    "Review",
    "ReviewOutput",
    "AnalysisRequest",
    "Sentiment",
    "CategoryType",
    
    # Services
    "ReviewProcessor",
    "GeminiService",
    
    # Validation and configuration
    "ValidationService",
    "settings",
    
    # API components
    "start_api_server",
    "api_app",
]

# Dynamic imports to avoid circular dependencies
def __getattr__(name):
    if name == 'cli_app':
        from customer_sentiment_hub.cli.app import app as cli_app
        return cli_app
    elif name == 'run_cli':
        from customer_sentiment_hub.cli.app import run_cli
        return run_cli
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")