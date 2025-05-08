"""
Adapter functions for converting between API and domain models.

This module provides explicit conversion between the API representation
of reviews (which use 'review_text') and domain models (which use 'text'),
ensuring consistency across the application boundaries.
"""

from typing import Dict, List, Any
from customer_sentiment_hub.domain.schema import Review, Label  # Import domain models

def domain_to_api_review(domain_review: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert a domain review to an API review representation.
    
    Args:
        domain_review: A review using domain model field names
        
    Returns:
        Dict with API field names ('review_text' instead of 'text')
    """
    return {
        "review_id": domain_review.get("review_id", ""),
        "review_text": domain_review.get("text", ""),
        "labels": domain_review.get("labels", [])
    }

def api_to_domain_review(api_review: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert an API review to a domain review representation.
    
    Args:
        api_review: A review using API field names
        
    Returns:
        Dict with domain model field names ('text' instead of 'review_text')
    """
    return {
        "review_id": api_review.get("review_id", ""),
        "text": api_review.get("review_text", ""),
        "labels": api_review.get("labels", [])
    }

# Helper functions for collections
def domain_to_api_reviews(domain_reviews: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Convert a list of domain reviews to API reviews."""
    return [domain_to_api_review(review) for review in domain_reviews]

def api_to_domain_reviews(api_reviews: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Convert a list of API reviews to domain reviews."""
    return [api_to_domain_review(review) for review in api_reviews]