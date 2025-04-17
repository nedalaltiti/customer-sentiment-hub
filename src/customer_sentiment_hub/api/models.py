# src/customer_sentiment_hub/api/models.py

"""
Data models for the Customer Sentiment Hub API.

This module contains Pydantic models that define the structure of request and response data,
as well as internal data models used for processing and analysis.
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict
import datetime

# Import domain models directly
from customer_sentiment_hub.domain.schema import Review


class ReviewInput(BaseModel):
    """An individual review input with ID."""
    review_id: str = Field(..., description="Unique identifier for the review")
    review_text: str = Field(
        ...,
        description="Text content of the review",
        min_length=1,
        max_length=5000,
    )

    @validator("review_text")
    def no_blank_or_whitespace(cls, text: str) -> str:
        if not text.strip():
            raise ValueError("Review text is empty or only whitespace")
        return text

    class Config:
        json_schema_extra = {
            "example": {
                "review_id": "12345",
                "review_text": "I love this product! Works perfectly for my needs."
            }
        }


class ReviewRequest(BaseModel):
    """Request body for sentiment analysis."""
    reviews: List[ReviewInput] = Field(
        ...,
        description="List of reviews to analyze",
        min_items=1,
        max_items=500,
    )

    class Config:
        json_schema_extra = {
            "example": {
                "reviews": [
                    {"review_id": "12345", "review_text": "Loved it!"},
                    {"review_id": "67890", "review_text": "Terrible service."}
                ]
            }
        }


class ReviewResponse(BaseModel):
    """Response body with processed reviews."""
    reviews: List[Review] = Field(..., description="Sentiment‐labeled reviews")

    class Config:
        json_schema_extra = {
            "example": {
                "reviews": [
                    {
                        "review_id": "1000",
                        "text": "Loved it!",
                        "labels": [
                            {
                                "category": "Product & Services",
                                "subcategory": "Progress Pace",
                                "sentiment": "Positive"
                            }
                        ]
                    }
                ]
            }
        }


class ErrorResponse(BaseModel):
    """Standardized error response."""
    detail: str = Field(..., description="Error message")
    code: str = Field(..., description="Machine‑readable error code")
    timestamp: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    path: Optional[str] = Field(None, description="The API path that generated the error")

    class Config:
        json_encoders = {datetime.datetime: lambda dt: dt.isoformat()}
        json_schema_extra = {
            "example": {
                "detail": "Service unavailable",
                "code": "SERVICE_UNAVAILABLE",
                "timestamp": "2025-04-17T12:00:00Z",
                "path": "/analyze"
            }
        }


# Health check response model
class HealthCheckResponse(BaseModel):
    """Model for health check responses."""
    status: str = Field(..., description="Service status")
    version: str = Field(..., description="API version")
    dependencies: Dict[str, str] = Field(..., description="Status of dependencies")
    timestamp: datetime.datetime = Field(..., description="Timestamp of this check")

    class Config:
        json_encoders = {datetime.datetime: lambda dt: dt.isoformat()}
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "version": "1.0.0",
                "dependencies": {
                    "gemini_api": "available"
                },
                "timestamp": "2025-04-17T12:00:00Z"
            }
        }