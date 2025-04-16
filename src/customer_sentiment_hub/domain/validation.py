"""
Validation logic for customer review analysis.

This module provides services for validating and correcting review labels
to ensure they conform to the defined taxonomy structure.
"""

from typing import Dict, List
from functools import lru_cache

from customer_sentiment_hub.domain.taxonomy import (
    Sentiment, CategoryType, TAXONOMY,
    get_valid_categories, get_valid_subcategories,
    get_category_for_subcategory, is_valid_subcategory_for_category
)


class ValidationService:
    """
    Service for validating and fixing review labels.
    
    This service ensures that all labels conform to the defined taxonomy,
    applying corrections when possible rather than rejecting invalid data.
    """
    
    def __init__(self):
        """Initialize the validation service with taxonomy references."""
        # Cache these values to avoid repeated lookups
        self.valid_categories = get_valid_categories()
        self.valid_subcategories = get_valid_subcategories()
        self.valid_sentiments = frozenset(s.value for s in Sentiment)
    
    @lru_cache(maxsize=100)
    def clean_sentiment(self, sentiment: str) -> str:
        """
        Clean and standardize sentiment values.
        
        Args:
            sentiment: The raw sentiment value
            
        Returns:
            str: Standardized sentiment value (Positive, Negative, or Neutral)
            
        Performance:
            O(1) - Uses cached results for repeated inputs
        """
        if not sentiment:
            return Sentiment.NEUTRAL.value
            
        # Normalize casing for more reliable matching
        sentiment_lower = sentiment.lower()
        
        # Direct mapping for common variations - O(1) lookup
        sentiment_map = {
            "positive": Sentiment.POSITIVE.value,
            "pos": Sentiment.POSITIVE.value,
            "good": Sentiment.POSITIVE.value,
            "favorable": Sentiment.POSITIVE.value,
            
            "negative": Sentiment.NEGATIVE.value,
            "neg": Sentiment.NEGATIVE.value,
            "bad": Sentiment.NEGATIVE.value,
            "unfavorable": Sentiment.NEGATIVE.value,
            
            "neutral": Sentiment.NEUTRAL.value,
            "neither": Sentiment.NEUTRAL.value,
            "mixed": Sentiment.NEUTRAL.value,
            "balanced": Sentiment.NEUTRAL.value,
        }
        
        # Try exact match in normalized map
        if sentiment_lower in sentiment_map:
            return sentiment_map[sentiment_lower]
        
        # Use substring matching as fallback
        if "positive" in sentiment_lower:
            return Sentiment.POSITIVE.value
        elif "negative" in sentiment_lower:
            return Sentiment.NEGATIVE.value
        elif "neutral" in sentiment_lower:
            return Sentiment.NEUTRAL.value
        
        # Default case
        return Sentiment.NEUTRAL.value
    
    def validate_and_fix_label(self, label: Dict[str, str]) -> Dict[str, str]:
        """
        Validate and fix a label to ensure it conforms to the taxonomy.
        
        This method applies a series of validation and correction rules:
        1. Ensures sentiment is standardized
        2. Fixes cases where category and subcategory are swapped
        3. Handles missing fields with reasonable defaults
        4. Corrects invalid category/subcategory combinations
        
        Args:
            label: A label dictionary with category, subcategory, and sentiment
            
        Returns:
            Dict[str, str]: A corrected label dictionary that conforms to the taxonomy
        """
        # Create a copy to avoid modifying the original
        fixed_label = label.copy()
        
        # Step 1: Clean sentiment - always needed
        if "sentiment" in fixed_label:
            fixed_label["sentiment"] = self.clean_sentiment(fixed_label["sentiment"])
        else:
            fixed_label["sentiment"] = Sentiment.NEUTRAL.value
        
        # Step 2: Handle category-related issues
        if "category" not in fixed_label:
            # No category provided
            if "subcategory" in fixed_label:
                # Try to infer category from subcategory
                category = get_category_for_subcategory(fixed_label["subcategory"])
                fixed_label["category"] = category
            else:
                # No category or subcategory - use default
                fixed_label["category"] = CategoryType.MISCELLANEOUS.value
                fixed_label["subcategory"] = "Other"
                return fixed_label
        
        # Step 3: Check if category is valid
        if fixed_label["category"] not in self.valid_categories:
            # Category might be a sentiment or subcategory
            
            # Check if it's a sentiment
            if fixed_label["category"] in self.valid_sentiments:
                # Move to sentiment if needed and use default category
                fixed_label["sentiment"] = fixed_label["category"]
                
                # Try to use subcategory's parent category
                if "subcategory" in fixed_label:
                    parent = get_category_for_subcategory(fixed_label["subcategory"])
                    fixed_label["category"] = parent
                else:
                    fixed_label["category"] = CategoryType.MISCELLANEOUS.value
                    fixed_label["subcategory"] = "Other"
                
            # Check if it's a subcategory
            else:
                subcategory = fixed_label["category"]
                parent = get_category_for_subcategory(subcategory)
                
                # If we found a parent, use it
                if parent != CategoryType.MISCELLANEOUS.value or subcategory == "Other":
                    fixed_label["subcategory"] = subcategory
                    fixed_label["category"] = parent
                else:
                    # Couldn't find a match - use default
                    fixed_label["category"] = CategoryType.MISCELLANEOUS.value
                    fixed_label["subcategory"] = "Other"
        
        # Step 4: Handle subcategory issues
        if "subcategory" not in fixed_label:
            # Missing subcategory - use default based on sentiment
            sentiment = fixed_label["sentiment"]
            category = fixed_label["category"]
            
            # Get subcategories for this category and sentiment
            subcats = TAXONOMY["Categories"].get(category, {}).get(sentiment, frozenset())
            
            if subcats:
                # Use the first available subcategory
                fixed_label["subcategory"] = next(iter(subcats))
            else:
                # No matching subcategories - use "Other" if available
                all_subcats = self.valid_subcategories.get(category, frozenset())
                if "Other" in all_subcats:
                    fixed_label["subcategory"] = "Other"
                elif all_subcats:
                    # Use any available subcategory
                    fixed_label["subcategory"] = next(iter(all_subcats))
                else:
                    # Fall back to miscellaneous
                    fixed_label["category"] = CategoryType.MISCELLANEOUS.value
                    fixed_label["subcategory"] = "Other"
        
        # Step 5: Check subcategory validity for the category
        elif not is_valid_subcategory_for_category(fixed_label["category"], fixed_label["subcategory"]):
            # Invalid subcategory for this category
            category = fixed_label["category"]
            sentiment = fixed_label["sentiment"]
            
            # Try to find a valid subcategory for this category and sentiment
            subcats = TAXONOMY["Categories"].get(category, {}).get(sentiment, frozenset())
            
            if subcats:
                fixed_label["subcategory"] = next(iter(subcats))
            else:
                # Try "Other" or any valid subcategory
                all_subcats = self.valid_subcategories.get(category, frozenset())
                if "Other" in all_subcats:
                    fixed_label["subcategory"] = "Other"
                elif all_subcats:
                    fixed_label["subcategory"] = next(iter(all_subcats))
                else:
                    # Fall back to miscellaneous
                    fixed_label["category"] = CategoryType.MISCELLANEOUS.value
                    fixed_label["subcategory"] = "Other"
        
        return fixed_label
    
    def validate_review_labels(self, labels: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        Validate and fix a list of labels for a review.
        
        Args:
            labels: A list of label dictionaries
            
        Returns:
            List[Dict[str, str]]: A list of validated and fixed labels
        """
        if not labels:
            return []
        
        return [self.validate_and_fix_label(label) for label in labels]