"""
Tests for the domain model schemas.

This module contains tests for the data models and their validation methods
used in the Customer Sentiment Hub.
"""

import unittest
from customer_sentiment_hub.domain.schema import (
    Label, Review, ReviewOutput, AnalysisRequest
)


class TestLabel(unittest.TestCase):
    """Test suite for the Label model."""

    def test_create_valid_label(self):
        """Test creating a valid Label instance."""
        label = Label(
            category="Product & Services",
            subcategory="Progress Pace",
            sentiment="Negative"
        )
        self.assertEqual(label.category, "Product & Services")
        self.assertEqual(label.subcategory, "Progress Pace")
        self.assertEqual(label.sentiment, "Negative")

    def test_validate_sentiment(self):
        """Test the sentiment validation/normalization."""
        # Valid sentiments should remain unchanged
        for sentiment in ["Positive", "Negative", "Neutral"]:
            label = Label(
                category="Product & Services",
                subcategory="Progress Pace",
                sentiment=sentiment
            )
            self.assertEqual(label.sentiment, sentiment)
        
        # Lowercase variants should be normalized
        label = Label(
            category="Product & Services",
            subcategory="Progress Pace",
            sentiment="positive"
        )
        self.assertEqual(label.sentiment, "Positive")
        
        # Containing valid sentiment should normalize
        label = Label(
            category="Product & Services",
            subcategory="Progress Pace",
            sentiment="This is positive feedback"
        )
        self.assertEqual(label.sentiment, "Positive")
        
        # Invalid sentiment should default to neutral
        label = Label(
            category="Product & Services",
            subcategory="Progress Pace",
            sentiment="Unknown"
        )
        self.assertEqual(label.sentiment, "Neutral")

    def test_category_subcategory_validation(self):
        """Test the category-subcategory validation."""
        # The model should allow invalid combinations for later correction
        label = Label(
            category="Product & Services",
            subcategory="Fee Collection",  
            sentiment="Negative"
        )
        # Model should be created without raising an exception
        self.assertEqual(label.category, "Product & Services")
        self.assertEqual(label.subcategory, "Fee Collection")


class TestReview(unittest.TestCase):
    """Test suite for the Review model."""

    def test_create_valid_review(self):
        """Test creating a valid Review instance."""
        review = Review(
            review_id="1001",
            text="The debt settlement process was taking too long.",
            labels=[
                Label(
                    category="Product & Services",
                    subcategory="Progress Pace",
                    sentiment="Negative"
                )
            ]
        )
        self.assertEqual(review.review_id, "1001")
        self.assertEqual(review.text, "The debt settlement process was taking too long.")
        self.assertEqual(len(review.labels), 1)
        self.assertEqual(review.labels[0].category, "Product & Services")

    def test_review_with_multiple_labels(self):
        """Test creating a Review with multiple labels."""
        review = Review(
            review_id="1002",
            text="The debt settlement was slow, but customer service was great.",
            labels=[
                Label(
                    category="Product & Services",
                    subcategory="Progress Pace",
                    sentiment="Negative"
                ),
                Label(
                    category="Communication",
                    subcategory="Communication Method",
                    sentiment="Positive"
                )
            ]
        )
        self.assertEqual(len(review.labels), 2)
        self.assertEqual(review.labels[0].sentiment, "Negative")
        self.assertEqual(review.labels[1].sentiment, "Positive")


class TestReviewOutput(unittest.TestCase):
    """Test suite for the ReviewOutput model."""

    def test_create_valid_review_output(self):
        """Test creating a valid ReviewOutput instance."""
        review_output = ReviewOutput(
            reviews=[
                Review(
                    review_id="1001",
                    text="The debt settlement process was taking too long.",
                    labels=[
                        Label(
                            category="Product & Services",
                            subcategory="Progress Pace",
                            sentiment="Negative"
                        )
                    ]
                )
            ]
        )
        self.assertEqual(len(review_output.reviews), 1)
        self.assertEqual(review_output.reviews[0].review_id, "1001")

    def test_review_output_with_multiple_reviews(self):
        """Test creating a ReviewOutput with multiple reviews."""
        review_output = ReviewOutput(
            reviews=[
                Review(
                    review_id="1001",
                    text="The debt settlement process was taking too long.",
                    labels=[
                        Label(
                            category="Product & Services",
                            subcategory="Progress Pace",
                            sentiment="Negative"
                        )
                    ]
                ),
                Review(
                    review_id="1002",
                    text="Customer service was very helpful.",
                    labels=[
                        Label(
                            category="Communication",
                            subcategory="Communication Method",
                            sentiment="Positive"
                        )
                    ]
                )
            ]
        )
        self.assertEqual(len(review_output.reviews), 2)
        self.assertEqual(review_output.reviews[0].review_id, "1001")
        self.assertEqual(review_output.reviews[1].review_id, "1002")


class TestAnalysisRequest(unittest.TestCase):
    """Test suite for the AnalysisRequest model."""

    def test_create_valid_analysis_request(self):
        """Test creating a valid AnalysisRequest instance."""
        request = AnalysisRequest(
            reviews=[
                "The debt settlement process was taking too long.",
                "Customer service was very helpful."
            ],
            batch_size=5,
            confidence_threshold=0.3,
            max_labels_per_review=5
        )
        self.assertEqual(len(request.reviews), 2)
        self.assertEqual(request.batch_size, 5)
        self.assertEqual(request.confidence_threshold, 0.3)
        self.assertEqual(request.max_labels_per_review, 5)

    def test_analysis_request_validation(self):
        """Test the analysis request parameter validation."""
        # Test batch_size larger than reviews
        request = AnalysisRequest(
            reviews=["Single review"],
            batch_size=5
        )
        # Should be adjusted to match the number of reviews
        self.assertEqual(request.batch_size, 1)
        
        # Test max_labels_per_review too large
        request = AnalysisRequest(
            reviews=["Single review"],
            max_labels_per_review=20
        )
        # Should be capped at 10
        self.assertEqual(request.max_labels_per_review, 10)
        
        # Test with minimal parameters
        request = AnalysisRequest(
            reviews=["Single review"]
        )
        self.assertIsNone(request.batch_size)
        self.assertIsNone(request.confidence_threshold)
        self.assertIsNone(request.max_labels_per_review)


if __name__ == "__main__":
    unittest.main()