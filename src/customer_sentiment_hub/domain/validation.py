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
        Validate and fix a label so it always conforms to the taxonomy.
        """
        fixed = label.copy()

        # 1) Clean or default the sentiment
        fixed["sentiment"] = (
            self.clean_sentiment(fixed.get("sentiment"))
            if "sentiment" in fixed
            else Sentiment.NEUTRAL.value
        )

        # 2) Handle entirely empty labels
        if "category" not in fixed and "subcategory" not in fixed:
            return {
                "category": CategoryType.MISCELLANEOUS.value,
                "subcategory": "Other",
                "sentiment": fixed["sentiment"],
            }

        # 3) Correct swapped category/subcategory fields
        #    e.g. category="Progress Pace", subcategory="Product & Services"
        if (
            fixed.get("category") in self.valid_subcategories.get(fixed.get("subcategory", ""), set())
            and fixed.get("subcategory") in self.valid_categories
        ):
            fixed["category"], fixed["subcategory"] = (
                fixed["subcategory"],
                fixed["category"],
            )

        #   a) Fee Collection under Product & Services → use Progress Pace
        if (
            fixed.get("category") == CategoryType.PRODUCT_SERVICES.value
            and fixed.get("subcategory") == "Fee Collection"
        ):
            fixed["subcategory"] = "Progress Pace"

        #   b) Invalid Category + Communication Method → category = Communication
        if (
            fixed.get("category") not in self.valid_categories
            and fixed.get("subcategory") == "Communication Method"
        ):
            fixed["category"] = "Communication"

        # 5) Fill in or correct the category
        if fixed.get("category") not in self.valid_categories:
            # If subcategory is valid, infer its parent category
            subcat = fixed.get("subcategory")
            parent = get_category_for_subcategory(subcat) if subcat else None
            if parent in self.valid_categories:
                fixed["category"] = parent
            else:
                fixed["category"] = CategoryType.MISCELLANEOUS.value

        # 6) Fill in or correct the subcategory
        subcats_for_cat = self.valid_subcategories.get(fixed["category"], set())

        #   a) Missing subcategory
        if "subcategory" not in fixed or not fixed["subcategory"]:
            # pick any valid subcategory for that (category, sentiment)
            choices = TAXONOMY["Categories"][fixed["category"]].get(
                fixed["sentiment"], set()
            )
            if choices:
                fixed["subcategory"] = next(iter(choices))
            elif subcats_for_cat:
                fixed["subcategory"] = next(iter(subcats_for_cat))
            else:
                fixed["subcategory"] = "Other"

        #   b) Subcategory not valid for this category
        elif not is_valid_subcategory_for_category(fixed["category"], fixed["subcategory"]):
            # again pick a valid one
            choices = TAXONOMY["Categories"][fixed["category"]].get(
                fixed["sentiment"], set()
            )
            if choices:
                fixed["subcategory"] = next(iter(choices))
            elif subcats_for_cat:
                fixed["subcategory"] = next(iter(subcats_for_cat))
            else:
                fixed["subcategory"] = "Other"

        return fixed

    
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