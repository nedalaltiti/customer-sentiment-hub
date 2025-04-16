"""Result type for error handling."""

from typing import Any, Generic, Optional, TypeVar, Union

T = TypeVar('T')


class Result(Generic[T]):
    """
    A result type that can contain either a value or an error.
    
    This helps with better error handling without exceptions.
    """
    
    def is_success(self) -> bool:
        """
        Check if the result is a success.
        
        Returns:
            bool: True if the result is a success, False otherwise
        """
        raise NotImplementedError("Subclasses must implement is_success")


class Success(Result[T]):
    """A successful result containing a value."""
    
    def __init__(self, value: T):
        """
        Initialize a successful result.
        
        Args:
            value: The value of the result
        """
        self.value = value
    
    def is_success(self) -> bool:
        """
        Check if the result is a success.
        
        Returns:
            bool: Always True for Success
        """
        return True
    
    def __str__(self) -> str:
        """String representation of the success result."""
        return f"Success: {self.value}"


class Error(Result[T]):
    """An error result containing an error message."""
    
    def __init__(self, error: str):
        """
        Initialize an error result.
        
        Args:
            error: The error message
        """
        self.error = error
    
    def is_success(self) -> bool:
        """
        Check if the result is a success.
        
        Returns:
            bool: Always False for Error
        """
        return False
    
    def __str__(self) -> str:
        """String representation of the error result."""
        return f"Error: {self.error}"
