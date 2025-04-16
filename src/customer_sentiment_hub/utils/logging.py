"""
Logging configuration for the Customer Sentiment Hub.

This module provides functions and configuration for setting up
consistent, flexible logging throughout the application.
"""

import logging
import logging.config
import sys
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Union, List

from customer_sentiment_hub.config.settings import settings


def configure_logging(
    log_level: Optional[str] = None,
    log_file: Optional[Union[str, Path]] = None,
    log_format: Optional[str] = None,
    console_output: bool = True,
    file_output: bool = True,
) -> None:
    """
    Configure logging for the application with flexible options.
    
    This function sets up logging handlers, formats, and levels for the application.
    It configures both console and file logging with appropriate formatting.
    
    Args:
        log_level: Override log level from settings (e.g., "DEBUG", "INFO")
        log_file: Custom log file path (defaults to application name + date)
        log_format: Custom log format string
        console_output: Whether to enable console logging
        file_output: Whether to enable file logging
    """
    # Determine log level
    level_name = log_level or settings.log_level
    level = getattr(logging, level_name.upper())
    
    # Determine log file path
    if log_file is None and file_output:
        # Create logs directory if it doesn't exist
        logs_dir = Path("logs")
        logs_dir.mkdir(exist_ok=True)
        
        # Use application name and date for log file
        app_name = getattr(settings, "app_name", "customer_sentiment_hub").lower().replace(" ", "_")
        date_str = datetime.now().strftime("%Y-%m-%d")
        log_file = logs_dir / f"{app_name}_{date_str}.log"
    
    # Set default log format if not provided
    if log_format is None:
        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Create handlers
    handlers: List[logging.Handler] = []
    
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(logging.Formatter(log_format))
        handlers.append(console_handler)
    
    if file_output and log_file:
        # Create directory for log file if it doesn't exist
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(str(log_path))
        file_handler.setLevel(level)
        file_handler.setFormatter(logging.Formatter(log_format))
        handlers.append(file_handler)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Remove existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add new handlers
    for handler in handlers:
        root_logger.addHandler(handler)
    
    # Configure specific loggers
    app_logger = logging.getLogger("customer_sentiment_hub")
    app_logger.setLevel(level)
    
    # Keep third-party loggers quieter
    if level > logging.DEBUG:
        logging.getLogger("google").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("fastapi").setLevel(logging.WARNING)
    
    # Log configuration details
    app_logger.info(f"Logging configured at level {logging.getLevelName(level)}")
    for handler in handlers:
        if isinstance(handler, logging.FileHandler):
            app_logger.info(f"Log file: {handler.baseFilename}")


def configure_logging_from_dict(config: Dict) -> None:
    """
    Configure logging using a dictionary configuration.
    
    This allows for more complex logging setups using the standard
    Python logging configuration dictionary format.
    
    Args:
        config: Dictionary configuration for logging
    """
    logging.config.dictConfig(config)
    logging.info("Logging configured from dictionary configuration")


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the given name, creating it if it doesn't exist.
    
    This is a convenience function for getting loggers with the correct
    naming convention for the application.
    
    Args:
        name: The name of the logger (can be module name)
        
    Returns:
        logging.Logger: Configured logger instance
    """
    # If name is a module, use its name
    if "." in name and not name.startswith("customer_sentiment_hub"):
        # Extract module name and prepend application namespace
        module_name = name.split(".")[-1]
        return logging.getLogger(f"customer_sentiment_hub.{module_name}")
    
    # Otherwise use the name directly
    if not name.startswith("customer_sentiment_hub."):
        name = f"customer_sentiment_hub.{name}"
    
    return logging.getLogger(name)