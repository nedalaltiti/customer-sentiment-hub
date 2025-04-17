# src/customer_sentiment_hub/__init__.py

"""
Customer Sentiment Hub - AI-powered customer feedback analysis.

This package provides:
1. A FastAPI HTTP API server for programmatic sentiment analysis
2. (Optional) A CLI interface under `customer_sentiment_hub.cli`
"""

__version__ = "0.1.0"
__author__ = "UsClarity"
__license__ = "Proprietary"


# Core domain models
from customer_sentiment_hub.domain.schema import Label, Review, ReviewOutput
from customer_sentiment_hub.domain.taxonomy import Sentiment, CategoryType

# Services
from customer_sentiment_hub.services.processor import ReviewProcessor
from customer_sentiment_hub.services.gemini_service import GeminiService

# Validation & configuration
from customer_sentiment_hub.domain.validation import ValidationService
from customer_sentiment_hub.config.settings import settings

# FastAPI app entry point
from customer_sentiment_hub.api.app import app as api_app

# Optional CLI entry-point
try:
    from customer_sentiment_hub.cli.app import app as cli_app, run_cli
except ImportError:
    cli_app = None
    run_cli = None


__all__ = [
    # Version info
    "__version__",
    "__author__",
    "__license__",

    # Domain
    "Label",
    "Review",
    "ReviewOutput",
    "Sentiment",
    "CategoryType",

    # Services
    "ReviewProcessor",
    "GeminiService",

    # Validation & Settings
    "ValidationService",
    "settings",

    # API
    "api_app",

    # CLI (if available)
    "cli_app",
    "run_cli",
]
