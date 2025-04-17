"""
Tests for the validation service.

This module contains tests for the validation and correction of review labels
in the Customer Sentiment Hub.
"""

import unittest
from customer_sentiment_hub.domain.taxonomy import Sentiment, CategoryType
from customer_sentiment_hub.domain.validation import ValidationService


class TestValidationService(unittest.TestCase):
    """Test suite for the ValidationService."""

    def setUp(self):
        """Set up a fresh ValidationService for each test."""
        self.service = ValidationService()

    def test_clean_sentiment(self):
        """Test cleaning and standardizing sentiment values."""
        # Valid sentiments should remain unchanged
        self.assertEqual(self.service.clean_sentiment("Positive"), "Positive")
        self.assertEqual(self.service.clean_sentiment("Negative"), "Negative")
        self.assertEqual(self.service.clean_sentiment("Neutral"), "Neutral")
        
        # Lowercase variants should be normalized
        self.assertEqual(self.service.clean_sentiment("positive"), "Positive")
        self.assertEqual(self.service.clean_sentiment("negative"), "Negative")
        self.assertEqual(self.service.clean_sentiment("neutral"), "Neutral")
        
        # Abbreviated forms should be recognized
        self.assertEqual(self.service.clean_sentiment("pos"), "Positive")
        self.assertEqual(self.service.clean_sentiment("neg"), "Negative")
        
        # Synonyms should be mapped correctly
        self.assertEqual(self.service.clean_sentiment("good"), "Positive")
        self.assertEqual(self.service.clean_sentiment("bad"), "Negative")
        self.assertEqual(self.service.clean_sentiment("mixed"), "Neutral")
        
        # Containing valid sentiment should normalize
        self.assertEqual(self.service.clean_sentiment("very positive"), "Positive")
        self.assertEqual(self.service.clean_sentiment("somewhat negative"), "Negative")
        
        # Empty or None should default to neutral
        self.assertEqual(self.service.clean_sentiment(""), "Neutral")
        self.assertEqual(self.service.clean_sentiment(None), "Neutral")
        
        # Invalid sentiment should default to neutral
        self.assertEqual(self.service.clean_sentiment("unknown"), "Neutral")
        self.assertEqual(self.service.clean_sentiment("xyz123"), "Neutral")

    def test_validate_and_fix_label_valid_inputs(self):
        """Test validation of already valid labels."""
        # Valid label should remain unchanged
        valid_label = {
            "category": "Product & Services",
            "subcategory": "Progress Pace",
            "sentiment": "Negative"
        }
        fixed_label = self.service.validate_and_fix_label(valid_label)
        self.assertEqual(fixed_label, valid_label)
        
        # Valid label with different sentiment capitalization
        label_with_lowercase = {
            "category": "Product & Services",
            "subcategory": "Progress Pace",
            "sentiment": "negative"
        }
        fixed_label = self.service.validate_and_fix_label(label_with_lowercase)
        self.assertEqual(fixed_label["category"], "Product & Services")
        self.assertEqual(fixed_label["subcategory"], "Progress Pace")
        self.assertEqual(fixed_label["sentiment"], "Negative")

    def test_validate_and_fix_label_missing_fields(self):
        """Test validation of labels with missing fields."""
        # Missing sentiment
        no_sentiment = {
            "category": "Product & Services",
            "subcategory": "Progress Pace"
        }
        fixed_label = self.service.validate_and_fix_label(no_sentiment)
        self.assertEqual(fixed_label["category"], "Product & Services")
        self.assertEqual(fixed_label["subcategory"], "Progress Pace")
        self.assertEqual(fixed_label["sentiment"], "Neutral")
        
        # Missing category but valid subcategory
        no_category = {
            "subcategory": "Progress Pace",
            "sentiment": "Negative"
        }
        fixed_label = self.service.validate_and_fix_label(no_category)
        self.assertEqual(fixed_label["category"], "Product & Services")
        self.assertEqual(fixed_label["subcategory"], "Progress Pace")
        self.assertEqual(fixed_label["sentiment"], "Negative")
        
        # Missing subcategory
        no_subcategory = {
            "category": "Product & Services",
            "sentiment": "Negative"
        }
        fixed_label = self.service.validate_and_fix_label(no_subcategory)
        self.assertEqual(fixed_label["category"], "Product & Services")
        # Should assign a valid subcategory for Product & Services with Negative sentiment
        self.assertIn(fixed_label["subcategory"], 
                     ["Unsettled Debt", "Progress Pace", "Procedure", "Settlement Percentage",
                      "Creditor Correspondence", "Debt Priority", "Settlement Failure",
                      "Summons", "Legal Procedure", "Legal Plan Representation",
                      "Lending", "Unmet Expectations (Services)", "Delayed Cancellation Requests"])
        self.assertEqual(fixed_label["sentiment"], "Negative")
        
        # Almost empty label with just sentiment
        only_sentiment = {
            "sentiment": "Positive"
        }
        fixed_label = self.service.validate_and_fix_label(only_sentiment)
        self.assertEqual(fixed_label["sentiment"], "Positive")
        self.assertIn(fixed_label["category"], self.service.valid_categories)
        
        # Completely empty label
        empty_label = {}
        fixed_label = self.service.validate_and_fix_label(empty_label)
        self.assertEqual(fixed_label["sentiment"], "Neutral")
        self.assertEqual(fixed_label["category"], "Miscellaneous")
        self.assertEqual(fixed_label["subcategory"], "Other")

    def test_validate_and_fix_label_invalid_combinations(self):
        """Test validation of labels with invalid category-subcategory combinations."""
        # Subcategory from wrong category
        wrong_subcategory = {
            "category": "Product & Services",
            "subcategory": "Fee Collection",  # From Billing & Payments
            "sentiment": "Negative"
        }
        fixed_label = self.service.validate_and_fix_label(wrong_subcategory)
        self.assertEqual(fixed_label["category"], "Product & Services")
        self.assertNotEqual(fixed_label["subcategory"], "Fee Collection")
        self.assertIn(fixed_label["subcategory"], 
                     ["Unsettled Debt", "Progress Pace", "Procedure", "Settlement Percentage",
                      "Creditor Correspondence", "Debt Priority", "Settlement Failure",
                      "Summons", "Legal Procedure", "Legal Plan Representation",
                      "Lending", "Unmet Expectations (Services)", "Delayed Cancellation Requests"])
        
        # Invalid category
        invalid_category = {
            "category": "Invalid Category",
            "subcategory": "Progress Pace",
            "sentiment": "Negative"
        }
        fixed_label = self.service.validate_and_fix_label(invalid_category)
        self.assertEqual(fixed_label["subcategory"], "Progress Pace")
        self.assertEqual(fixed_label["category"], "Product & Services")
        
        # Invalid subcategory
        invalid_subcategory = {
            "category": "Product & Services",
            "subcategory": "Invalid Subcategory",
            "sentiment": "Negative"
        }
        fixed_label = self.service.validate_and_fix_label(invalid_subcategory)
        self.assertEqual(fixed_label["category"], "Product & Services")
        self.assertNotEqual(fixed_label["subcategory"], "Invalid Subcategory")
        
        # Both invalid category and subcategory
        all_invalid = {
            "category": "Invalid Category",
            "subcategory": "Invalid Subcategory",
            "sentiment": "Negative"
        }
        fixed_label = self.service.validate_and_fix_label(all_invalid)
        self.assertIn(fixed_label["category"], self.service.valid_categories)
        self.assertIn(fixed_label["subcategory"], 
                     self.service.valid_subcategories.get(fixed_label["category"], frozenset()))

    def test_validate_and_fix_label_swapped_fields(self):
        """Test validation of labels with swapped category and subcategory."""
        # Category in subcategory field and vice versa
        swapped = {
            "category": "Progress Pace",  # This is a subcategory
            "subcategory": "Product & Services",  # This is a category
            "sentiment": "Negative"
        }
        fixed_label = self.service.validate_and_fix_label(swapped)
        # Should detect and correct the swap
        self.assertEqual(fixed_label["category"], "Product & Services")
        self.assertEqual(fixed_label["subcategory"], "Progress Pace")
        
        # Sentiment in category field
        sentiment_as_category = {
            "category": "Positive",  # This is a sentiment
            "subcategory": "Progress Pace",
            "sentiment": "Negative"  # Original sentiment is preserved
        }
        fixed_label = self.service.validate_and_fix_label(sentiment_as_category)
        self.assertEqual(fixed_label["category"], "Product & Services")
        self.assertEqual(fixed_label["subcategory"], "Progress Pace")
        self.assertEqual(fixed_label["sentiment"], "Negative")  # Original sentiment is kept

    def test_validate_review_labels(self):
        """Test validation of a list of labels for a review."""
        labels = [
            {
                "category": "Product & Services",
                "subcategory": "Progress Pace",
                "sentiment": "negative"
            },
            {
                "category": "Invalid Category",
                "subcategory": "Communication Method",
                "sentiment": "Positive"
            },
            {}  # Empty label
        ]
        
        fixed_labels = self.service.validate_review_labels(labels)
        
        # Should have same length
        self.assertEqual(len(fixed_labels), 3)
        
        # First label should be normalized
        self.assertEqual(fixed_labels[0]["category"], "Product & Services")
        self.assertEqual(fixed_labels[0]["subcategory"], "Progress Pace")
        self.assertEqual(fixed_labels[0]["sentiment"], "Negative")
        
        # Second label should have category fixed
        self.assertEqual(fixed_labels[1]["subcategory"], "Communication Method")
        self.assertEqual(fixed_labels[1]["category"], "Communication")
        self.assertEqual(fixed_labels[1]["sentiment"], "Positive")
        
        # Third label should be populated with defaults
        self.assertEqual(fixed_labels[2]["category"], "Miscellaneous")
        self.assertEqual(fixed_labels[2]["subcategory"], "Other")
        self.assertEqual(fixed_labels[2]["sentiment"], "Neutral")
        
        # Empty list should return empty list
        self.assertEqual(self.service.validate_review_labels([]), [])


if __name__ == "__main__":
    unittest.main()