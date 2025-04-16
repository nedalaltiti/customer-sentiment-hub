"""Abstract LLM service interface."""

from abc import ABC, abstractmethod
from typing import Dict, List

from customer_sentiment_hub.utils.result import Result


class LLMService(ABC):
    """Abstract base class for LLM services."""
    
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