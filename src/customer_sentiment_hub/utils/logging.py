"""Logging configuration."""

import logging
import sys
from typing import Optional

from customer_sentiment_hub.config.settings import settings


def configure_logging(log_level: Optional[str] = None) -> None:
    """
    Configure logging for the application.
    
    Args:
        log_level: Override log level (optional)
    """
    level = getattr(logging, log_level or settings.log_level)
    
    # Configure root logger
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("customer_sentiment_hub.log")
        ]
    )
    
    # Set specific logger levels
    logging.getLogger("customer_sentiment_hub").setLevel(level)
    
    # Keep third-party loggers quieter
    logging.getLogger("google").setLevel(logging.WARNING)
    logging.getLogger("langchain").setLevel(logging.WARNING)
    
    logging.info(f"Logging configured at level {logging.getLevelName(level)}")