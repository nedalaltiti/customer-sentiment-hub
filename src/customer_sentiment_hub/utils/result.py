"""
Result type for robust error handling without exceptions.

This module implements the Result pattern, which represents the outcome
of an operation that might fail. This allows for more explicit error
handling compared to exceptions.
"""

from __future__ import annotations
from typing import Any, Callable, Dict, Generic, List, Optional, TypeVar, Union, cast, overload

T = TypeVar('T')  # Success value type
E = TypeVar('E')  # Error value type
U = TypeVar('U')  # Mapped value type


class Result(Generic[T]):
    """
    A result type that represents either success or failure of an operation.
    
    The Result pattern provides a more explicit way to handle errors compared
    to exceptions, making error handling visible in function signatures and
    encouraging proper error handling throughout the codebase.
    """
    
    def is_success(self) -> bool:
        """
        Check if the result represents a successful operation.
        
        Returns:
            bool: True if success, False if error
        """
        raise NotImplementedError("Subclasses must implement is_success")
    
    def is_error(self) -> bool:
        """
        Check if the result represents a failed operation.
        
        Returns:
            bool: True if error, False if success
        """
        return not self.is_success()
    
    def unwrap(self) -> T:
        """
        Get the success value, raising an exception if the result is an error.
        
        Returns:
            T: The success value
            
        Raises:
            ValueError: If the result is an error
        """
        raise NotImplementedError("Subclasses must implement unwrap")
    
    def unwrap_or(self, default: T) -> T:
        """
        Get the success value or a default if the result is an error.
        
        Args:
            default: The default value to return if the result is an error
            
        Returns:
            T: The success value or the default
        """
        raise NotImplementedError("Subclasses must implement unwrap_or")
    
    def map(self, fn: Callable[[T], U]) -> Result[U]:
        """
        Apply a function to the success value, preserving the result type.
        
        Args:
            fn: Function to apply to the success value
            
        Returns:
            Result[U]: A new result with the function applied to the success value,
                      or the original error if the result is an error
        """
        raise NotImplementedError("Subclasses must implement map")
    
    @staticmethod
    def success(value: T) -> Result[T]:
        """
        Create a success result with the given value.
        
        Args:
            value: The success value
            
        Returns:
            Result[T]: A success result
        """
        return Success(value)
    
    @staticmethod
    def error(error: str) -> Result[T]:
        """
        Create an error result with the given error message.
        
        Args:
            error: The error message
            
        Returns:
            Result[T]: An error result
        """
        return Error(error)
    
    @staticmethod
    def from_exception(e: Exception, context: str = "") -> Result[T]:
        """
        Create an error result from an exception.
        
        Args:
            e: The exception
            context: Optional context information
            
        Returns:
            Result[T]: An error result with a formatted error message
        """
        if context:
            error_message = f"{context}: {str(e)}"
        else:
            error_message = str(e)
        return Error(error_message)
    
    @staticmethod
    def try_operation(operation: Callable[[], T], error_context: str = "") -> Result[T]:
        """
        Try to perform an operation that might raise an exception.
        
        Args:
            operation: The operation to perform
            error_context: Optional context for error messages
            
        Returns:
            Result[T]: A success result with the operation's return value,
                      or an error result if an exception is raised
        """
        try:
            return Success(operation())
        except Exception as e:
            return Result.from_exception(e, error_context)


class Success(Result[T]):
    """
    A successful result containing a value.
    
    This represents an operation that completed successfully.
    """
    
    def __init__(self, value: T):
        """
        Initialize a successful result.
        
        Args:
            value: The success value
        """
        self.value = value
    
    def is_success(self) -> bool:
        """
        Check if the result represents a successful operation.
        
        Returns:
            bool: Always True for Success
        """
        return True
    
    def unwrap(self) -> T:
        """
        Get the success value.
        
        Returns:
            T: The success value
        """
        return self.value
    
    def unwrap_or(self, default: T) -> T:
        """
        Get the success value or a default if the result is an error.
        
        Args:
            default: The default value (unused for Success)
            
        Returns:
            T: The success value
        """
        return self.value
    
    def map(self, fn: Callable[[T], U]) -> Result[U]:
        """
        Apply a function to the success value.
        
        Args:
            fn: Function to apply to the success value
            
        Returns:
            Result[U]: A new success result with the function applied
        """
        return Success(fn(self.value))
    
    def __str__(self) -> str:
        """String representation of the success result."""
        return f"Success: {self.value}"
    
    def __repr__(self) -> str:
        """Detailed string representation of the success result."""
        return f"Success({repr(self.value)})"


class Error(Result[T]):
    """
    An error result containing an error message.
    
    This represents an operation that failed.
    """
    
    def __init__(self, error: str):
        """
        Initialize an error result.
        
        Args:
            error: The error message
        """
        self.error = error
    
    def is_success(self) -> bool:
        """
        Check if the result represents a successful operation.
        
        Returns:
            bool: Always False for Error
        """
        return False
    
    def unwrap(self) -> T:
        """
        Get the success value, raising an exception since this is an error.
        
        Raises:
            ValueError: Always raised for Error
        """
        raise ValueError(f"Cannot unwrap Error result: {self.error}")
    
    def unwrap_or(self, default: T) -> T:
        """
        Get the success value or a default if the result is an error.
        
        Args:
            default: The default value to return
            
        Returns:
            T: The default value
        """
        return default
    
    def map(self, fn: Callable[[T], U]) -> Result[U]:
        """
        Apply a function to the success value (no-op for Error).
        
        Args:
            fn: Function to apply (unused for Error)
            
        Returns:
            Result[U]: A new error result with the same error message
        """
        return Error(self.error)
    
    def __str__(self) -> str:
        """String representation of the error result."""
        return f"Error: {self.error}"
    
    def __repr__(self) -> str:
        """Detailed string representation of the error result."""
        return f"Error({repr(self.error)})"


def collect_results(results: List[Result[T]]) -> Result[List[T]]:
    """
    Collect multiple results into a single result.
    
    If all results are successful, returns a success result with a list of values.
    If any result is an error, returns the first error encountered.
    
    Args:
        results: List of results to collect
        
    Returns:
        Result[List[T]]: Success with list of values or the first error
    """
    values = []
    
    for result in results:
        if result.is_error():
            return cast(Error[List[T]], result)
        values.append(result.unwrap())
    
    return Success(values)