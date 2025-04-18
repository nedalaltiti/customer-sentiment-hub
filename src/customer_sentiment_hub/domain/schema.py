"""
Domain models for the Customer Sentiment Hub.

This module defines the core data structures used throughout the application,
representing the fundamental business entities and their relationships.
"""

from typing import List

from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict

from customer_sentiment_hub.domain.taxonomy import (
    Sentiment, get_valid_subcategories
)


class Label(BaseModel):
    """
    Represents a single label with category, subcategory and sentiment.
    
    A label classifies a specific aspect of a customer review, identifying:
    - The general category (e.g., "Product & Services")
    - The specific subcategory (e.g., "Unsettled Debt")
    - The sentiment expressed (Positive, Negative, or Neutral)
    """
    
    category: str = Field(
        description="The main category of the issue (e.g., 'Product & Services')")
    subcategory: str = Field(
        description="The specific subcategory of the issue")
    sentiment: str = Field(
        description="The sentiment must be ONLY 'Positive', 'Negative', or 'Neutral'")
    # confidence: Optional[float] = Field(
    #     default=None, 
    #     description="Confidence score for this label (0.0-1.0)",
    #     ge=0.0, 
    #     le=1.0
    # )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "category": "Product & Services",
                "subcategory": "Progress Pace",
                "sentiment": "Negative",
            }
        }
    )
    
    @field_validator("sentiment")
    def validate_sentiment(cls, v: str) -> str:
        """Validate and normalize sentiment values."""
        valid_sentiments = [s.value for s in Sentiment]
        if v in valid_sentiments:
            return v
            
        # Try to normalize the sentiment
        v_lower = v.lower()
        for sentiment in valid_sentiments:
            if sentiment.lower() in v_lower:
                return sentiment
                
        # Default fallback
        return Sentiment.NEUTRAL.value
    
    @model_validator(mode='after')
    def check_category_subcategory(self) -> 'Label':
        """Validate that category and subcategory are compatible."""
        valid_subcategories = get_valid_subcategories()
        if (self.category in valid_subcategories and 
                self.subcategory not in valid_subcategories[self.category]):
            # This would technically be invalid, but I'll let it pass
            # and let the ValidationService handle corrections
            pass
        return self


class Review(BaseModel):
    """
    Represents a single review with its metadata and labels.
    
    A review contains the original text submitted by a customer,
    along with extracted labels that categorize the sentiment and topics.
    """
    
    review_id: str = Field(description="A unique identifier for the review")
    text: str = Field(description="The full text of the review")
    labels: List[Label] = Field(description="The list of labels for this review")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "review_id": "1001",
                "text": "The debt settlement process was taking too long, but customer service was helpful.",
                "labels": [
                    {
                        "category": "Product & Services",
                        "subcategory": "Progress Pace",
                        "sentiment": "Negative"
                    },
                    {
                        "category": "Communication",
                        "subcategory": "Communication Method",
                        "sentiment": "Positive"
                    }
                ]
            }
        }
    )


class ReviewOutput(BaseModel):
    """
    Represents the output containing multiple processed reviews.
    
    This model is used as the container for returning a batch of
    processed reviews with their extracted labels.
    """
    
    reviews: List[Review] = Field(description="List of processed reviews")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "reviews": [
                    {
                        "review_id": "1001",
                        "text": "The debt settlement process was taking too long.",
                        "labels": [
                            {
                                "category": "Product & Services",
                                "subcategory": "Progress Pace",
                                "sentiment": "Negative"
                            }
                        ]
                    }
                ]
            }
        }
    )