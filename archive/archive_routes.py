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
import json
from datetime import datetime

from customer_sentiment_hub.api.models import (
    ReviewRequest, 
    ReviewResponse, 
    HealthCheckResponse,
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


# Custom JSON encoder to handle datetime objects
class CustomJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder that can handle datetime objects."""
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


# Function to safely serialize objects to JSON
def safe_json_serialize(obj):
    """Safely serialize an object to JSON, handling datetime objects."""
    return json.dumps(obj, cls=CustomJSONEncoder)


# Dependencies
def get_services():
    """
    Dependency that provides initialized services for route handlers.
    
    This ensures services are properly initialized and reused across requests,
    improving performance and reducing resource consumption.
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
    
    Used to protect admin endpoints and ensure proper authorization.
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
    
    Returns a health status object with information about the system's operational status.
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
    
    # Create response with safe serialization
    response_data = {
        "status": status,
        "version": settings.version,
        "dependencies": dependencies_status,
        "timestamp": datetime.now()  # This will be properly serialized
    }
    
    return HealthCheckResponse(**response_data)


# Main sentiment analysis endpoint
@main_router.post("/analyze", response_model=ReviewResponse, tags=["Sentiment Analysis"])
async def analyze_reviews(
    request: Request,
    review_request: ReviewRequest,
    services: Dict = Depends(get_services)
):
    """
    Analyze customer reviews for sentiment and extract insights.
    
    Processes a batch of review inputs and returns detailed sentiment analysis,
    preserving the connection between input review IDs and their analysis results.
    """
    try:
        # Count the number of reviews for proper logging
        review_count = len(review_request.reviews)
        
        # Log the request
        logger.info(
            f"Processing sentiment analysis request with {review_count} reviews. "
            f"Request ID: {getattr(request.state, 'request_id', 'unknown')}"
        )
        
        # Extract review texts and IDs from the request
        review_texts = [review.review_text for review in review_request.reviews]
        review_ids = [review.review_id for review in review_request.reviews]
        
        # Process the reviews with their IDs
        start_time = time.time()
        result = await services["processor"].process_reviews(review_texts, review_ids)
        processing_time = time.time() - start_time
        
        # Log processing time
        logger.info(f"Sentiment analysis completed in {processing_time:.2f} seconds for {review_count} reviews")
        
        # Check for success
        if result.is_success():
            # Return the processed reviews
            return {"reviews": result.value["reviews"]}
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
            detail=str(e)
        )


# Batch processing endpoint
@main_router.post("/analyze/batch", tags=["Sentiment Analysis"])
async def submit_batch_analysis(
    request: Request,
    review_request: ReviewRequest,
    callback_url: Optional[str] = Body(None),
    services: Dict = Depends(get_services)
):
    """
    Submit a batch of reviews for asynchronous processing.
    
    Returns a job ID that can be used to check the status later.
    This endpoint is useful for processing large numbers of reviews
    without waiting for immediate results.
    """
    try:
        # Extract review texts and IDs
        review_texts = [review.review_text for review in review_request.reviews]
        review_ids = [review.review_id for review in review_request.reviews]
        
        # Generate a consistent job ID based on request content
        hash_input = "_".join(review_ids[:5]) if review_ids else "_".join(review_texts[:5])
        job_id = f"job_{int(time.time())}_{hash(hash_input) % 10000}"
        
        # Log the batch request
        logger.info(
            f"Received batch analysis request with {len(review_request.reviews)} reviews. "
            f"Job ID: {job_id}, Request ID: {getattr(request.state, 'request_id', 'unknown')}"
        )
        
        # Here we would typically enqueue the job for background processing
        # For now, just log that we've queued it
        logger.info(f"Queued batch job {job_id} for processing")
        
        # Return job information to the client using JSONResponse to handle datetime
        response_data = {
            "job_id": job_id,
            "status": "queued",
            "message": "Batch analysis job submitted successfully",
            "review_count": len(review_request.reviews),
            "submitted_at": datetime.now()  # This will be properly serialized
        }
        
        # Use safe serialization for response
        return JSONResponse(content=response_data)
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
    This endpoint allows clients to poll for job completion.
    """
    if not job_id.startswith("job_"):
        raise HTTPException(
            status_code=400,
            detail="Invalid job ID format"
        )
    
    # Here you would typically query a job status database
    # For now, return mock data with datetime
    response_data = {
        "job_id": job_id,
        "status": "processing",  # Could be "queued", "processing", "completed", "failed"
        "progress": 45,  # Percentage complete
        "submitted_at": datetime.now().replace(hour=14, minute=30, second=0),
        "estimated_completion": datetime.now().replace(hour=14, minute=35, second=0)
    }
    
    # Use safe serialization for response
    return JSONResponse(content=response_data)


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
    
    Returns aggregated sentiment data across the specified date range,
    allowing analysis of sentiment changes over time.
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
    
        # Here you would typically query your analytics database
        # For now, return mock data with datetime objects
        response_data = {
            "period": {
                "start": start,
                "end": end,
                "granularity": granularity
            },
            "trends": [
                {
                    "timestamp": datetime(2025, 4, 10),
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
                    "timestamp": datetime(2025, 4, 11),
                    "sentiment_distribution": {
                        "very_positive": 0.20,
                        "positive": 0.40,
                        "neutral": 0.20,
                        "negative": 0.15,
                        "very_negative": 0.05
                    },
                    "average_score": 0.70
                }
            ]
        }
        
        # Use safe serialization for response
        return JSONResponse(content=response_data)
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
    This endpoint helps identify the most common topics in customer feedback.
    """
    # Here you would typically query your analytics database
    # For now, return mock data with datetime objects
    response_data = {
        "period": {
            "start": start_date,
            "end": end_date,
            "timestamp": datetime.now()
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
        ]
    }
    
    # Use safe serialization for response
    return JSONResponse(content=response_data)


# Admin endpoints - protected by admin role verification
@admin_router.get("/queue-status", dependencies=[Depends(verify_admin_role)], tags=["Administration"])
async def get_queue_status():
    """
    Get the status of the processing queue.
    
    Returns information about current queue length and processing rates.
    Admin access required for this endpoint.
    """
    # Here you would typically query your job queue system
    # For now, return mock data with datetime objects
    response_data = {
        "queue_length": 45,
        "processing_rate": 12.5,  # Jobs per minute
        "oldest_job": datetime.now().replace(hour=14, minute=15, second=0),
        "estimated_completion_time": datetime.now().replace(hour=14, minute=45, second=0)
    }
    
    # Use safe serialization for response
    return JSONResponse(content=response_data)


@admin_router.post("/reprocess/{job_id}", dependencies=[Depends(verify_admin_role)], tags=["Administration"])
async def reprocess_job(job_id: str):
    """
    Reprocess a specific batch job.
    
    Useful for jobs that failed or produced incorrect results.
    Admin access required for this endpoint.
    """
    if not job_id.startswith("job_"):
        raise HTTPException(
            status_code=400,
            detail="Invalid job ID format"
        )
    
    # Here you would typically requeue the job
    # For now, just return a success response with timestamp
    response_data = {
        "job_id": job_id,
        "status": "requeued",
        "message": "Job has been requeued for processing",
        "requeued_at": datetime.now()
    }
    
    # Use safe serialization for response
    return JSONResponse(content=response_data)


def setup_routes(app):
    """
    Configure and add all routes to the FastAPI application.
    
    This function centralizes route registration, making it easier to
    manage and modify the API's structure.
    """
    # Include all routers
    app.include_router(main_router)
    app.include_router(analytics_router)
    app.include_router(admin_router)