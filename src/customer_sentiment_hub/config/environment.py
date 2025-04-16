"""Environment variable handling."""

import os
from typing import Any, Optional, TypeVar

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

T = TypeVar("T")


def get_env_var(name: str, default: Optional[T] = None) -> Any:
    """
    Get environment variable value.
    
    Args:
        name: The name of the environment variable
        default: Default value if not set
        
    Returns:
        The value of the environment variable or the default
    """
    return os.environ.get(name, default)


def get_env_var_bool(name: str, default: bool = False) -> bool:
    """
    Get boolean environment variable value.
    
    Args:
        name: The name of the environment variable
        default: Default value if not set
        
    Returns:
        The boolean value of the environment variable
    """
    value = os.environ.get(name, str(default)).lower()
    return value in ("1", "true", "yes", "y", "on")