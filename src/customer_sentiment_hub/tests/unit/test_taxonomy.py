"""
Tests for the taxonomy module.

This module contains tests for the taxonomy definitions and utility functions
used in the Customer Sentiment Hub.
"""

import unittest
from customer_sentiment_hub.domain.taxonomy import (
    Sentiment, CategoryType, TAXONOMY,
    get_valid_categories, get_valid_subcategories,
    get_category_for_subcategory, is_valid_subcategory_for_category,
    generate_taxonomy_string
)


class TestTaxonomy(unittest.TestCase):
    """Test suite for the taxonomy module."""

    def test_sentiment_enum(self):
        """Test that Sentiment enum contains expected values."""
        self.assertEqual(Sentiment.POSITIVE.value, "Positive")
        self.assertEqual(Sentiment.NEGATIVE.value, "Negative")
        self.assertEqual(Sentiment.NEUTRAL.value, "Neutral")
        self.assertEqual(len(Sentiment), 3)

    def test_category_type_enum(self):
        """Test that CategoryType enum contains expected values."""
        self.assertEqual(CategoryType.PRODUCT_SERVICES.value, "Product & Services")
        self.assertEqual(CategoryType.BILLING_PAYMENTS.value, "Billing & Payments")
        self.assertEqual(CategoryType.COMMUNICATION.value, "Communication")
        self.assertEqual(CategoryType.AGENT_SPECIFIC.value, "Agent Specific")
        self.assertEqual(CategoryType.SALES_AFFILIATE.value, "Sales / Affiliate Related")
        self.assertEqual(CategoryType.MISCELLANEOUS.value, "Miscellaneous")
        self.assertEqual(len(CategoryType), 6)

    def test_taxonomy_structure(self):
        """Test the overall structure of the TAXONOMY dictionary."""
        # Test top level keys
        self.assertIn("Sentiments", TAXONOMY)
        self.assertIn("Categories", TAXONOMY)
        
        # Test sentiments
        self.assertEqual(TAXONOMY["Sentiments"], frozenset(s.value for s in Sentiment))
        
        # Test categories
        categories = TAXONOMY["Categories"]
        self.assertEqual(len(categories), len(CategoryType))
        
        # Each category should have entries for all sentiments
        for category in categories:
            self.assertIn(category, get_valid_categories())
            for sentiment in Sentiment:
                self.assertIn(sentiment.value, categories[category])
                self.assertIsInstance(categories[category][sentiment.value], frozenset)

    def test_taxonomy_consistency(self):
        """Test that the taxonomy is internally consistent."""
        for category, sentiment_subcats in TAXONOMY["Categories"].items():
            for sentiment, subcategories in sentiment_subcats.items():
                # Each subcategory should be unique within its category
                unique_subcats = set()
                for subcat in subcategories:
                    self.assertNotIn(subcat, unique_subcats, 
                        f"Duplicate subcategory '{subcat}' found in {category}")
                    unique_subcats.add(subcat)

    def test_get_valid_categories(self):
        """Test the get_valid_categories function."""
        categories = get_valid_categories()
        self.assertIsInstance(categories, frozenset)
        
        # Should contain all CategoryType values
        for category_type in CategoryType:
            self.assertIn(category_type.value, categories)
        
        # Double-check a few specific categories
        self.assertIn("Product & Services", categories)
        self.assertIn("Billing & Payments", categories)
        self.assertIn("Communication", categories)

    def test_get_valid_subcategories(self):
        """Test the get_valid_subcategories function."""
        subcategories_dict = get_valid_subcategories()
        self.assertIsInstance(subcategories_dict, dict)
        
        # Each category should have a non-empty set of subcategories
        for category in CategoryType:
            self.assertIn(category.value, subcategories_dict)
            self.assertIsInstance(subcategories_dict[category.value], frozenset)
            self.assertTrue(len(subcategories_dict[category.value]) > 0)
        
        # Check specific examples
        product_services = subcategories_dict[CategoryType.PRODUCT_SERVICES.value]
        self.assertIn("Progress Pace", product_services)
        self.assertIn("Unsettled Debt", product_services)
        
        communication = subcategories_dict[CategoryType.COMMUNICATION.value]
        self.assertIn("Communication Method", communication)
        self.assertIn("Delayed Responses", communication)

    def test_get_category_for_subcategory(self):
        """Test the get_category_for_subcategory function."""
        # Test valid subcategories
        self.assertEqual(
            get_category_for_subcategory("Progress Pace"),
            CategoryType.PRODUCT_SERVICES.value
        )
        self.assertEqual(
            get_category_for_subcategory("Fee Collection"),
            CategoryType.BILLING_PAYMENTS.value
        )
        self.assertEqual(
            get_category_for_subcategory("Communication Method"),
            CategoryType.COMMUNICATION.value
        )
        
        # Test invalid subcategory
        self.assertEqual(
            get_category_for_subcategory("NonExistentSubcategory"),
            CategoryType.MISCELLANEOUS.value
        )

    def test_is_valid_subcategory_for_category(self):
        """Test the is_valid_subcategory_for_category function."""
        # Test valid combinations
        self.assertTrue(is_valid_subcategory_for_category(
            CategoryType.PRODUCT_SERVICES.value, "Progress Pace"
        ))
        self.assertTrue(is_valid_subcategory_for_category(
            CategoryType.BILLING_PAYMENTS.value, "Fee Collection"
        ))
        
        # Test invalid combinations
        self.assertFalse(is_valid_subcategory_for_category(
            CategoryType.PRODUCT_SERVICES.value, "Fee Collection"
        ))
        self.assertFalse(is_valid_subcategory_for_category(
            CategoryType.BILLING_PAYMENTS.value, "Progress Pace"
        ))
        
        # Test with invalid category
        self.assertFalse(is_valid_subcategory_for_category(
            "NonExistentCategory", "Progress Pace"
        ))
        
        # Test with invalid subcategory
        self.assertFalse(is_valid_subcategory_for_category(
            CategoryType.PRODUCT_SERVICES.value, "NonExistentSubcategory"
        ))

    def test_generate_taxonomy_string(self):
        """Test the generate_taxonomy_string function."""
        taxonomy_string = generate_taxonomy_string()
        self.assertIsInstance(taxonomy_string, str)
        
        # Check that the string contains key elements
        self.assertIn("MAIN CATEGORIES:", taxonomy_string)
        self.assertIn("FOR EACH MAIN CATEGORY, USE ONLY THESE SUBCATEGORIES:", taxonomy_string)
        
        # Check that all categories are included
        for category in CategoryType:
            self.assertIn(category.value, taxonomy_string)
        
        # Check that all sentiments are included
        for sentiment in Sentiment:
            self.assertIn(f"{sentiment.value} sentiment subcategories:", taxonomy_string)
        
        # Check for some specific subcategories
        self.assertIn("Progress Pace", taxonomy_string)
        self.assertIn("Fee Collection", taxonomy_string)
        self.assertIn("Communication Method", taxonomy_string)


if __name__ == "__main__":
    unittest.main()