"""Validation logic for customer review analysis."""

import re
from typing import Dict, List, Set

from customer_sentiment_hub.domain.taxonomy import (
    Sentiment, get_valid_categories, get_valid_subcategories
)


class ValidationService:
    """Service for validating and fixing review labels."""
    
    def __init__(self):
        """Initialize the validation service."""
        self.valid_categories = get_valid_categories()
        self.valid_subcategories = get_valid_subcategories()
    
    def clean_sentiment(self, sentiment: str) -> str:
        """
        Clean and standardize sentiment values.
        
        Args:
            sentiment: The raw sentiment value
            
        Returns:
            str: Standardized sentiment value
        """
        # Remove emojis and non-alphanumeric characters
        cleaned = re.sub(r'[^\w\s]', '', sentiment).strip()
        
        # Extract just "Positive", "Negative", or "Neutral"
        if "positive" in cleaned.lower():
            return Sentiment.POSITIVE.value
        elif "negative" in cleaned.lower():
            return Sentiment.NEGATIVE.value
        elif "neutral" in cleaned.lower():
            return Sentiment.NEUTRAL.value
        else:
            # Default to "Neutral" if no match
            return Sentiment.NEUTRAL.value
    
    def validate_and_fix_label(self, label: Dict[str, str]) -> Dict[str, str]:
        """
        Validate and fix a label to ensure it conforms to the taxonomy.
        
        Args:
            label: A label dictionary with category, subcategory, and sentiment
            
        Returns:
            Dict[str, str]: A fixed label dictionary
        """
        # Clean sentiment
        if "sentiment" in label:
            label["sentiment"] = self.clean_sentiment(label["sentiment"])
        else:
            label["sentiment"] = Sentiment.NEUTRAL.value
        
        # Check if category is actually a sentiment
        if "category" in label and label["category"] in [s.value for s in Sentiment]:
            # Fix: category is actually a sentiment
            if "subcategory" in label:
                # Try to find a valid category for this subcategory
                for category, subcats in self.valid_subcategories.items():
                    if label["subcategory"] in subcats:
                        # Found a valid category
                        label["category"] = category
                        return label
                
                # Use default
                label["category"] = "Miscellaneous"
            else:
                # Default fallback
                label["category"] = "Miscellaneous"
                label["subcategory"] = "Other"
        
        # Fix invalid categories
        elif "category" in label and label["category"] not in self.valid_categories:
            # Try to find this as a subcategory
            found = False
            for category, subcats in self.valid_subcategories.items():
                if label["category"] in subcats:
                    # This "category" is actually a subcategory
                    if "subcategory" in label:
                        # Move current subcategory to category
                        label["subcategory"] = label["category"]
                    else:
                        label["subcategory"] = label["category"]
                    label["category"] = category
                    found = True
                    break
            
            if not found:
                # Use default
                label["category"] = "Miscellaneous"
                if "subcategory" not in label:
                    label["subcategory"] = "Other"
        
        # Fix invalid subcategories
        if ("category" in label and "subcategory" in label and 
            label["category"] in self.valid_categories and 
            label["subcategory"] not in self.valid_subcategories[label["category"]]):
            
            # Default to "Other" if available for this category
            if "Other" in self.valid_subcategories[label["category"]]:
                label["subcategory"] = "Other"
            else:
                # Find a suitable subcategory based on sentiment
                sentiment = label["sentiment"]
                from customer_sentiment_hub.domain.taxonomy import TAXONOMY
                
                valid_subcats = TAXONOMY["Categories"][label["category"]][sentiment]
                if valid_subcats:
                    label["subcategory"] = valid_subcats[0]
                else:
                    # Ultimate fallback
                    label["category"] = "Miscellaneous"
                    label["subcategory"] = "Other"
        
        return label