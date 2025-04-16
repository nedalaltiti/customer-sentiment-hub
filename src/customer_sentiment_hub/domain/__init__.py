"""
Domain models and business logic for Customer Sentiment Hub.

This package contains the core domain entities, validation rules,
and taxonomy definitions that represent the business domain,
independent of the API or infrastructure layers.
"""

from customer_sentiment_hub.domain.schema import Label, Review, ReviewOutput, AnalysisRequest
from customer_sentiment_hub.domain.taxonomy import Sentiment, CategoryType, generate_taxonomy_string
from customer_sentiment_hub.domain.validation import ValidationService

__all__ = [
    # Core models
    'Label', 'Review', 'ReviewOutput', 'AnalysisRequest',
    
    # Domain enumerations
    'Sentiment', 'CategoryType',
    
    # Services
    'ValidationService',
    
    # Helper functions
    'generate_taxonomy_string'
]