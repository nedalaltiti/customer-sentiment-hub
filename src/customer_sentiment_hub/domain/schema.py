"""Data models for the Customer Sentiment Hub."""

from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

from customer_sentiment_hub.domain.taxonomy import (
    CategoryType, Sentiment, get_valid_categories, get_valid_subcategories
)


class Label(BaseModel):
    """Represents a single label with category, subcategory and sentiment."""
    
    category: str = Field(
        description="The main category of the issue (e.g., 'Product & Services')")
    subcategory: str = Field(
        description="The specific subcategory of the issue")
    sentiment: str = Field(
        description="The sentiment must be ONLY 'Positive', 'Negative', or 'Neutral'")
    confidence: Optional[float] = Field(
        default=None, description="Confidence score for this label")
    
    @field_validator("sentiment")
    def validate_sentiment(cls, v: str) -> str:
        """Validate that sentiment is one of the allowed values."""
        valid_sentiments = [s.value for s in Sentiment]
        if v not in valid_sentiments:
            # Try to normalize the sentiment
            v_lower = v.lower()
            for sentiment in valid_sentiments:
                if sentiment.lower() in v_lower:
                    return sentiment
            return Sentiment.NEUTRAL.value
        return v


class Review(BaseModel):
    """Represents a single review with its metadata and labels."""
    
    review_id: str = Field(description="A unique identifier for the review")
    text: str = Field(description="The full text of the review")
    labels: List[Label] = Field(description="The list of labels for this review")


class ReviewOutput(BaseModel):
    """Represents the output containing multiple reviews."""
    
    reviews: List[Review] = Field(description="List of processed reviews")


class AnalysisRequest(BaseModel):
    """Request model for analysis API."""
    
    reviews: List[str] = Field(description="List of review texts to analyze")
    batch_size: Optional[int] = Field(
        default=None, description="Batch size for processing")
    confidence_threshold: Optional[float] = Field(
        default=None, description="Confidence threshold for predictions")
    max_labels_per_review: Optional[int] = Field(
        default=None, description="Maximum number of labels per review")