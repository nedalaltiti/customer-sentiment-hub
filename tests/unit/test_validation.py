"""Tests for the validation service."""

import pytest

from customer_sentiment_hub.domain.validation import ValidationService


@pytest.fixture
def validation_service():
    """Create a validation service for testing."""
    return ValidationService()


def test_clean_sentiment(validation_service):
    """Test cleaning sentiment values."""
    # Test positive sentiment variations
    assert validation_service.clean_sentiment("Positive") == "Positive"
    assert validation_service.clean_sentiment("positive") == "Positive"
    assert validation_service.clean_sentiment("👍 Positive") == "Positive"
    assert validation_service.clean_sentiment("Very positive") == "Positive"
    
    # Test negative sentiment variations
    assert validation_service.clean_sentiment("Negative") == "Negative"
    assert validation_service.clean_sentiment("negative") == "Negative"
    assert validation_service.clean_sentiment("👎 Negative") == "Negative"
    assert validation_service.clean_sentiment("Very negative") == "Negative"
    
    # Test neutral sentiment variations
    assert validation_service.clean_sentiment("Neutral") == "Neutral"
    assert validation_service.clean_sentiment("neutral") == "Neutral"
    assert validation_service.clean_sentiment("Somewhat neutral") == "Neutral"
    
    # Test default case
    assert validation_service.clean_sentiment("Unknown") == "Neutral"
    assert validation_service.clean_sentiment("") == "Neutral"


def test_validate_and_fix_label(validation_service):
    """Test validating and fixing labels."""
    # Test valid label
    valid_label = {
        "category": "Product & Services",
        "subcategory": "Procedure",
        "sentiment": "Positive"
    }
    assert validation_service.validate_and_fix_label(valid_label) == valid_label
    
    # Test label with sentiment as category
    sentiment_as_category = {
        "category": "Positive",
        "subcategory": "Procedure"
    }
    fixed = validation_service.validate_and_fix_label(sentiment_as_category)
    assert fixed["category"] == "Product & Services"
    assert fixed["subcategory"] == "Procedure"
    assert fixed["sentiment"] == "Positive"
    
    # Test label with invalid subcategory
    invalid_subcategory = {
        "category": "Product & Services",
        "subcategory": "Invalid Subcategory",
        "sentiment": "Negative"
    }
    fixed = validation_service.validate_and_fix_label(invalid_subcategory)
    assert fixed["category"] == "Product & Services"
    assert fixed["subcategory"] == "Other" or fixed["subcategory"] in validation_service.valid_subcategories["Product & Services"]
    assert fixed["sentiment"] == "Negative"
    
    # Test completely invalid label
    invalid_label = {
        "category": "Invalid Category",
        "subcategory": "Invalid Subcategory",
        "sentiment": "Invalid Sentiment"
    }
    fixed = validation_service.validate_and_fix_label(invalid_label)
    assert fixed["category"] == "Miscellaneous"
    assert fixed["subcategory"] == "Other"
    assert fixed["sentiment"] == "Neutral"