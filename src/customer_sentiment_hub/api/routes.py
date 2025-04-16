"""
API routes for the Customer Sentiment Hub API.

This module defines all API endpoints, organizes them into routers,
and handles request/response interactions.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Body, Query, Path
from fastapi.responses import JSONResponse
from typing import List, Dict, Optional, Any
import time
import logging
from datetime import datetime

from customer_sentiment_hub.api.models import (
    ReviewRequest, 
    ReviewResponse, 
    ErrorResponse,
    HealthCheckResponse,
    ProcessedReview
)
from customer_sentiment_hub.services.processor import ReviewProcessor
from customer_sentiment_hub.services.gemini_service import GeminiService
from customer_sentiment_hub.domain.validation import ValidationService
from customer_sentiment_hub.config.settings import settings


# Configure logging
logger = logging.getLogger("customer_sentiment_hub")

# Create API routers
main_router = APIRouter()
analytics_router = APIRouter(prefix="/analytics", tags=["Analytics"])
admin_router = APIRouter(prefix="/admin", tags=["Administration"])


# Dependencies
def get_services():
    """
    Dependency that provides initialized services for route handlers.
    
    This ensures services are properly initialized and reused.
    """
    validation_service = ValidationService()
    gemini_service = GeminiService(
        gemini_settings=settings.gemini,
        google_settings=settings.google_cloud,
        validation_service=validation_service,
    )
    processor = ReviewProcessor(
        llm_service=gemini_service,
        settings=settings.processing,
    )
    
    return {
        "validation_service": validation_service,
        "gemini_service": gemini_service,
        "processor": processor
    }


def verify_admin_role(request: Request):
    """
    Dependency that verifies the user has admin role.
    
    Used to protect admin endpoints.
    """
    user_role = getattr(request.state, "user_role", None)
    if user_role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )
    return True


# Health check endpoint
@main_router.get("/health", response_model=HealthCheckResponse, tags=["System"])
async def health_check():
    """
    Check the health status of the API and its dependencies.
    
    Returns a health status object with information about dependencies.
    """
    dependencies_status = {}
    
    # Check Gemini API status
    try:
        # Simple test to see if Gemini API is responsive
        gemini_service = GeminiService(
            gemini_settings=settings.gemini,
            google_settings=settings.google_cloud,
            validation_service=ValidationService(),
        )
        await gemini_service.test_connection()
        dependencies_status["gemini_api"] = "available"
    except Exception as e:
        logger.error(f"Gemini API health check failed: {str(e)}")
        dependencies_status["gemini_api"] = "unavailable"
    
    # Add more dependency checks as needed
    
    # Determine overall status
    status = "healthy" if all(v == "available" for v in dependencies_status.values()) else "degraded"
    
    return HealthCheckResponse(
        status=status,
        version=settings.version,
        dependencies=dependencies_status
    )


# Main sentiment analysis endpoint
@main_router.post("/analyze", response_model=ReviewResponse, tags=["Sentiment Analysis"])
async def analyze_reviews(
    request: Request,
    review_request: ReviewRequest,
    services: Dict = Depends(get_services)
):
    try:
        # Log the request
        logger.info(
            f"Processing sentiment analysis request with {len(review_request.texts)} reviews. "
            f"Request ID: {getattr(request.state, 'request_id', 'unknown')}"
        )
        
        # Process the reviews
        start_time = time.time()
        result = await services["processor"].process_reviews(review_request.texts)
        processing_time = time.time() - start_time
        
        # Log processing time
        logger.info(f"Sentiment analysis completed in {processing_time:.2f} seconds")
        
        # Check for success
        if result.is_success():
            # Transform the result to match our API model
            processed_reviews = []
            
            for review_data in result.value["reviews"]:
                # Extract sentiment from labels or assign a default
                sentiment = "neutral"  # Default sentiment
                score = 0.5  # Default score
                
                # Try to determine sentiment from labels if available
                if "labels" in review_data and review_data["labels"]:
                    # Count sentiment occurrences
                    sentiment_counts = {}
                    for label in review_data["labels"]:
                        if "sentiment" in label:
                            # Convert to your SentimentLevel enum format
                            label_sentiment = label["sentiment"].lower()
                            if label_sentiment == "negative":
                                normalized = "negative"
                            elif label_sentiment == "positive":
                                normalized = "positive"
                            else:
                                normalized = "neutral"
                                
                            sentiment_counts[normalized] = sentiment_counts.get(normalized, 0) + 1
                    
                    # Determine overall sentiment based on most common label
                    if sentiment_counts:
                        sentiment = max(sentiment_counts.items(), key=lambda x: x[1])[0]
                        
                        # Calculate a simple score (0-1 range)
                        if sentiment == "negative":
                            score = 0.2
                        elif sentiment == "positive":
                            score = 0.8
                        else:
                            score = 0.5
                
                # Create aspects from labels if they exist
                aspects = []
                if "labels" in review_data and review_data["labels"]:
                    for label in review_data["labels"]:
                        if "category" in label and "subcategory" in label and "sentiment" in label:
                            # THIS IS THE CRITICAL FIX - always use a valid float for confidence
                            confidence_value = 0.5  # Default confidence
                            
                            # Only use the actual confidence if it's a valid float
                            if label.get("confidence") is not None and isinstance(label.get("confidence"), (int, float)):
                                confidence_value = float(label.get("confidence"))
                            
                            aspects.append({
                                "name": f"{label['category']} - {label['subcategory']}",
                                "sentiment": label["sentiment"].lower(),
                                "confidence": confidence_value  # Always a valid float
                            })
                
                # Create a processed review that matches our model
                processed_review = {
                    "text": review_data["text"],
                    "sentiment": sentiment,
                    "score": score,
                    "aspects": aspects,
                    "keywords": [],  # Add logic to extract keywords if available
                    "language": "en",  # Default language
                    "processed_at": datetime.now()
                }
                
                processed_reviews.append(processed_review)
            
            return {"reviews": processed_reviews}
        else:
            # Log the error
            logger.error(f"Error processing reviews: {result.error}")
            
            # Return an error response
            raise HTTPException(
                status_code=500,
                detail=result.error
            )
    except Exception as e:
        # Log unexpected exceptions
        logger.exception(f"Unexpected error in analyze_reviews: {str(e)}")
        
        # Return a user-friendly error
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred during review analysis"
        )


# Batch processing endpoint
@main_router.post("/analyze/batch", response_model=Dict[str, str], tags=["Sentiment Analysis"])
async def submit_batch_analysis(
    request: Request,
    review_request: ReviewRequest,
    callback_url: Optional[str] = Body(None),
    services: Dict = Depends(get_services)
):
    """
    Submit a batch of reviews for asynchronous processing.
    
    Returns a job ID that can be used to check the status later.
    """
    try:
        # Generate a job ID
        job_id = f"job_{int(time.time())}_{hash(str(review_request.texts)[:100]) % 10000}"
        
        # Log the batch request
        logger.info(
            f"Received batch analysis request with {len(review_request.texts)} reviews. "
            f"Job ID: {job_id}, Request ID: {getattr(request.state, 'request_id', 'unknown')}"
        )
        
        # Queue the batch job (this would integrate with a task queue in production)
        # For now, we'll just simulate enqueuing
        logger.info(f"Queued batch job {job_id} for processing")
        
        # In a real implementation, you would send this to a background task processor
        # such as Celery, RQ, or a cloud task queue
        
        return {
            "job_id": job_id,
            "status": "queued",
            "message": "Batch analysis job submitted successfully"
        }
    except Exception as e:
        # Log the exception
        logger.exception(f"Error submitting batch analysis job: {str(e)}")
        
        # Return an error response
        raise HTTPException(
            status_code=500,
            detail="Failed to submit batch analysis job"
        )


# Get batch job status
@main_router.get("/analyze/batch/{job_id}", tags=["Sentiment Analysis"])
async def get_batch_status(job_id: str):
    """
    Check the status of a previously submitted batch job.
    
    Returns the current status and, if complete, a link to download results.
    """
    # In a real implementation, this would check a database or task queue
    # For now, we'll simulate a response
    
    # Simulate some basic validation
    if not job_id.startswith("job_"):
        raise HTTPException(
            status_code=400,
            detail="Invalid job ID format"
        )
    
    # Return a simulated status
    # In production, you would query your task system for the actual status
    return {
        "job_id": job_id,
        "status": "processing",  # Could be "queued", "processing", "completed", "failed"
        "progress": 45,  # Percentage complete
        "submitted_at": "2025-04-16T14:30:00Z",
        "estimated_completion": "2025-04-16T14:35:00Z"
    }


# Analytics endpoints
@analytics_router.get("/trends", tags=["Analytics"])
async def get_sentiment_trends(
    start_date: str = Query(..., description="Start date (ISO format)"),
    end_date: str = Query(..., description="End date (ISO format)"),
    granularity: str = Query("daily", description="Time granularity (hourly, daily, weekly, monthly)"),
    services: Dict = Depends(get_services)
):
    """
    Get sentiment trends over a specified time period.
    
    Returns aggregated sentiment data across the specified date range.
    """
    try:
        # Parse dates
        try:
            start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid date format. Please use ISO format (YYYY-MM-DDTHH:MM:SSZ)"
            )
        
        # Validate date range
        if start > end:
            raise HTTPException(
                status_code=400,
                detail="Start date must be before end date"
            )
        
        # Validate granularity
        valid_granularities = ["hourly", "daily", "weekly", "monthly"]
        if granularity not in valid_granularities:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid granularity. Must be one of: {', '.join(valid_granularities)}"
            )
        
        # In a real implementation, you would query your database for these trends
        # For now, we'll return sample data
        
        return {
            "period": {
                "start": start_date,
                "end": end_date,
                "granularity": granularity
            },
            "trends": [
                {
                    "timestamp": "2025-04-10T00:00:00Z",
                    "sentiment_distribution": {
                        "very_positive": 0.25,
                        "positive": 0.45,
                        "neutral": 0.15,
                        "negative": 0.10,
                        "very_negative": 0.05
                    },
                    "average_score": 0.75
                },
                {
                    "timestamp": "2025-04-11T00:00:00Z",
                    "sentiment_distribution": {
                        "very_positive": 0.20,
                        "positive": 0.40,
                        "neutral": 0.20,
                        "negative": 0.15,
                        "very_negative": 0.05
                    },
                    "average_score": 0.70
                }
                # Additional data points would be included in a real implementation
            ]
        }
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Log other exceptions
        logger.exception(f"Error retrieving sentiment trends: {str(e)}")
        
        # Return a user-friendly error
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve sentiment trends"
        )


@analytics_router.get("/top-aspects", tags=["Analytics"])
async def get_top_aspects(
    start_date: str = Query(..., description="Start date (ISO format)"),
    end_date: str = Query(..., description="End date (ISO format)"),
    limit: int = Query(10, ge=1, le=100, description="Number of aspects to return"),
    sentiment: Optional[str] = Query(None, description="Filter by sentiment (positive, negative, neutral, all)"),
    services: Dict = Depends(get_services)
):
    """
    Get the most frequently mentioned aspects in reviews.
    
    Returns the top aspects extracted from reviews, with counts and average sentiment.
    """
    # Similar implementation to get_sentiment_trends
    # Would query the database for the top aspects
    
    return {
        "period": {
            "start": start_date,
            "end": end_date
        },
        "sentiment_filter": sentiment,
        "aspects": [
            {
                "name": "user interface",
                "count": 256,
                "sentiment_distribution": {
                    "positive": 0.65,
                    "neutral": 0.25,
                    "negative": 0.10
                },
                "average_score": 0.78
            },
            {
                "name": "customer service",
                "count": 187,
                "sentiment_distribution": {
                    "positive": 0.40,
                    "neutral": 0.20,
                    "negative": 0.40
                },
                "average_score": 0.52
            }
            # Additional aspects would be included in a real implementation
        ]
    }


# Admin endpoints - protected by admin role verification
@admin_router.get("/queue-status", dependencies=[Depends(verify_admin_role)], tags=["Administration"])
async def get_queue_status():
    """
    Get the status of the processing queue.
    
    Returns information about current queue length and processing rates.
    Admin access required.
    """
    return {
        "queue_length": 45,
        "processing_rate": 12.5,  # Jobs per minute
        "oldest_job": "2025-04-16T14:15:00Z",
        "estimated_completion_time": "2025-04-16T14:45:00Z"
    }


@admin_router.post("/reprocess/{job_id}", dependencies=[Depends(verify_admin_role)], tags=["Administration"])
async def reprocess_job(job_id: str):
    """
    Reprocess a specific batch job.
    
    Useful for jobs that failed or produced incorrect results.
    Admin access required.
    """
    return {
        "job_id": job_id,
        "status": "requeued",
        "message": "Job has been requeued for processing"
    }


def setup_routes(app):
    """
    Configure and add all routes to the FastAPI application.
    
    This function centralizes route registration.
    """
    # Include all routers
    app.include_router(main_router)
    app.include_router(analytics_router)
    app.include_router(admin_router)