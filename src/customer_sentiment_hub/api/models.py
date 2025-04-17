"""
Data models for the Customer Sentiment Hub API.

This module contains Pydantic models that define the structure of request and response data,
as well as internal data models used for processing and analysis.
"""

from pydantic import BaseModel, Field, conlist, validator
from typing import List, Dict, Optional, Any
from enum import Enum
import datetime

# Import domain models from schema to prevent duplication
from customer_sentiment_hub.domain.schema import Label, Review, ReviewOutput

# Define the individual review input model
class ReviewInput(BaseModel):
    """Model for an individual review input with ID."""
    review_id: str = Field(..., description="Unique identifier for the review")
    review_text: str = Field(..., description="Text content of the review")
    
    @validator('review_text')
    def validate_text_length(cls, text):
        """Validate that the review text is not too long."""
        max_length = 5000  # Maximum characters per review
        if len(text) > max_length:
            raise ValueError(f"Review text exceeds maximum length of {max_length} characters")
        if not text.strip():
            raise ValueError("Review text is empty or contains only whitespace")
        return text
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "review_id": "12345",
                "review_text": "I love this product! Works perfectly for my needs."
            }
        }
    }

# Update the API-specific request model
class ReviewRequest(BaseModel):
    """Model for the request body when submitting reviews for analysis."""
    reviews: conlist(ReviewInput, min_length=1, max_length=500) = Field(
        ..., 
        description="List of reviews to analyze (1-500 items)"
    )
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "reviews": [
                    {
                        "review_id": "12345",
                        "review_text": "I love this product! Works perfectly for my needs."
                    },
                    {
                        "review_id": "67890",
                        "review_text": "The customer service was terrible. Would not recommend."
                    }
                ]
            }
        }
    }

# API response model - aligned with processor output format
class ReviewResponse(BaseModel):
    """Model for the response body when returning analyzed reviews."""
    reviews: List[Review] = Field(..., description="List of processed reviews with sentiment analysis")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "reviews": [
                    {
                        "review_id": "1000",
                        "text": "I love this product! Works perfectly for my needs.",
                        "labels": [
                            {
                                "category": "Product & Services",
                                "subcategory": "Product Quality",
                                "sentiment": "Positive"
                            }
                        ]
                    }
                ]
            }
        }
    }

# Error response model for consistent error handling
class ErrorResponse(BaseModel):
    """Model for API error responses."""
    detail: str = Field(..., description="Error message")
    code: str = Field(..., description="Error code for programmatic handling")
    timestamp: datetime.datetime = Field(default_factory=datetime.datetime.now)
    path: Optional[str] = Field(None, description="The API path that generated the error")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "detail": "Unable to process reviews due to service unavailability",
                "code": "SERVICE_UNAVAILABLE",
                "timestamp": "2025-04-16T14:30:45.123Z",
                "path": "/analyze"
            }
        },
        "json_encoders": {
            datetime.datetime: lambda dt: dt.isoformat()
        }
    }

# Health check response model
class HealthCheckResponse(BaseModel):
    """Model for health check responses."""
    status: str = Field(..., description="Service status")
    version: str = Field(..., description="API version")
    dependencies: Dict[str, str] = Field(..., description="Status of dependencies")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "healthy",
                "version": "1.0.0",
                "dependencies": {
                    "gemini_api": "available"
                }
            }
        }
    }