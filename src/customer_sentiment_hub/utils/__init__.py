"""
Utility functions and helpers for the Customer Sentiment Hub.

This package provides common utilities, error handling patterns,
logging configuration, and helper functions used throughout the application.
"""

from customer_sentiment_hub.utils.helpers import (
    load_json_file, save_json_file, 
    extract_review_texts, batch_items
)
from customer_sentiment_hub.utils.logging import configure_logging
from customer_sentiment_hub.utils.result import Result, Success, Error

__all__ = [
    # File utilities
    'load_json_file', 'save_json_file',
    
    # Data processing
    'extract_review_texts', 'batch_items',
    
    # Application configuration
    'configure_logging',
    
    # Error handling
    'Result', 'Success', 'Error'
]