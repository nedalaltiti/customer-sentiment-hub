"""
Data models for the Customer Sentiment Hub API.

This module contains Pydantic models that define the structure of request and response data,
as well as internal data models used for processing and analysis.
"""

from pydantic import BaseModel, Field, conlist, validator
from typing import List, Dict, Optional, Any, Union
from enum import Enum
import datetime


class SentimentLevel(str, Enum):
    """Enumeration of possible sentiment levels."""
    VERY_NEGATIVE = "very_negative"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"  
    POSITIVE = "positive"
    VERY_POSITIVE = "very_positive"


class Aspect(BaseModel):
    """Model representing an aspect of a review with its associated sentiment."""
    name: str = Field(..., description="The aspect name (e.g., 'customer service', 'product quality')")
    sentiment: SentimentLevel = Field(..., description="The sentiment associated with this aspect")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score for this aspect analysis")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "user interface",
                "sentiment": "positive",
                "confidence": 0.89
            }
        }


class ProcessedReview(BaseModel):
    """Model representing a processed review with sentiment analysis."""
    text: str = Field(..., description="The original review text")
    sentiment: SentimentLevel = Field(..., description="Overall sentiment of the review")
    score: float = Field(..., ge=0.0, le=1.0, description="Confidence score for the sentiment analysis")
    aspects: List[Aspect] = Field(default=[], description="Aspect-based sentiment analysis")
    keywords: List[str] = Field(default=[], description="Key terms extracted from the review")
    language: Optional[str] = Field(None, description="Detected language of the review")
    processed_at: datetime.datetime = Field(default_factory=datetime.datetime.now, description="Timestamp of processing")
    
    class Config:
        json_schema_extra = {
            "example": {
                "text": "The app is easy to use but customer service is slow to respond.",
                "sentiment": "neutral",
                "score": 0.65,
                "aspects": [
                    {"name": "usability", "sentiment": "positive", "confidence": 0.92},
                    {"name": "customer service", "sentiment": "negative", "confidence": 0.85}
                ],
                "keywords": ["app", "easy", "use", "customer service", "slow", "respond"],
                "language": "en",
                "processed_at": "2025-04-16T14:30:45.123Z"
            }
        }


class ReviewRequest(BaseModel):
    """Model for the request body when submitting reviews for analysis."""
    texts: conlist(str, min_length=1, max_length=100) = Field(
        ..., 
        description="List of review texts to analyze (1-100 items)"
    )
    
    @validator('texts')
    def validate_text_length(cls, texts):
        """Validate that no individual text is too long."""
        max_length = 5000  # Maximum characters per review
        for i, text in enumerate(texts):
            if len(text) > max_length:
                raise ValueError(f"Review at index {i} exceeds maximum length of {max_length} characters")
            if not text.strip():
                raise ValueError(f"Review at index {i} is empty or contains only whitespace")
        return texts
    
    class Config:
        json_schema_extra = {
            "example": {
                "texts": [
                    "I love this product! Works perfectly for my needs.",
                    "The customer service was terrible. Would not recommend.",
                    "Average experience, nothing special to report."
                ]
            }
        }


class ReviewResponse(BaseModel):
    """Model for the response body when returning analyzed reviews."""
    reviews: List[ProcessedReview] = Field(..., description="List of processed reviews with sentiment analysis")
    
    class Config:
        json_schema_extra = {
            "example": {
                "reviews": [
                    {
                        "text": "I love this product! Works perfectly for my needs.",
                        "sentiment": "positive",
                        "score": 0.92,
                        "aspects": [
                            {"name": "overall", "sentiment": "positive", "confidence": 0.92}
                        ],
                        "keywords": ["love", "product", "works", "perfectly", "needs"],
                        "language": "en",
                        "processed_at": "2025-04-16T14:30:45.123Z"
                    }
                ]
            }
        }


class ErrorResponse(BaseModel):
    """Model for API error responses."""
    detail: str = Field(..., description="Error message")
    code: str = Field(..., description="Error code for programmatic handling")
    timestamp: datetime.datetime = Field(default_factory=datetime.datetime.now)
    path: Optional[str] = Field(None, description="The API path that generated the error")
    
    # For Pydantic v2
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


class HealthCheckResponse(BaseModel):
    """Model for health check responses."""
    status: str = Field(..., description="Service status")
    version: str = Field(..., description="API version")
    dependencies: Dict[str, str] = Field(..., description="Status of dependencies")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "version": "1.0.0",
                "dependencies": {
                    "gemini_api": "available",
                    "database": "available"
                }
            }
        }