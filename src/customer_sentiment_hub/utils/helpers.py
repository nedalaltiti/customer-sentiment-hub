"""
Helper functions for common operations.

This module provides utilities for file operations, data processing,
and other common tasks used throughout the application.
"""

import json
import os
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, TypeVar, Union, Callable, cast

# Configure module-level logger
logger = logging.getLogger(__name__)

T = TypeVar('T')

def load_json_file(file_path: Union[str, Path]) -> Dict[str, Any]:
    """
    Load and parse a JSON file with robust error handling.
    
    Args:
        file_path: Path to the JSON file (string or Path object)
        
    Returns:
        Dict[str, Any]: The loaded JSON data
        
    Raises:
        FileNotFoundError: If the file doesn't exist
        json.JSONDecodeError: If the file contains invalid JSON
        PermissionError: If the file cannot be read due to permissions
    """
    # Convert to Path object for better path handling
    path = Path(file_path)
    
    try:
        # Use with context manager for proper resource handling
        with path.open('r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"JSON file not found: {path}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in file {path}: {str(e)}")
        raise
    except PermissionError:
        logger.error(f"Permission denied when reading file: {path}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error reading JSON file {path}: {str(e)}")
        raise


def save_json_file(
    data: Any, 
    file_path: Union[str, Path], 
    indent: int = 2,
    ensure_ascii: bool = False
) -> None:
    """
    Save data to a JSON file with directory creation and error handling.
    
    Args:
        data: The data to save (must be JSON serializable)
        file_path: Path to the output file (string or Path object)
        indent: Number of spaces for indentation (default: 2)
        ensure_ascii: Whether to escape non-ASCII characters (default: False)
        
    Raises:
        TypeError: If the data is not JSON serializable
        PermissionError: If the file cannot be written due to permissions
    """
    # Convert to Path object for better path handling
    path = Path(file_path)
    
    try:
        # Create directory if it doesn't exist
        path.parent.mkdir(parents=True, exist_ok=True)
        
        # Use with context manager for proper resource handling
        with path.open('w', encoding='utf-8') as f:
            json.dump(data, f, indent=indent, ensure_ascii=ensure_ascii)
            
        logger.debug(f"Successfully saved JSON data to {path}")
    except TypeError as e:
        logger.error(f"Cannot serialize to JSON: {str(e)}")
        raise
    except PermissionError:
        logger.error(f"Permission denied when writing to file: {path}")
        raise
    except Exception as e:
        logger.error(f"Error saving JSON file {path}: {str(e)}")
        raise


def extract_review_texts(data: Union[List, Dict]) -> List[str]:
    """
    Extract review texts from various data structures.
    
    This function handles different input formats:
    - List of strings: Returns the strings
    - List of dictionaries with 'text' key: Returns the text values
    - Dictionary with 'reviews' key: Extracts texts from the reviews
    - Dictionary with string values: Returns the values
    
    Args:
        data: Input data containing reviews
        
    Returns:
        List[str]: Extracted review texts
        
    Example:
        >>> extract_review_texts(["Review 1", "Review 2"])
        ["Review 1", "Review 2"]
        
        >>> extract_review_texts([{"text": "Review 1"}, {"text": "Review 2"}])
        ["Review 1", "Review 2"]
        
        >>> extract_review_texts({"reviews": [{"text": "Review 1"}, {"text": "Review 2"}]})
        ["Review 1", "Review 2"]
    """
    review_texts = []
    
    # Handle different input formats
    if isinstance(data, list):
        # Process list of strings or dictionaries
        for item in data:
            if isinstance(item, str):
                review_texts.append(item)
            elif isinstance(item, dict) and 'text' in item:
                review_texts.append(item['text'])
                
    elif isinstance(data, dict):
        # Check for reviews key first
        if 'reviews' in data and isinstance(data['reviews'], list):
            # Extract from reviews list
            for review in data['reviews']:
                if isinstance(review, dict) and 'text' in review:
                    review_texts.append(review['text'])
        else:
            # Extract string values from dictionary
            for key, value in data.items():
                if isinstance(value, str):
                    review_texts.append(value)
    
    return review_texts


def batch_items(items: List[T], batch_size: int) -> List[List[T]]:
    """
    Split a list into batches of specified size.
    
    This function is useful for processing large datasets in manageable chunks.
    
    Args:
        items: The list to split
        batch_size: Maximum size of each batch (must be > 0)
        
    Returns:
        List[List[T]]: List of batches
        
    Raises:
        ValueError: If batch_size is less than or equal to zero
        
    Example:
        >>> batch_items([1, 2, 3, 4, 5], 2)
        [[1, 2], [3, 4], [5]]
    """
    if batch_size <= 0:
        raise ValueError("Batch size must be greater than zero")
    
    if not items:
        return []
    
    # Use list comprehension for efficiency
    return [items[i:i + batch_size] for i in range(0, len(items), batch_size)]


def safe_get(data: Dict[str, Any], key_path: str, default: Any = None) -> Any:
    """
    Safely access nested dictionary values using dot notation.
    
    Args:
        data: Dictionary to access
        key_path: Path to the value using dot notation (e.g., "user.profile.name")
        default: Value to return if path doesn't exist
        
    Returns:
        Any: Value at the specified path, or default if not found
        
    Example:
        >>> safe_get({"user": {"profile": {"name": "John"}}}, "user.profile.name")
        "John"
        >>> safe_get({"user": {"profile": {}}}, "user.profile.name", "Unknown")
        "Unknown"
    """
    keys = key_path.split('.')
    result = data
    
    for key in keys:
        if isinstance(result, dict) and key in result:
            result = result[key]
        else:
            return default
            
    return result