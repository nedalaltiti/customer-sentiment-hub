"""Base interface for LLM services."""

from abc import ABC, abstractmethod
from typing import Dict, List

from customer_sentiment_hub.utils.result import Result


class LLMService(ABC):
    """
    Abstract base class defining the interface for LLM services.
    
    This provides a common interface for different LLM implementations
    (Gemini, future models, etc.) to implement.
    """
    
    @abstractmethod
    async def analyze_reviews(self, review_texts: List[str]) -> Result[Dict]:
        """
        Analyze a batch of review texts.
        
        Args:
            review_texts: List of review texts to analyze
            
        Returns:
            Result containing analysis results or error
        """
        pass
    
    @abstractmethod
    async def test_connection(self) -> bool:
        """
        Test connection to the LLM service.
        
        Returns:
            bool: True if connection is successful, raises an exception otherwise
        """
        pass